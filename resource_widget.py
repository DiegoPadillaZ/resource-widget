"""
Resource Widget - A small always-on-top desktop widget for Windows
showing live RAM and Disk usage.

No installation required once compiled: it is a single portable .exe.

Build instructions (run on a Windows machine, see BUILD.txt):
    pip install psutil pyinstaller
    pyinstaller --onefile --noconsole --name ResourceWidget resource_widget.py
"""

import tkinter as tk
import psutil
import sys

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
WIDTH, HEIGHT = 230, 130
UPDATE_MS = 1500
DISK_PATH = "C:\\" if sys.platform.startswith("win") else "/"

BG = "#14161b"
PANEL = "#1e2129"
TEXT = "#e6e8ee"
SUBTEXT = "#8a8f9c"
ACCENT_RAM = "#5aa9ff"
ACCENT_DISK = "#7cf29c"
WARN = "#ffb454"
DANGER = "#ff5a5a"
BAR_BG = "#2a2d37"


def color_for(pct: float, accent: str) -> str:
    if pct >= 90:
        return DANGER
    if pct >= 75:
        return WARN
    return accent


class ResourceWidget(tk.Tk):
    def __init__(self):
        super().__init__()

        self.overrideredirect(True)          # no title bar / borders
        self.attributes("-topmost", True)    # always on top
        try:
            self.attributes("-alpha", 0.94)  # slight transparency
        except tk.TclError:
            pass

        self.geometry(f"{WIDTH}x{HEIGHT}+80+80")
        self.config(bg=BG)

        self._offset_x = 0
        self._offset_y = 0

        self._build_ui()
        self._bind_drag()
        self._tick()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------
    def _build_ui(self):
        self.canvas = tk.Canvas(
            self, width=WIDTH, height=HEIGHT, bg=BG,
            highlightthickness=0, bd=0
        )
        self.canvas.pack(fill="both", expand=True)

        self._round_rect(self.canvas, 2, 2, WIDTH - 2, HEIGHT - 2,
                          radius=16, fill=PANEL, outline="")

        self.canvas.create_text(
            16, 14, anchor="w", text="System Monitor",
            fill=TEXT, font=("Segoe UI", 10, "bold")
        )

        # close button
        self.close_btn = self.canvas.create_text(
            WIDTH - 16, 14, anchor="e", text="✕",
            fill=SUBTEXT, font=("Segoe UI", 10, "bold")
        )
        self.canvas.tag_bind(self.close_btn, "<Button-1>", lambda e: self.destroy())

        # RAM row
        self.ram_label = self.canvas.create_text(
            16, 42, anchor="w", text="RAM", fill=SUBTEXT,
            font=("Segoe UI", 9)
        )
        self.ram_pct_text = self.canvas.create_text(
            WIDTH - 16, 42, anchor="e", text="--%", fill=TEXT,
            font=("Segoe UI", 9, "bold")
        )
        self.ram_bar_bg = self._round_rect(
            self.canvas, 16, 58, WIDTH - 16, 68, radius=5, fill=BAR_BG, outline=""
        )
        self.ram_bar_fg = self._round_rect(
            self.canvas, 16, 58, 16, 68, radius=5, fill=ACCENT_RAM, outline=""
        )

        # Disk row
        self.disk_label = self.canvas.create_text(
            16, 86, anchor="w", text=f"Disk ({DISK_PATH})", fill=SUBTEXT,
            font=("Segoe UI", 9)
        )
        self.disk_pct_text = self.canvas.create_text(
            WIDTH - 16, 86, anchor="e", text="--%", fill=TEXT,
            font=("Segoe UI", 9, "bold")
        )
        self.disk_bar_bg = self._round_rect(
            self.canvas, 16, 102, WIDTH - 16, 112, radius=5, fill=BAR_BG, outline=""
        )
        self.disk_bar_fg = self._round_rect(
            self.canvas, 16, 102, 16, 112, radius=5, fill=ACCENT_DISK, outline=""
        )

    def _round_rect(self, canvas, x1, y1, x2, y2, radius=12, **kwargs):
        points = [
            x1 + radius, y1,
            x2 - radius, y1,
            x2, y1,
            x2, y1 + radius,
            x2, y2 - radius,
            x2, y2,
            x2 - radius, y2,
            x1 + radius, y2,
            x1, y2,
            x1, y2 - radius,
            x1, y1 + radius,
            x1, y1,
        ]
        return canvas.create_polygon(points, smooth=True, **kwargs)

    def _update_bar(self, bar_id, x1, y, x2_full, pct, height=10):
        new_x2 = x1 + (x2_full - x1) * (pct / 100.0)
        radius = height / 2
        points = [
            x1 + radius, y,
            new_x2 - radius, y,
            new_x2, y,
            new_x2, y + radius,
            new_x2, y + height - radius,
            new_x2, y + height,
            new_x2 - radius, y + height,
            x1 + radius, y + height,
            x1, y + height,
            x1, y + height - radius,
            x1, y + radius,
            x1, y,
        ]
        self.canvas.coords(bar_id, *points)

    # ------------------------------------------------------------------
    # Drag to move (frameless window has no title bar)
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
    # Data refresh
    # ------------------------------------------------------------------
    def _tick(self):
        try:
            ram = psutil.virtual_memory()
            disk = psutil.disk_usage(DISK_PATH)

            ram_pct = ram.percent
            disk_pct = disk.percent

            self.canvas.itemconfig(self.ram_pct_text, text=f"{ram_pct:.0f}%")
            self.canvas.itemconfig(self.disk_pct_text, text=f"{disk_pct:.0f}%")

            ram_color = color_for(ram_pct, ACCENT_RAM)
            disk_color = color_for(disk_pct, ACCENT_DISK)
            self.canvas.itemconfig(self.ram_bar_fg, fill=ram_color)
            self.canvas.itemconfig(self.disk_bar_fg, fill=disk_color)

            self._update_bar(self.ram_bar_fg, 16, 58, WIDTH - 16, ram_pct)
            self._update_bar(self.disk_bar_fg, 16, 102, WIDTH - 16, disk_pct)

            used_gb = ram.used / (1024 ** 3)
            total_gb = ram.total / (1024 ** 3)
            self.canvas.itemconfig(
                self.ram_label,
                text=f"RAM  {used_gb:.1f}/{total_gb:.1f} GB"
            )

            dused_gb = disk.used / (1024 ** 3)
            dtotal_gb = disk.total / (1024 ** 3)
            self.canvas.itemconfig(
                self.disk_label,
                text=f"Disk  {dused_gb:.0f}/{dtotal_gb:.0f} GB"
            )
        except Exception:
            pass

        self.after(UPDATE_MS, self._tick)


if __name__ == "__main__":
    app = ResourceWidget()
    app.mainloop()
