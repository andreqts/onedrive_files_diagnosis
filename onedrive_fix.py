import os
import sys
import time
import unicodedata
import argparse
from datetime import datetime

# Prohibited characters by OneDrive/Windows
INVALID_CHARS = set('<>:"/\\|?*')

# Path length limits
OLD_PATH_LIMIT = 250
CURRENT_PATH_LIMIT = 400

def has_invalid_chars(name):
    return any(c in INVALID_CHARS for c in name)

def has_invisible_chars(name):
    return any(ord(c) < 32 for c in name)

def has_wsl_remapped_chars(name):
    # WSL (DrvFs) maps illegal NTFS characters to the Unicode Private Use Area (U+F000 - U+F0FF)
    return any(0xF000 <= ord(c) <= 0xF0FF for c in name)

def is_path_too_long(path):
    return len(path) > CURRENT_PATH_LIMIT

def is_path_warning(path):
    return OLD_PATH_LIMIT < len(path) <= CURRENT_PATH_LIMIT

def has_invalid_timestamp(path):
    try:
        ts = os.path.getmtime(path)
        dt = datetime.fromtimestamp(ts)
        return dt.year < 1980 or dt.year > 2100
    except:
        return True

def check_file(path, report):
    problems = {
        'issues': [],
        'warnings': []
    }

    name = os.path.basename(path)

    if has_invalid_chars(name):
        problems['issues'].append("Invalid characters in name")

    if has_invisible_chars(name):
        problems['issues'].append("Invisible characters in name")

    if has_wsl_remapped_chars(name):
        problems['issues'].append("WSL-remapped character detected (likely forbidden on Windows)")

    path_len = len(path)
    if is_path_too_long(path):
        problems['issues'].append(f"Path too long ({path_len} chars, max {CURRENT_PATH_LIMIT})")
    elif is_path_warning(path):
        problems['warnings'].append(f"Path length warning ({path_len} chars, over {OLD_PATH_LIMIT})")

    if has_invalid_timestamp(path):
        problems['issues'].append("Invalid timestamp")

    if name.endswith(" "):
        problems['issues'].append("Trailing space in name")

    if name.endswith("."):
        problems['issues'].append("Trailing dot in name")

    # ADS (Alternate Data Streams)
    if ":" in name and not path.startswith("\\\\?\\"):
        problems['issues'].append("Alternate Data Stream detected")

    if problems['issues'] or problems['warnings']:
        # If there are any issues, the file as a whole is flagged as an ISSUE
        status = "ISSUE" if problems['issues'] else "WARNING"
        report.write(f"[{status}] {path}\n")
        
        for i in problems['issues']:
            report.write(f"  - {i}\n")
            
        for w in problems['warnings']:
            # If the overall file is an ISSUE, prefix warnings to distinguish them
            prefix = "[WARNING] " if problems['issues'] else ""
            report.write(f"  - {prefix}{w}\n")
            
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