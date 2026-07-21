#!/usr/bin/env python3
"""
Read a saved klines JSON (either raw list or Toobit object with 'data'),
decode each kline array into a labelled object, and save as decode-{date}.json.
"""

import json
import glob
import os
import re
import sys

# ----------------------------------------------------------------------
# 1. Determine input file
# ----------------------------------------------------------------------
def find_input_file():
    # Look for files matching either "iran-date-*.json" or just a date like "1405-*.json"
    patterns = ["iran-date-*.json", "????-??-??.json"]
    files = []
    for p in patterns:
        files.extend(glob.glob(p))
    if not files:
        print("No file matching 'iran-date-*.json' or '????-??-??.json' found.", file=sys.stderr)
        sys.exit(1)
    # Sort by modification time and pick the newest
    latest = max(files, key=os.path.getmtime)
    return latest

if len(sys.argv) > 1:
    input_file = sys.argv[1]
    if not os.path.isfile(input_file):
        print(f"Input file '{input_file}' does not exist.", file=sys.stderr)
        sys.exit(1)
else:
    input_file = find_input_file()
    print(f"Auto-selected input file: {input_file}")

# ----------------------------------------------------------------------
# 2. Extract Iranian date from filename (flexible)
# ----------------------------------------------------------------------
# Try to find a pattern like YYYY-MM-DD (e.g., 1405-04-30)
match = re.search(r'(\d{4}-\d{2}-\d{2})', input_file)
if match:
    iran_date = match.group(1)
else:
    # Fallback: use current Iranian date
    import jdatetime
    iran_date = jdatetime.date.today().strftime("%Y-%m-%d")
    print(f"Could not extract date from filename, using today: {iran_date}")

output_file = f"decode-{iran_date}.json"

# ----------------------------------------------------------------------
# 3. Read and transform the JSON data
# ----------------------------------------------------------------------
try:
    with open(input_file, "r", encoding="utf-8") as f:
        raw = json.load(f)
except json.JSONDecodeError as e:
    print(f"Error decoding JSON from {input_file}: {e}", file=sys.stderr)
    sys.exit(1)
except IOError as e:
    print(f"Error reading file: {e}", file=sys.stderr)
    sys.exit(1)

# Handle both structures: { "data": [...] } or just [...]
if isinstance(raw, dict) and "data" in raw:
    data = raw["data"]
    print(f"Found 'data' field with {len(data)} entries.")
elif isinstance(raw, list):
    data = raw
    print(f"Root is a list with {len(data)} entries.")
else:
    print("Error: JSON root is neither a list nor an object containing a 'data' array.", file=sys.stderr)
    sys.exit(1)

if not isinstance(data, list):
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
    print(f"Successfully wrote {len(decoded)} entries to {output_file}")
except IOError as e:
    print(f"Error writing file: {e}", file=sys.stderr)
    sys.exit(1)