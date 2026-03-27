import os
import sys
import time
import unicodedata
import argparse
from datetime import datetime

# Prohibited characters by OneDrive/Windows
INVALID_CHARS = set('<>:"/\\|?*')

def has_invalid_chars(name):
    return any(c in INVALID_CHARS for c in name)

def has_invisible_chars(name):
    return any(ord(c) < 32 for c in name)

def is_path_too_long(path):
    return len(path) > 250  # safety margin

def has_invalid_timestamp(path):
    try:
        ts = os.path.getmtime(path)
        dt = datetime.fromtimestamp(ts)
        return dt.year < 1980 or dt.year > 2100
    except:
        return True

def check_file(path, report):
    problems = []

    name = os.path.basename(path)

    if has_invalid_chars(name):
        problems.append("Invalid characters in name")

    if has_invisible_chars(name):
        problems.append("Invisible characters in name")

    if is_path_too_long(path):
        problems.append("Path too long (>250 chars)")

    if has_invalid_timestamp(path):
        problems.append("Invalid timestamp")

    # ADS (Alternate Data Streams)
    if ":" in name and not path.startswith("\\\\?\\"):
        problems.append("Alternate Data Stream detected")

    if problems:
        report.write(f"[ISSUE] {path}\n")
        for p in problems:
            report.write(f"  - {p}\n")
        report.write("\n")

def main():
    parser = argparse.ArgumentParser(description="OneDrive Diagnosis Tool")
    parser.add_argument("path", help="OneDrive local folder path")
    parser.add_argument("report", nargs='?', default="onedrive_diagnosis.txt", help="Report file name/path (default: onedrive_diagnosis.txt)")
    args = parser.parse_args()

    onedrive_path = args.path
    report_file = args.report

    if not os.path.exists(onedrive_path):
        print(f"Error: OneDrive path not found: {onedrive_path}")
        sys.exit(1)

    with open(report_file, "w", encoding="utf-8") as report:
        report.write("=== OneDrive Diagnosis ===\n")
        report.write(f"Date: {datetime.now()}\n\n")
        report.write(f"Scanned Path: {onedrive_path}\n\n")

        for root, dirs, files in os.walk(onedrive_path):
            for f in files:
                full = os.path.join(root, f)
                check_file(full, report)

    print(f"Diagnosis completed. View the file: {report_file}")

if __name__ == "__main__":
    main()