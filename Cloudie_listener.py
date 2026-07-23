"""
Cloudie_listener.py
-------------------
This tiny script runs silently at Windows startup.
It waits for Ctrl+Shift+F9 — then launches Cloudie.
Uses almost no RAM and you will never see it.
"""

import subprocess
import os
import sys
import time
import keyboard

# Path to your Cloudie.py — update if you move it
CLOUDIE_PATH = r"C:\Users\Acer\OneDrive\ドキュメント\Desktop\Cloudie.py"
PYTHON_PATH  = r"C:\Users\Acer\AppData\Local\Programs\Python\Python310\python.exe"

cloudie_process = None

def launch_or_close():
    global cloudie_process

    # If Cloudie is not running — launch it
    if cloudie_process is None or cloudie_process.poll() is not None:
        cloudie_process = subprocess.Popen(
            [PYTHON_PATH, CLOUDIE_PATH],
            creationflags=subprocess.CREATE_NO_WINDOW
        )
    else:
        # If already running — send hotkey so it toggles listening
        # (Cloudie.py handles Ctrl+Shift+F9 internally too)
        pass  # Cloudie handles its own toggle internally

# Register the global hotkey
keyboard.add_hotkey("ctrl+shift+f9", launch_or_close)

# Keep script alive silently forever
keyboard.wait()
