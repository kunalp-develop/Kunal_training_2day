"""Run the support-ticket pipeline on data/tickets.csv. Wiring only: no rules live here."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
# Lets the script run from a fresh checkout without `pip install -e .`.
sys.path.insert(0, str(ROOT / "src"))

from ticket_pipeline import (  # noqa: E402  (import after the sys.path line above)
    CleanedCsvWriter,
    CsvTicketLoader,
    QualityReportWriter,
    TicketPipeline,
)

RAW_CSV = ROOT / "data" / "tickets.csv"
CLEAN_CSV = ROOT / "data" / "cleaned_tickets.csv"
QUALITY_CSV = ROOT / "data" / "quality_issues.csv"


def main() -> None:
    result = TicketPipeline(CsvTicketLoader(RAW_CSV)).run()

    saved = CleanedCsvWriter(CLEAN_CSV, protected=[RAW_CSV]).write(result.frame)
    issues = QualityReportWriter(QUALITY_CSV).write(result.report)

    print(f"Cleaned dataset saved to: {saved.relative_to(ROOT)}")
    print(f"Row-level quality issues saved to: {issues.relative_to(ROOT)}")
    print(json.dumps(result.analytics, indent=2))


if __name__ == "__main__":
    main()
