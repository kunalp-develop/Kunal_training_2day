"""CsvTicketLoader: reads files and reports malformed input clearly.

Includes the Day 1 review P0: a row with one extra field made pandas use the
first value as the row index, silently shifting every column one place left.
"""

from pathlib import Path

import pytest

from ticket_pipeline.errors import EmptyDatasetError, InvalidCSVError
from ticket_pipeline.loading import CsvTicketLoader

from conftest import REQUIRED_HEADER, write_csv


def test_valid_file_loads_every_row_and_column(tmp_path: Path) -> None:
    path = write_csv(
        tmp_path / "ok.csv",
        REQUIRED_HEADER
        + "T-1,billing,high,Refund,2,5,resolved\n"
        + "T-2,account,low,Email,1,4,open\n",
    )

    frame = CsvTicketLoader(path).load()

    assert frame.shape == (2, 7)
    assert frame["ticket_id"].tolist() == ["T-1", "T-2"]


def test_na_like_text_is_kept_and_only_empty_cells_are_missing(tmp_path: Path) -> None:
    path = write_csv(tmp_path / "na.csv", REQUIRED_HEADER + "NA,N/A,,None,,5,NULL\n")

    row = CsvTicketLoader(path).load().iloc[0]

    assert (row["ticket_id"], row["category"], row["description"], row["status"]) == (
        "NA",
        "N/A",
        "None",
        "NULL",
    )
    assert row.isna()[["priority", "resolution_time_hours"]].all()


def test_row_with_extra_field_is_rejected_with_line_number(tmp_path: Path) -> None:
    # Exact reproducer from the Day 1 review report.
    path = write_csv(
        tmp_path / "extra_field.csv",
        REQUIRED_HEADER + "T-101,Billing,High,Valid,2,5,Closed,UNEXPECTED\n",
    )

    with pytest.raises(InvalidCSVError, match=r"line 2 expected 7 fields, found 8"):
        CsvTicketLoader(path).load()


def test_row_with_missing_field_is_rejected(tmp_path: Path) -> None:
    path = write_csv(
        tmp_path / "short_row.csv",
        REQUIRED_HEADER
        + "T-1,billing,high,Valid,2,5,resolved\n"
        + "T-2,billing,high,Too short,2,5\n",
    )

    with pytest.raises(InvalidCSVError, match=r"line 3 expected 7 fields, found 6"):
        CsvTicketLoader(path).load()


def test_quoted_commas_are_not_counted_as_extra_fields(tmp_path: Path) -> None:
    path = write_csv(
        tmp_path / "quoted.csv",
        REQUIRED_HEADER + 'T-1,billing,high,"Refund, then invoice",2,5,resolved\n',
    )

    assert CsvTicketLoader(path).load().loc[0, "description"] == "Refund, then invoice"


def test_blank_lines_are_ignored_not_rejected(tmp_path: Path) -> None:
    path = write_csv(
        tmp_path / "blank_lines.csv",
        REQUIRED_HEADER + "T-1,billing,high,Valid,2,5,resolved\n\n",
    )

    assert CsvTicketLoader(path).load()["ticket_id"].tolist() == ["T-1"]


def test_unclosed_quote_is_invalid_csv(tmp_path: Path) -> None:
    path = write_csv(tmp_path / "bad.csv", 'ticket_id,category\n"unfinished,billing\n')

    with pytest.raises(InvalidCSVError, match="Could not read a valid CSV"):
        CsvTicketLoader(path).load()


def test_empty_file_is_an_empty_dataset(tmp_path: Path) -> None:
    path = write_csv(tmp_path / "empty.csv", "")

    with pytest.raises(EmptyDatasetError, match="no header row"):
        CsvTicketLoader(path).load()


def test_header_only_file_is_an_empty_dataset(tmp_path: Path) -> None:
    path = write_csv(tmp_path / "header_only.csv", REQUIRED_HEADER)

    with pytest.raises(EmptyDatasetError, match="contains no ticket rows"):
        CsvTicketLoader(path).load()


def test_missing_file_is_invalid_csv(tmp_path: Path) -> None:
    with pytest.raises(InvalidCSVError, match="Could not read a valid CSV"):
        CsvTicketLoader(tmp_path / "does_not_exist.csv").load()


def test_non_utf8_bytes_are_invalid_csv(tmp_path: Path) -> None:
    path = tmp_path / "latin1.csv"
    path.write_bytes(REQUIRED_HEADER.encode() + "T-1,billing,high,Café,2,5,resolved\n".encode("latin-1"))

    with pytest.raises(InvalidCSVError, match="Could not read a valid CSV"):
        CsvTicketLoader(path).load()
