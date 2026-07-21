#!/usr/bin/env python3
import subprocess
import sys
import shutil
import jdatetime
import os

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
    "--symbol", "BTCUSDT",
    "--interval", "4h",
    "--limit", "120",
    "--json"
]

# ----------------------------------------------------------------------
# Run command and save output
# ----------------------------------------------------------------------
try:
    print(f"Running: {' '.join(command)}")
    result = subprocess.run(command, capture_output=True, text=True, check=True)
    json_output = result.stdout
except subprocess.CalledProcessError as e:
    print(f"Command failed with exit code {e.returncode}", file=sys.stderr)
    print(f"stderr: {e.stderr}", file=sys.stderr)
    sys.exit(1)
except FileNotFoundError:
    print(f"Error: The executable '{toobit_path}' was not found.", file=sys.stderr)
    sys.exit(1)

filename = f"{persian_date_str}.json"
try:
    with open(filename, "w", encoding="utf-8") as f:
        f.write(json_output)
    print(f"Successfully saved JSON to {filename}")
except IOError as e:
    print(f"Error writing file: {e}", file=sys.stderr)
    sys.exit(1)