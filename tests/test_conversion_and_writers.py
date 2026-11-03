"""frame_to_tickets (DataFrame -> model boundary) and the output writers."""

from pathlib import Path

import pandas as pd
import pytest

from ticket_pipeline.cleaning import TicketCleaner
from ticket_pipeline.conversion import frame_to_tickets
from ticket_pipeline.errors import InvalidTicketError
from ticket_pipeline.models import Priority
from ticket_pipeline.schema import REQUIRED_COLUMNS
from ticket_pipeline.writers import CleanedCsvWriter, QualityReportWriter


def cleaned(*rows: tuple):
    return TicketCleaner().clean(pd.DataFrame(list(rows), columns=list(REQUIRED_COLUMNS)))


def test_cleaned_rows_become_tickets_with_none_for_missing_numbers() -> None:
    result = cleaned(("T-1", "billing", "high", "x", 2, None, "resolved"))

    (ticket,) = frame_to_tickets(result.frame)

    assert ticket.priority is Priority.HIGH
    assert ticket.resolution_time_hours == 2.0
    assert ticket.customer_rating is None


def test_a_row_cleaning_should_have_fixed_fails_loudly() -> None:
    broken = pd.DataFrame([["T-1", "billing", "high", "x", -5.0, 5.0, "open"]], columns=list(REQUIRED_COLUMNS))

    with pytest.raises(InvalidTicketError, match="cleaned row 0"):
        frame_to_tickets(broken)


def test_cleaned_writer_saves_csv_and_creates_folders(tmp_path: Path) -> None:
    result = cleaned(("T-1", "billing", "high", "x", 2, 5, "resolved"))
    destination = tmp_path / "out" / "cleaned.csv"

    CleanedCsvWriter(destination).write(result.frame)

    assert pd.read_csv(destination)["ticket_id"].tolist() == ["T-1"]


def test_cleaned_writer_refuses_to_overwrite_protected_raw_file(tmp_path: Path) -> None:
    raw = tmp_path / "tickets.csv"
    raw.write_text("original", encoding="utf-8")

    with pytest.raises(ValueError, match="Refusing to overwrite"):
        CleanedCsvWriter(raw, protected=[raw]).write(pd.DataFrame({"a": [1]}))

    assert raw.read_text(encoding="utf-8") == "original"


def test_quality_writer_uses_one_based_record_numbers(tmp_path: Path) -> None:
    result = cleaned(
        ("T-1", "billing", "high", "x", 2, 5, "resolved"),
        ("T-2", "billing", "high", "x", "bad", 9, "resolved"),
    )

    path = QualityReportWriter(tmp_path / "issues.csv").write(result.report)

    assert path.read_text(encoding="utf-8").splitlines() == [
        "source_record_number,issues",
        "2,invalid_customer_rating;invalid_resolution_time_hours",
    ]
