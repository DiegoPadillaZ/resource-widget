@echo off
REM Run this on a Windows machine, in the same folder as resource_widget.py
REM It installs the two needed packages and builds a single portable .exe.

echo Installing dependencies...
pip install psutil pyinstaller

echo Building ResourceWidget.exe ...
pyinstaller --onefile --noconsole --name ResourceWidget resource_widget.py

echo.
echo Done. Your exe is in the "dist" folder: dist\ResourceWidget.exe
echo You can copy that single file anywhere - no installer needed.
pause
