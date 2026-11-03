"""Run the Day 1 support-ticket pipeline from the repository root."""

from __future__ import annotations

import json
import sys
from csv import DictWriter
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from ticket_pipeline import TicketDataProcessor, build_analytics


RAW_CSV = ROOT / "data" / "tickets.csv"
CLEAN_CSV = ROOT / "data" / "cleaned_tickets.csv"
QUALITY_CSV = ROOT / "data" / "quality_issues.csv"


def main() -> None:
    processor = TicketDataProcessor(RAW_CSV, output_path=CLEAN_CSV)
    cleaned = processor.process()
    saved_path = processor.save_cleaned_data(cleaned)
    report = build_analytics(cleaned, processor.report)

    with QUALITY_CSV.open("w", newline="", encoding="utf-8") as quality_file:
        writer = DictWriter(
            quality_file, fieldnames=["source_record_number", "issues"]
        )
        writer.writeheader()
        for row_index, reasons in processor.report["invalid_record_reasons"].items():
            writer.writerow(
                {
                    "source_record_number": int(row_index) + 1,
                    "issues": ";".join(reasons),
                }
            )

    print(f"Cleaned dataset saved to: {saved_path.relative_to(ROOT)}")
    print(f"Row-level quality issues saved to: {QUALITY_CSV.relative_to(ROOT)}")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
