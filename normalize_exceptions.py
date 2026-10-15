#!/usr/bin/env python3
"""Normalize Corrigan Peak's exception export without inventing missing data.

Usage: python normalize_exceptions.py exceptions.csv --output-dir output
Requires only Python 3.9+ standard library.
"""
import argparse
import csv
import json
from collections import Counter
from datetime import datetime
from pathlib import Path

EXPECTED_COLUMNS = {"exception_id", "terminal", "event_type", "carrier_code", "event_ts"}
DATE_FORMATS = ("%Y-%m-%d %H:%M:%S", "%m/%d/%Y %H:%M", "%Y-%m-%dT%H:%M:%SZ")


def normalize_terminal(raw):
    token = " ".join(raw.strip().lower().split())
    aliases = {"t3": "Terminal 3", "terminal 3": "Terminal 3"}
    return aliases.get(token)


def normalize_timestamp(raw):
    raw = raw.strip()
    for fmt in DATE_FORMATS:
        try:
            parsed = datetime.strptime(raw, fmt)
            # A Z suffix explicitly signifies UTC. Other input timestamps have
            # unspecified timezone; do not silently reinterpret them as UTC.
            is_utc = fmt.endswith("Z")
            return parsed.strftime("%Y-%m-%dT%H:%M:%S") + ("Z" if is_utc else ""), is_utc
        except ValueError:
            continue
    return None, False


def clean(rows):
    output = []
    warnings = []
    counts = Counter()
    for line_number, row in enumerate(rows, start=2):
        rid = (row.get("exception_id") or "").strip()
        event = (row.get("event_type") or "").strip().lower()
        terminal = normalize_terminal(row.get("terminal") or "")
        carrier = (row.get("carrier_code") or "").strip().upper()
        timestamp, explicit_utc = normalize_timestamp(row.get("event_ts") or "")
        if not terminal:
            warnings.append({"row": line_number, "exception_id": rid, "field": "terminal", "issue": "Unrecognized terminal; cannot safely normalize"})
        if not carrier:
            warnings.append({"row": line_number, "exception_id": rid, "field": "carrier_code", "issue": "Carrier code missing; requires source correction"})
        if not timestamp:
            warnings.append({"row": line_number, "exception_id": rid, "field": "event_ts", "issue": "Unrecognized timestamp format"})
        elif not explicit_utc:
            warnings.append({"row": line_number, "exception_id": rid, "field": "event_ts", "issue": "Source timezone unspecified; local clock time retained, not converted to UTC"})
        cleaned = {"exception_id": rid, "terminal": terminal or "", "event_type": event,
                   "carrier_code": carrier, "event_ts": timestamp or ""}
        output.append(cleaned)
        if event:
            counts[event] += 1
        else:
            warnings.append({"row": line_number, "exception_id": rid, "field": "event_type", "issue": "Missing event type; excluded from summary"})
    return output, counts, warnings


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input_csv", type=Path)
    parser.add_argument("--output-dir", type=Path, default=Path("output"))
    args = parser.parse_args()
    with args.input_csv.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames or not EXPECTED_COLUMNS.issubset(reader.fieldnames):
            parser.error("CSV must have columns: " + ", ".join(sorted(EXPECTED_COLUMNS)))
        cleaned, counts, warnings = clean(reader)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    with (args.output_dir / "cleaned_exceptions.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=sorted(EXPECTED_COLUMNS))
        writer.writeheader()
        writer.writerows(cleaned)
    with (args.output_dir / "event_summary.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["event_type", "count"])
        writer.writerows(sorted(counts.items()))
    (args.output_dir / "data_quality_notes.json").write_text(json.dumps(warnings, indent=2) + "\n", encoding="utf-8")
    print(f"Processed {len(cleaned)} rows")
    for event, count in sorted(counts.items()):
        print(f"  {event}: {count}")
    print(f"Data-quality warnings: {len(warnings)} (see data_quality_notes.json)")


if __name__ == "__main__":
    main()
