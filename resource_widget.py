"""
Resource Widget - a small, always-on-top desktop dashboard for Windows
showing live CPU, RAM, GPU (NVIDIA) and Disk usage.

No installation required once compiled: it is a single portable .exe.

Build (see README.md / GitHub Actions workflow for the automated version):
    pip install -r requirements.txt pyinstaller
    pyinstaller --onefile --noconsole --name ResourceWidget resource_widget.py
"""

import sys
import collections
import tkinter as tk
import psutil

# ---------------------------------------------------------------------------
# Optional NVIDIA GPU support. Falls back gracefully if unavailable
# (no NVIDIA GPU, driver missing, or pynvml not installed).
# ---------------------------------------------------------------------------
GPU_AVAILABLE = False
_gpu_handle = None
try:
    import pynvml

    pynvml.nvmlInit()
    _gpu_handle = pynvml.nvmlDeviceGetHandleByIndex(0)
    _gpu_name = pynvml.nvmlDeviceGetName(_gpu_handle)
    if isinstance(_gpu_name, bytes):
        _gpu_name = _gpu_name.decode("utf-8", "ignore")
    GPU_AVAILABLE = True
except Exception:
    GPU_AVAILABLE = False
    _gpu_name = "No GPU detected"


def read_gpu():
    """Returns (usage_pct, vram_used_gb, vram_total_gb, temp_c) or None."""
    if not GPU_AVAILABLE:
        return None
    try:
        util = pynvml.nvmlDeviceGetUtilizationRates(_gpu_handle)
        mem = pynvml.nvmlDeviceGetMemoryInfo(_gpu_handle)
        temp = pynvml.nvmlDeviceGetTemperature(_gpu_handle, pynvml.NVML_TEMPERATURE_GPU)
        return (
            float(util.gpu),
            mem.used / (1024 ** 3),
            mem.total / (1024 ** 3),
            float(temp),
        )
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Config / theme
# ---------------------------------------------------------------------------
WIDTH = 260
HEIGHT_FULL = 388
HEIGHT_COLLAPSED = 46
UPDATE_MS = 1200
DISK_PATH = "C:\\" if sys.platform.startswith("win") else "/"
HISTORY_LEN = 40

BG = "#0f1115"
CARD = "#171a21"
ROW_BG = "#1d212b"
BORDER = "#252a35"
TEXT = "#eef0f5"
SUBTEXT = "#7d8494"
MUTED = "#565c6b"

C_CPU = "#5aa9ff"
C_RAM = "#b98bff"
C_GPU = "#34e0a1"
C_DISK = "#ffb454"
WARN = "#ffcc4d"
DANGER = "#ff5c6c"

BAR_TRACK = "#262b36"


def status_color(pct, accent):
    if pct >= 90:
        return DANGER
    if pct >= 75:
        return WARN
    return accent


class RoundedCanvas(tk.Canvas):
    """Canvas helper with rounded-rect / rounded-bar drawing."""

    def round_rect(self, x1, y1, x2, y2, radius=10, **kwargs):
        r = radius
        points = [
            x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r,
            x2, y2 - r, x2, y2, x2 - r, y2, x1 + r, y2,
            x1, y2, x1, y2 - r, x1, y1 + r, x1, y1,
        ]
        return self.create_polygon(points, smooth=True, **kwargs)

    def update_round_rect(self, item, x1, y1, x2, y2, radius=10):
        r = min(radius, max((x2 - x1) / 2, 1), max((y2 - y1) / 2, 1))
        if x2 <= x1:
            x2 = x1 + 0.01
        points = [
            x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r,
            x2, y2 - r, x2, y2, x2 - r, y2, x1 + r, y2,
            x1, y2, x1, y2 - r, x1, y1 + r, x1, y1,
        ]
        self.coords(item, *points)


class MetricRow:
    """One metric: icon glyph, label, % text, sub-label, progress bar."""

    def __init__(self, canvas: RoundedCanvas, y, icon, label, accent):
        self.canvas = canvas
        self.accent = accent
        self.y = y
        pad = 14
        bar_y1 = y + 34
        bar_y2 = bar_y1 + 7

        canvas.create_text(pad, y, anchor="w", text=icon, fill=accent,
                            font=("Segoe UI Symbol", 11, "bold"))
        canvas.create_text(pad + 22, y, anchor="w", text=label, fill=TEXT,
                            font=("Segoe UI", 10, "bold"))
        self.pct_text = canvas.create_text(
            WIDTH - pad, y, anchor="e", text="--%", fill=TEXT,
            font=("Segoe UI", 10, "bold")
        )
        self.sub_text = canvas.create_text(
            pad + 22, y + 16, anchor="w", text="", fill=SUBTEXT,
            font=("Segoe UI", 8)
        )

        canvas.round_rect(pad, bar_y1, WIDTH - pad, bar_y2, radius=4,
                           fill=BAR_TRACK, outline="")
        self.bar = canvas.round_rect(pad, bar_y1, pad, bar_y2, radius=4,
                                      fill=accent, outline="")
        self.bar_y1, self.bar_y2 = bar_y1, bar_y2
        self.x1, self.x2_full = pad, WIDTH - pad

    def update(self, pct, sub_label):
        pct = max(0.0, min(100.0, pct))
        color = status_color(pct, self.accent)
        self.canvas.itemconfig(self.pct_text, text=f"{pct:.0f}%")
        self.canvas.itemconfig(self.sub_text, text=sub_label)
        self.canvas.itemconfig(self.bar, fill=color)
        new_x2 = self.x1 + (self.x2_full - self.x1) * (pct / 100.0)
        self.canvas.update_round_rect(self.bar, self.x1, self.bar_y1, new_x2, self.bar_y2, radius=4)


class ResourceWidget(tk.Tk):
    def __init__(self):
        super().__init__()

        self.overrideredirect(True)
        self.attributes("-topmost", True)
        try:
            self.attributes("-alpha", 0.97)
        except tk.TclError:
            pass

        self.collapsed = False
        self.geometry(f"{WIDTH}x{HEIGHT_FULL}+80+80")
        self.config(bg=BG)

        self._offset_x = 0
        self._offset_y = 0
        self.cpu_history = collections.deque([0] * HISTORY_LEN, maxlen=HISTORY_LEN)

        self._build_ui()
        self._bind_drag()
        self._tick()

    # ------------------------------------------------------------------
    def _build_ui(self):
        self.canvas = RoundedCanvas(self, width=WIDTH, height=HEIGHT_FULL, bg=BG,
                                     highlightthickness=0, bd=0)
        self.canvas.pack(fill="both", expand=True)
        self._draw_static()

    def _draw_static(self):
        c = self.canvas
        c.delete("all")

        # outer card
        c.round_rect(1, 1, WIDTH - 1, HEIGHT_FULL - 1, radius=16, fill=CARD, outline=BORDER)

        # header
        self.live_dot = c.create_oval(14, 15, 20, 21, fill=C_GPU, outline="")
        c.create_text(26, 12, anchor="w", text="SYSTEM MONITOR", fill=TEXT,
                       font=("Segoe UI", 9, "bold"))

        self.min_btn = c.create_text(WIDTH - 40, 12, anchor="e", text="—",
                                      fill=SUBTEXT, font=("Segoe UI", 10, "bold"))
        c.tag_bind(self.min_btn, "<Button-1>", lambda e: self._toggle_collapse())

        self.close_btn = c.create_text(WIDTH - 16, 12, anchor="e", text="✕",
                                        fill=SUBTEXT, font=("Segoe UI", 10, "bold"))
        c.tag_bind(self.close_btn, "<Button-1>", lambda e: self.destroy())

        c.create_line(0, 34, WIDTH, 34, fill=BORDER)

        # metric rows
        row_h = 62
        y0 = 58
        self.cpu_row = MetricRow(c, y0, "\u25A3", "CPU", C_CPU)
        self.ram_row = MetricRow(c, y0 + row_h, "\u25A4", "RAM", C_RAM)
        self.gpu_row = MetricRow(c, y0 + row_h * 2, "\u25A6", "GPU", C_GPU)
        self.disk_row = MetricRow(c, y0 + row_h * 3, "\u25A5", "DISK", C_DISK)

        # divider + sparkline area
        spark_y = y0 + row_h * 4 + 4
        c.create_line(14, spark_y, WIDTH - 14, spark_y, fill=BORDER)
        c.create_text(14, spark_y + 12, anchor="w", text="CPU · last 60s",
                       fill=MUTED, font=("Segoe UI", 8))

        self.spark_top = spark_y + 26
        self.spark_bottom = HEIGHT_FULL - 16
        self.spark_left = 14
        self.spark_right = WIDTH - 14
        c.round_rect(self.spark_left, self.spark_top, self.spark_right,
                      self.spark_bottom, radius=6, fill=ROW_BG, outline="")
        self.spark_line = c.create_line(0, 0, 0, 0, fill=C_CPU, width=2, smooth=True)
        self.spark_fill = c.create_polygon(0, 0, 0, 0, fill="", outline="")

        if not GPU_AVAILABLE:
            self.gpu_row.update(0, _gpu_name[:28])

    # ------------------------------------------------------------------
    def _toggle_collapse(self):
        self.collapsed = not self.collapsed
        new_h = HEIGHT_COLLAPSED if self.collapsed else HEIGHT_FULL
        self.geometry(f"{WIDTH}x{new_h}")
        self.canvas.config(height=new_h)
        self._redraw_card_height(new_h)

    def _redraw_card_height(self, h):
        # Simplest robust approach: fully redraw static chrome sized to h.
        # For collapsed mode we only show the header bar.
        c = self.canvas
        c.delete("all")
        if self.collapsed:
            c.round_rect(1, 1, WIDTH - 1, h - 1, radius=16, fill=CARD, outline=BORDER)
            self.live_dot = c.create_oval(14, 15, 20, 21, fill=C_GPU, outline="")
            c.create_text(26, 12, anchor="w", text="SYSTEM MONITOR", fill=TEXT,
                          font=("Segoe UI", 9, "bold"))
            self.min_btn = c.create_text(WIDTH - 40, 12, anchor="e", text="▢",
                                          fill=SUBTEXT, font=("Segoe UI", 10, "bold"))
            c.tag_bind(self.min_btn, "<Button-1>", lambda e: self._toggle_collapse())
            self.close_btn = c.create_text(WIDTH - 16, 12, anchor="e", text="✕",
                                            fill=SUBTEXT, font=("Segoe UI", 10, "bold"))
            c.tag_bind(self.close_btn, "<Button-1>", lambda e: self.destroy())
        else:
            self._draw_static()

    # ------------------------------------------------------------------
    def _bind_drag(self):
        self.canvas.bind("<Button-1>", self._start_drag)
        self.canvas.bind("<B1-Motion>", self._on_drag)

    def _start_drag(self, event):
        self._offset_x = event.x
        self._offset_y = event.y

    def _on_drag(self, event):
        x = self.winfo_pointerx() - self._offset_x
        y = self.winfo_pointery() - self._offset_y
        self.geometry(f"+{x}+{y}")

    # ------------------------------------------------------------------
    def _update_sparkline(self):
        c = self.canvas
        w = self.spark_right - self.spark_left
        h = self.spark_bottom - self.spark_top
        n = len(self.cpu_history)
        step = w / max(n - 1, 1)

        pts = []
        for i, val in enumerate(self.cpu_history):
            x = self.spark_left + i * step
            y = self.spark_bottom - (val / 100.0) * h
            pts.extend([x, y])

        if len(pts) >= 4:
            c.coords(self.spark_line, *pts)
            poly = pts + [self.spark_right, self.spark_bottom, self.spark_left, self.spark_bottom]
            c.coords(self.spark_fill, *poly)
            c.itemconfig(self.spark_fill, fill=self._fade(C_CPU))

    @staticmethod
    def _fade(hex_color, alpha_hint="#14"):
        # tkinter canvas fill has no alpha; approximate with a dim static color
        return "#1c2636"

    # ------------------------------------------------------------------
    def _tick(self):
        try:
            cpu_pct = psutil.cpu_percent(interval=None)
            ram = psutil.virtual_memory()
            disk = psutil.disk_usage(DISK_PATH)
            gpu = read_gpu()

            self.cpu_history.append(cpu_pct)

            if not self.collapsed:
                self.cpu_row.update(cpu_pct, f"{cpu_pct:.0f}% across all cores")

                used_gb = ram.used / (1024 ** 3)
                total_gb = ram.total / (1024 ** 3)
                self.ram_row.update(ram.percent, f"{used_gb:.1f} / {total_gb:.1f} GB")

                if gpu is not None:
                    g_pct, g_used, g_total, g_temp = gpu
                    self.gpu_row.update(
                        g_pct, f"{g_used:.1f}/{g_total:.1f} GB · {g_temp:.0f}\u00b0C"
                    )
                else:
                    self.gpu_row.update(0, _gpu_name[:28] if not GPU_AVAILABLE else "read error")

                dused_gb = disk.used / (1024 ** 3)
                dtotal_gb = disk.total / (1024 ** 3)
                self.disk_row.update(disk.percent, f"{dused_gb:.0f} / {dtotal_gb:.0f} GB ({DISK_PATH})")

                self._update_sparkline()
        except Exception:
            pass

        self.after(UPDATE_MS, self._tick)


if __name__ == "__main__":
    app = ResourceWidget()
    app.mainloop()
