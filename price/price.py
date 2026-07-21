#!/usr/bin/env python3
import subprocess
import sys
import shutil
import jdatetime
import os
import threading
import time
from itertools import cycle

# ----------------------------------------------------------------------
# Locate the 'toobit' executable
# ----------------------------------------------------------------------
def find_toobit():
    # First, try the system PATH
    exe = shutil.which("toobit")
    if exe:
        return exe

    # On Windows, also try with .exe extension if not found
    if sys.platform == "win32":
        exe = shutil.which("toobit.exe")
        if exe:
            return exe

    # Look in the current working directory
    cwd_exe = os.path.join(os.getcwd(), "toobit")
    if os.path.isfile(cwd_exe):
        return cwd_exe
    cwd_exe_exe = os.path.join(os.getcwd(), "toobit.exe")
    if os.path.isfile(cwd_exe_exe):
        return cwd_exe_exe

    # Look in the parent directory (one level up)
    parent = os.path.dirname(os.getcwd())
    parent_exe = os.path.join(parent, "toobit")
    if os.path.isfile(parent_exe):
        return parent_exe
    parent_exe_exe = os.path.join(parent, "toobit.exe")
    if os.path.isfile(parent_exe_exe):
        return parent_exe_exe

    return None

toobit_path = find_toobit()
if not toobit_path:
    print("Error: Could not find 'toobit' executable. Please install it or set the correct path.", file=sys.stderr)
    sys.exit(1)

# ----------------------------------------------------------------------
# Get Iranian date and build command
# ----------------------------------------------------------------------
today = jdatetime.date.today()
persian_date_str = today.strftime("%Y-%m-%d")

command = [
    toobit_path,
    "market", "klines",
    "--symbol", input("Please input a coin you want (e.g. BTCUSDT ETHUSDT ...): "),
    "--interval", input("What is your timeframe like 1m 5m 15m 1h 4h : "),
    "--limit", input("How many candels and data do you want 1 10 120 : "),
    "--json"
]

# ----------------------------------------------------------------------
# Spinner animation (runs in a separate thread)
# ----------------------------------------------------------------------
def spinner(stop_event):
    """Display a rotating spinner until stop_event is set."""
    chars = cycle(['|', '/', '-', '\\'])
    msg = "Fetching data..."
    while not stop_event.is_set():
        sys.stdout.write(f'\r{msg} {next(chars)}')
        sys.stdout.flush()
        time.sleep(0.1)
    # Clear the line when done
    sys.stdout.write('\r' + ' ' * (len(msg) + 2) + '\r')
    sys.stdout.flush()

# ----------------------------------------------------------------------
# Run command with animated spinner
# ----------------------------------------------------------------------
stop_event = threading.Event()
spinner_thread = threading.Thread(target=spinner, args=(stop_event,))

print(f"Running: {' '.join(command)}")
spinner_thread.start()

try:
    result = subprocess.run(command, capture_output=True, text=True, check=True)
    json_output = result.stdout
except subprocess.CalledProcessError as e:
    stop_event.set()
    spinner_thread.join()
    print(f"Command failed with exit code {e.returncode}", file=sys.stderr)
    print(f"stderr: {e.stderr}", file=sys.stderr)
    sys.exit(1)
except FileNotFoundError:
    stop_event.set()
    spinner_thread.join()
    print(f"Error: The executable '{toobit_path}' was not found.", file=sys.stderr)
    sys.exit(1)
else:
    stop_event.set()
    spinner_thread.join()

# ----------------------------------------------------------------------
# Save JSON output
# ----------------------------------------------------------------------
filename = f"{persian_date_str}.json"
try:
    with open(filename, "w", encoding="utf-8") as f:
        f.write(json_output)
    print(f"Successfully saved JSON to {filename}")
except IOError as e:
    print(f"Error writing file: {e}", file=sys.stderr)
    sys.exit(1)