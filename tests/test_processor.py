from pathlib import Path

import pandas as pd
import pytest

from ticket_pipeline import (
    EmptyDatasetError,
    InvalidCSVError,
    MissingColumnsError,
    TicketDataProcessor,
    build_analytics,
)


REQUIRED_HEADER = (
    "ticket_id,category,priority,description,resolution_time_hours,"
    "customer_rating,status\n"
)


def write_csv(path: Path, content: str) -> Path:
    path.write_text(content, encoding="utf-8")
    return path


def test_valid_input_is_cleaned_and_raw_file_is_unchanged(tmp_path: Path) -> None:
    raw_path = write_csv(
        tmp_path / "tickets.csv",
        REQUIRED_HEADER + "T-1,billing,high,Refund,2,5,resolved\n",
    )
    original_text = raw_path.read_text(encoding="utf-8")
    output_path = tmp_path / "cleaned" / "cleaned_tickets.csv"

    processor = TicketDataProcessor(raw_path, output_path)
    cleaned = processor.process()
    saved_path = processor.save_cleaned_data(cleaned)

    assert len(cleaned) == 1
    assert cleaned.loc[0, "ticket_id"] == "T-1"
    assert pd.api.types.is_float_dtype(cleaned["resolution_time_hours"])
    assert saved_path.exists()
    assert raw_path.read_text(encoding="utf-8") == original_text


def test_invalid_csv_raises_clear_exception(tmp_path: Path) -> None:
    path = write_csv(tmp_path / "bad.csv", 'ticket_id,category\n"unfinished,billing\n')
    processor = TicketDataProcessor(path)

    with pytest.raises(InvalidCSVError, match="Could not read a valid CSV"):
        processor.process()


def test_empty_dataset_raises_clear_exception(tmp_path: Path) -> None:
    path = write_csv(tmp_path / "empty.csv", REQUIRED_HEADER)
    processor = TicketDataProcessor(path)

    with pytest.raises(EmptyDatasetError, match="contains no ticket rows"):
        processor.process()


def test_missing_required_columns_are_reported(tmp_path: Path) -> None:
    path = write_csv(tmp_path / "missing.csv", "ticket_id,category\nT-1,billing\n")
    processor = TicketDataProcessor(path)

    with pytest.raises(MissingColumnsError) as error:
        processor.process()

    assert "priority" in str(error.value)
    assert "status" in str(error.value)


def test_duplicate_ids_keep_first_and_are_reported(tmp_path: Path) -> None:
    path = write_csv(
        tmp_path / "duplicates.csv",
        REQUIRED_HEADER
        + "T-1,billing,high,First,2,5,resolved\n"
        + "T-1,billing,low,Second,9,1,open\n",
    )
    processor = TicketDataProcessor(path)
    cleaned = processor.process()

    assert len(cleaned) == 1
    assert cleaned.loc[0, "description"] == "First"
    assert processor.report["duplicate_ticket_ids"] == ["T-1"]
    assert processor.report["duplicate_rows_removed"] == 1


def test_invalid_numeric_values_become_missing_and_are_counted(tmp_path: Path) -> None:
    path = write_csv(
        tmp_path / "numeric.csv",
        REQUIRED_HEADER
        + "T-1,billing,high,Bad time,not-a-number,5,resolved\n"
        + "T-2,billing,low,Negative time,-1,6,open\n",
    )
    processor = TicketDataProcessor(path)
    cleaned = processor.process()

    assert cleaned["resolution_time_hours"].isna().sum() == 2
    assert cleaned["customer_rating"].isna().sum() == 1
    assert processor.report["invalid_numeric_values"] == {
        "resolution_time_hours": 2,
        "customer_rating": 1,
    }


def test_missing_ticket_id_is_dropped_and_missing_text_gets_placeholder(
    tmp_path: Path,
) -> None:
    path = write_csv(
        tmp_path / "missing_values.csv",
        REQUIRED_HEADER
        + ",billing,high,No identifier,1,5,resolved\n"
        + "T-2,,, ,2,4,\n",
    )
    processor = TicketDataProcessor(path)
    cleaned = processor.process()

    assert len(cleaned) == 1
    assert cleaned.loc[0, "category"] == "unknown"
    assert cleaned.loc[0, "priority"] == "unknown"
    assert cleaned.loc[0, "status"] == "unknown"
    assert cleaned.loc[0, "description"] == ""
    assert processor.report["rows_dropped_missing_ticket_id"] == 1


def test_processor_refuses_to_overwrite_raw_csv(tmp_path: Path) -> None:
    raw_path = write_csv(
        tmp_path / "tickets.csv",
        REQUIRED_HEADER + "T-1,billing,high,Refund,2,5,resolved\n",
    )
    processor = TicketDataProcessor(raw_path)
    cleaned = processor.process()

    with pytest.raises(ValueError, match="Refusing to overwrite"):
        processor.save_cleaned_data(cleaned, raw_path)


def test_duplicate_policy_can_fail_closed(tmp_path: Path) -> None:
    path = write_csv(
        tmp_path / "duplicates.csv",
        REQUIRED_HEADER
        + "T-1,billing,high,First,2,5,resolved\n"
        + "T-1,billing,low,Second,9,1,open\n",
    )
    processor = TicketDataProcessor(path, duplicate_policy="raise")

    with pytest.raises(ValueError, match="Duplicate ticket IDs found"):
        processor.process()


def test_analytics_calculates_priority_rating_and_unresolved_count(
    tmp_path: Path,
) -> None:
    path = write_csv(
        tmp_path / "analytics.csv",
        REQUIRED_HEADER
        + "T-1,billing,high,Refund,2,5,resolved\n"
        + "T-2,billing,low,Invoice,4,3,open\n",
    )
    processor = TicketDataProcessor(path)
    cleaned = processor.process()
    analytics = build_analytics(cleaned, processor.report)

    assert analytics["ticket_count_by_priority"] == {"high": 1, "low": 1}
    assert analytics["average_resolution_time_hours_by_category"] == {"billing": 3.0}
    assert analytics["average_customer_rating"] == 4.0
    assert analytics["unresolved_ticket_count"] == 1
