"""Regression tests for CSV rows whose field count does not match the header.

Day 1 review P0: a row with one extra field made pandas use the first value
as the row index, silently shifting every column one place to the left.
"""

from pathlib import Path

import pytest

from ticket_pipeline import InvalidCSVError, TicketDataProcessor


REQUIRED_HEADER = (
    "ticket_id,category,priority,description,resolution_time_hours,"
    "customer_rating,status\n"
)


def write_csv(path: Path, content: str) -> Path:
    path.write_text(content, encoding="utf-8")
    return path


def test_row_with_extra_field_is_rejected_with_line_number(tmp_path: Path) -> None:
    # Exact reproducer from the Day 1 review report.
    path = write_csv(
        tmp_path / "extra_field.csv",
        REQUIRED_HEADER + "T-101,Billing,High,Valid,2,5,Closed,UNEXPECTED\n",
    )

    with pytest.raises(InvalidCSVError, match=r"line 2.*expected 7 fields, found 8"):
        TicketDataProcessor(path).process()


def test_row_with_missing_field_is_rejected(tmp_path: Path) -> None:
    path = write_csv(
        tmp_path / "short_row.csv",
        REQUIRED_HEADER
        + "T-1,billing,high,Valid,2,5,resolved\n"
        + "T-2,billing,high,Too short,2,5\n",
    )

    with pytest.raises(InvalidCSVError, match=r"line 3.*expected 7 fields, found 6"):
        TicketDataProcessor(path).process()


def test_blank_lines_are_ignored_not_rejected(tmp_path: Path) -> None:
    path = write_csv(
        tmp_path / "blank_lines.csv",
        REQUIRED_HEADER + "T-1,billing,high,Valid,2,5,resolved\n\n",
    )

    cleaned = TicketDataProcessor(path).process()

    assert cleaned["ticket_id"].tolist() == ["T-1"]
