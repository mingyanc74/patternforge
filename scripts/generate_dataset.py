"""Streaming, deterministic CSV/XLSX fixtures. Does not upload or contact any external service."""

import argparse
import csv
import json
from pathlib import Path


def rows(count):
    for i in range(count):
        email = "\\N" if i % 10 == 0 else "not-an-email" if i % 10 == 1 else f"user{i}@example.com"
        yield [
            str(i).zfill(8),
            f"  USER   {i}  ",
            email,
            f"Order ORD-{i} shipped",
            "Sydney",
            "AU",
            "+61 400 123 456",
            "active",
            "2026-10-19",
            "Customer record",
        ]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--rows", type=int, default=1000)
    parser.add_argument("--output", type=Path, default=Path("data/fixtures/customers.csv"))
    args = parser.parse_args()
    if args.rows < 0:
        parser.error("rows must be nonnegative")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    headers = ["ID", "Name", "Email", "Description", "City", "Country", "Phone", "Status", "Date", "Notes"]
    if args.output.suffix.lower() == ".xlsx":
        from openpyxl import Workbook

        workbook = Workbook(write_only=True)
        sheet = workbook.create_sheet("Customers")
        sheet.append(headers)
        for row in rows(args.rows):
            sheet.append([None if value == "\\N" else value for value in row])
        workbook.save(args.output)
    else:
        with args.output.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.writer(stream)
            writer.writerow(headers)
            writer.writerows(rows(args.rows))
    expected = sum(1 for i in range(10) if i not in (0, 1)) * (args.rows // 10) + sum(
        1 for i in range(args.rows % 10) if i not in (0, 1)
    )
    meta = {
        "rows": args.rows,
        "email_changed_cells": expected,
        "null_encoding_csv": "\\N",
        "bytes": args.output.stat().st_size,
    }
    args.output.with_suffix(args.output.suffix + ".expected.json").write_text(
        json.dumps(meta, indent=2), encoding="utf-8"
    )
    print(json.dumps({"file": str(args.output), **meta}, indent=2))


if __name__ == "__main__":
    main()
