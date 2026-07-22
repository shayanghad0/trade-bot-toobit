#!/usr/bin/env python3
"""
Read a saved klines JSON (either raw list or Toobit object with 'data'),
decode each kline array into a labelled object, and save as decode-{date}.json.

If no filename is given as argument, the script searches for files matching
'iran-date-*.json' or '????-??-??.json' in the current directory.
- If exactly one is found, it is used automatically.
- If more than one are found, a numbered list is shown and you select one.
- If none are found, the script exits with an error.
"""

import json
import glob
import os
import re
import sys
import threading
import time
from itertools import cycle

# ----------------------------------------------------------------------
# Helper: find all matching JSON files in the current directory
# ----------------------------------------------------------------------
def find_matching_files():
    patterns = ["iran-date-*.json", "????-??-??.json"]
    files = []
    for p in patterns:
        files.extend(glob.glob(p))
    # Remove duplicates (if any pattern overlaps)
    files = list(set(files))
    # Sort alphabetically for consistent ordering
    files.sort()
    return files

# ----------------------------------------------------------------------
# 1. Determine input file (argument, or interactive selection)
# ----------------------------------------------------------------------
if len(sys.argv) > 1:
    input_file = sys.argv[1]
    if not os.path.isfile(input_file):
        print(f"Input file '{input_file}' does not exist.", file=sys.stderr)
        sys.exit(1)
else:
    # Search for files
    matches = find_matching_files()
    if not matches:
        print("No file matching 'iran-date-*.json' or '????-??-??.json' found.", file=sys.stderr)
        sys.exit(1)
    elif len(matches) == 1:
        input_file = matches[0]
        print(f"Auto-selected input file: {input_file}")
    else:
        print("Multiple matching files found:")
        for idx, fname in enumerate(matches, start=1):
            print(f"{idx}. {fname}")
        while True:
            try:
                choice = input("Please input which one you want to decode (enter number): ")
                idx = int(choice) - 1
                if 0 <= idx < len(matches):
                    input_file = matches[idx]
                    break
                else:
                    print(f"Invalid number. Please enter a number between 1 and {len(matches)}.")
            except ValueError:
                print("Please enter a valid number.")

# ----------------------------------------------------------------------
# 2. Extract Iranian date from filename (flexible)
# ----------------------------------------------------------------------
match = re.search(r'(\d{4}-\d{2}-\d{2})', input_file)
if match:
    iran_date = match.group(1)
else:
    # Fallback: use current Iranian date
    import jdatetime
    iran_date = jdatetime.date.today().strftime("%Y-%m-%d")
    print(f"Could not extract date from filename, using today: {iran_date}")

output_file = f"candles.json"

# ----------------------------------------------------------------------
# Spinner animation (runs in a separate thread)
# ----------------------------------------------------------------------
def spinner(stop_event):
    """Display a rotating spinner until stop_event is set."""
    chars = cycle(['|', '/', '-', '\\'])
    msg = "Processing data..."
    while not stop_event.is_set():
        sys.stdout.write(f'\r{msg} {next(chars)}')
        sys.stdout.flush()
        time.sleep(0.1)
    # Clear the line when done
    sys.stdout.write('\r' + ' ' * (len(msg) + 2) + '\r')
    sys.stdout.flush()

stop_event = threading.Event()
spinner_thread = threading.Thread(target=spinner, args=(stop_event,))
spinner_thread.start()

# ----------------------------------------------------------------------
# 3. Read and transform the JSON data
# ----------------------------------------------------------------------
try:
    with open(input_file, "r", encoding="utf-8") as f:
        raw = json.load(f)
except json.JSONDecodeError as e:
    stop_event.set()
    spinner_thread.join()
    print(f"Error decoding JSON from {input_file}: {e}", file=sys.stderr)
    sys.exit(1)
except IOError as e:
    stop_event.set()
    spinner_thread.join()
    print(f"Error reading file: {e}", file=sys.stderr)
    sys.exit(1)

# Handle both structures: { "data": [...] } or just [...]
if isinstance(raw, dict) and "data" in raw:
    data = raw["data"]
    print(f"\nFound 'data' field with {len(data)} entries.")
elif isinstance(raw, list):
    data = raw
    print(f"\nRoot is a list with {len(data)} entries.")
else:
    stop_event.set()
    spinner_thread.join()
    print("Error: JSON root is neither a list nor an object containing a 'data' array.", file=sys.stderr)
    sys.exit(1)

if not isinstance(data, list):
    stop_event.set()
    spinner_thread.join()
    print("Error: 'data' is not a list.", file=sys.stderr)
    sys.exit(1)

# ----------------------------------------------------------------------
# 4. Define kline field names and decode each entry
# ----------------------------------------------------------------------
fields = [
    "open_time",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "ignore",
    "quote_volume",
    "trades",
    "taker_buy_volume",
    "taker_buy_quote_volume"
]

decoded = []
for idx, item in enumerate(data):
    if not isinstance(item, list):
        print(f"Warning: item at index {idx} is not a list, skipping.", file=sys.stderr)
        continue
    if len(item) != len(fields):
        print(f"Warning: item at index {idx} has {len(item)} elements, expected {len(fields)}. Skipping.", file=sys.stderr)
        continue
    decoded.append(dict(zip(fields, item)))

# ----------------------------------------------------------------------
# 5. Save the decoded JSON
# ----------------------------------------------------------------------
try:
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(decoded, f, indent=2, ensure_ascii=False)
except IOError as e:
    stop_event.set()
    spinner_thread.join()
    print(f"Error writing file: {e}", file=sys.stderr)
    sys.exit(1)

# Stop spinner and print final success message
stop_event.set()
spinner_thread.join()
print(f"Successfully wrote {len(decoded)} entries to {output_file}")