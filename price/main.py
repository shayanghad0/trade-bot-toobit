#!/usr/bin/env python3
"""
Combined script to fetch and decode cryptocurrency klines data from Toobit.
1. Fetches data using the 'toobit' executable
2. Decodes the raw klines data into labelled objects
3. Saves the decoded data as candles.json
"""

import json
import os
import shutil
import subprocess
import sys
import threading
import time
from itertools import cycle
import jdatetime

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

# ----------------------------------------------------------------------
# Spinner animation (runs in a separate thread)
# ----------------------------------------------------------------------
def spinner(stop_event, message="Processing..."):
    """Display a rotating spinner until stop_event is set."""
    chars = cycle(['|', '/', '-', '\\'])
    while not stop_event.is_set():
        sys.stdout.write(f'\r{message} {next(chars)}')
        sys.stdout.flush()
        time.sleep(0.1)
    # Clear the line when done
    sys.stdout.write('\r' + ' ' * (len(message) + 2) + '\r')
    sys.stdout.flush()

# ----------------------------------------------------------------------
# Step 1: Fetch data using toobit
# ----------------------------------------------------------------------
def fetch_toobit_data():
    toobit_path = find_toobit()
    if not toobit_path:
        print("Error: Could not find 'toobit' executable. Please install it or set the correct path.", file=sys.stderr)
        sys.exit(1)

    # Get user input
    symbol = input("Please input a coin you want (e.g. BTCUSDT ETHUSDT ...): ")
    interval = input("What is your timeframe like 1m 5m 15m 1h 4h : ")
    limit = input("How many candels and data do you want 1 10 120 : ")

    command = [
        toobit_path,
        "market", "klines",
        "--symbol", symbol,
        "--interval", interval,
        "--limit", limit,
        "--json"
    ]

    print(f"Running: {' '.join(command)}")
    
    stop_event = threading.Event()
    spinner_thread = threading.Thread(target=spinner, args=(stop_event, "Fetching data..."))
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

    return json_output

# ----------------------------------------------------------------------
# Step 2: Decode the JSON data
# ----------------------------------------------------------------------
def decode_klines(json_data):
    output_file = "candles.json"

    stop_event = threading.Event()
    spinner_thread = threading.Thread(target=spinner, args=(stop_event, "Decoding data..."))
    spinner_thread.start()

    try:
        raw = json.loads(json_data)
    except json.JSONDecodeError as e:
        stop_event.set()
        spinner_thread.join()
        print(f"Error decoding JSON: {e}", file=sys.stderr)
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

    # Define kline field names and decode each entry
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

    # Save the decoded JSON
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
    print(f"Successfully decoded {len(decoded)} entries to {output_file}")
    
    return output_file

# ----------------------------------------------------------------------
# Main function
# ----------------------------------------------------------------------
def main():
    print("=" * 50)
    print("TOOBIT DATA FETCHER AND DECODER")
    print("=" * 50)
    
    # Step 1: Fetch data
    print("\n[STEP 1] Fetching data from Toobit...")
    json_data = fetch_toobit_data()
    
    # Step 2: Decode data
    print(f"\n[STEP 2] Decoding data...")
    decoded_file = decode_klines(json_data)
    
    print("\n" + "=" * 50)
    print("SUCCESS! Process completed.")
    print(f"Decoded data saved to: {decoded_file}")
    print("=" * 50)

if __name__ == "__main__":
    main()