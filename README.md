# Resource Widget

A polished, always-on-top Windows desktop dashboard showing live **CPU**,
**RAM**, **GPU** (NVIDIA — usage, VRAM, temperature) and **Disk** usage, plus
a rolling CPU history sparkline. No installer — it's a single portable `.exe`.

If no NVIDIA GPU / driver is found, the GPU row shows "No GPU detected"
instead of failing — the rest of the widget keeps working normally.

![status](https://img.shields.io/badge/build-GitHub%20Actions-blue)

## How the auto-build works

Every time you push to `main` (or open a pull request), GitHub Actions spins
up a Windows runner, installs the dependencies, and compiles
`resource_widget.py` into `ResourceWidget.exe` with PyInstaller. You never
need Python or a Windows machine yourself — GitHub does the compiling.

### Getting the exe after a push

1. Push your code to GitHub.
2. Go to the **Actions** tab of the repo → click the latest **Build Windows
   Widget** run.
3. Scroll to **Artifacts** → download **ResourceWidget-windows-exe**.
   It's a zip containing `ResourceWidget.exe`. That's the whole app.

Artifacts are kept for 30 days per run.

### Getting an exe attached to a Release (permanent download link)

If you want a stable, permanent download link instead of digging through
Actions runs each time, push a version tag:

```bash
git tag v1.0.0
git push origin v1.0.0
```

The workflow will build the exe and automatically create a GitHub Release
named `v1.0.0` with `ResourceWidget.exe` attached. Anyone can then grab it
straight from the repo's **Releases** page.

## Running the widget

Download `ResourceWidget.exe` and double-click it. It opens as a small
borderless dashboard card showing CPU, RAM, GPU and Disk (`C:`), each with a
progress bar that shifts from green → orange → red as usage climbs, plus a
live CPU history sparkline at the bottom.

- Drag it anywhere by clicking and holding on the panel.
- Click **—** to collapse it down to just the header bar; click again to
  expand.
- Click the small **✕** in the top-right corner to close it.

### Run it automatically at Windows startup (optional)

Press `Win + R`, type `shell:startup`, press Enter. Copy a shortcut to
`ResourceWidget.exe` into that folder — it will launch every time you log in.

## Building locally instead (optional)

You don't need this if you're using GitHub Actions, but if you want to build
on your own Windows PC:

```bash
pip install -r requirements.txt pyinstaller
pyinstaller --onefile --noconsole --name ResourceWidget resource_widget.py
```

The exe will be in the `dist` folder.

## Repo structure

```
.
├── .github/workflows/build.yml   # CI: builds the exe on every push / tag
├── resource_widget.py            # the widget source
├── requirements.txt              # Python dependencies (psutil)
├── .gitignore
└── README.md
```
