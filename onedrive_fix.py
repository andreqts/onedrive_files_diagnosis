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
RELATIVE_PATH_LIMIT = 400
ABSOLUTE_PATH_LIMIT = 520
SEGMENT_LIMIT = 255
# Microsoft recommends not syncing more than 300,000 files
MAX_SYNC_FILES_LIMIT = 300000  # Microsoft recommended sync limit

def has_invalid_chars(name):
    return any(c in INVALID_CHARS for c in name)

def has_invisible_chars(name):
    return any(ord(c) < 32 for c in name)

def has_wsl_remapped_chars(name):
    # WSL (DrvFs) maps illegal NTFS characters to the Unicode Private Use Area (U+F000 - U+F0FF)
    return any(0xF000 <= ord(c) <= 0xF0FF for c in name)

    return any(0xF000 <= ord(c) <= 0xF0FF for c in name)

def has_invalid_timestamp(path):
    try:
        ts = os.path.getmtime(path)
        dt = datetime.fromtimestamp(ts)
        return dt.year < 1980 or dt.year > 2100
    except:
        return True

def check_file(path, onedrive_root, report):
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

    # Segment length check
    for part in os.path.normpath(path).split(os.sep):
        if len(part) > SEGMENT_LIMIT:
            problems['issues'].append(f"Path segment '{part[:15]}...' too long ({len(part)} chars, max {SEGMENT_LIMIT})")
            break

    # Absolute and Relative path length checks
    rel_path = os.path.relpath(path, onedrive_root)
    path_len = len(path)
    rel_len = len(rel_path)
    
    if path_len > ABSOLUTE_PATH_LIMIT:
        problems['issues'].append(f"Absolute path too long ({path_len} chars, max {ABSOLUTE_PATH_LIMIT})")
    elif path_len > OLD_PATH_LIMIT:
        problems['warnings'].append(f"Absolute path length Explorer warning ({path_len} chars, over {OLD_PATH_LIMIT})")

    if rel_len > RELATIVE_PATH_LIMIT:
        problems['issues'].append(f"Relative path too long ({rel_len} chars, max {RELATIVE_PATH_LIMIT})")

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
        
        
    return problems

def main():
    parser = argparse.ArgumentParser(description="OneDrive Diagnosis Tool")
    parser.add_argument("path", help="OneDrive local folder path")
    parser.add_argument("report", nargs='?', default="onedrive_diagnosis.txt", help="Report file name/path (default: onedrive_diagnosis.txt)")
    parser.add_argument("--test_mode", action="store_true", help="Enable test mode (lowers MAX_SYNC_FILES_LIMIT to 10 for automated testing)")
    args = parser.parse_args()

    onedrive_path = os.path.abspath(args.path)
    report_file = args.report

    if not os.path.exists(onedrive_path):
        print(f"Error: OneDrive path not found: {onedrive_path}")
        sys.exit(1)

    with open(report_file, "w", encoding="utf-8") as report:
        report.write("=== OneDrive Diagnosis ===\n")
        report.write(f"Date: {datetime.now()}\n\n")
        report.write(f"Scanned Path: {onedrive_path}\n\n")

        stats = {
            'files_scanned': 0,
            'files_with_issues': 0,
            'files_with_only_warnings': 0,
            'total_issues': 0,
            'total_warnings': 0
        }

        for root, dirs, files in os.walk(onedrive_path):
            for f in files:
                full = os.path.join(root, f)
                problems = check_file(full, onedrive_path, report)
                stats['files_scanned'] += 1
                
                num_issues = len(problems['issues'])
                num_warnings = len(problems['warnings'])
                
                stats['total_issues'] += num_issues
                stats['total_warnings'] += num_warnings
                
                if num_issues > 0:
                    stats['files_with_issues'] += 1
                elif num_warnings > 0:
                    stats['files_with_only_warnings'] += 1

        sync_limit = 10 if args.test_mode else MAX_SYNC_FILES_LIMIT
        if stats['files_scanned'] > sync_limit:
            warning_msg = f"\n[ALERT] Performance Warning: This folder contains {stats['files_scanned']} items, which exceeds Microsoft's recommended sync limit of {sync_limit} items.\nSyncing more than {MAX_SYNC_FILES_LIMIT} items can cause significant performance degradation.\n"
            report.write("========================================\n")
            report.write("!!!!! CRITICAL PERFORMANCE ALERT !!!!!\n")
            report.write(warning_msg)
            report.write("========================================\n\n")
            print(warning_msg)

        report.write("----------------------------------------\n")
        report.write("SCAN SUMMARY\n")
        report.write("----------------------------------------\n")
        report.write(f"Number of files scanned: {stats['files_scanned']}\n")
        report.write(f"Number of files with issues: {stats['files_with_issues']}\n")
        report.write(f"Number of files with only warnings: {stats['files_with_only_warnings']}\n")
        report.write(f"Total number of issues in all files: {stats['total_issues']}\n")
        report.write(f"Total number of warnings in all files: {stats['total_warnings']}\n")

    print(f"Diagnosis completed. View the file: {report_file}")

if __name__ == "__main__":
    main()