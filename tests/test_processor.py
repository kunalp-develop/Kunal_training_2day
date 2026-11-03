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


def test_na_like_text_values_are_preserved_but_empty_cells_are_missing(
    tmp_path: Path,
) -> None:
    path = write_csv(
        tmp_path / "na_like_values.csv",
        REQUIRED_HEADER
        + "NA,N/A,high,Description: NULL,2,5,resolved\n"
        + "T-2,,low,None,3,4,open\n"
        + "T-3,account,medium,Empty description,,3,resolved\n",
    )
    processor = TicketDataProcessor(path)

    cleaned = processor.process()

    assert cleaned["ticket_id"].tolist() == ["NA", "T-2", "T-3"]
    assert cleaned.loc[0, "category"] == "n/a"
    assert cleaned.loc[0, "description"] == "Description: NULL"
    assert cleaned.loc[1, "description"] == "None"
    assert cleaned.loc[1, "category"] == "unknown"
    assert pd.isna(cleaned.loc[2, "resolution_time_hours"])
    assert processor.report["rows_dropped_missing_ticket_id"] == 0


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


def test_non_finite_resolution_times_are_flagged_without_affecting_analytics(
    tmp_path: Path,
) -> None:
    path = write_csv(
        tmp_path / "non_finite.csv",
        REQUIRED_HEADER
        + "T-1,billing,high,Positive infinity,inf,5,resolved\n"
        + "T-2,billing,low,Negative infinity,-inf,4,resolved\n"
        + "T-3,billing,medium,Valid time,2.0,3,resolved\n"
        + "T-4,billing,low,Missing time,,2,resolved\n",
    )
    processor = TicketDataProcessor(path)
    cleaned = processor.process()
    analytics = build_analytics(cleaned, processor.report)

    assert cleaned["resolution_time_hours"].iloc[:2].isna().all()
    assert cleaned["resolution_time_hours"].iloc[2] == 2.0
    assert pd.isna(cleaned["resolution_time_hours"].iloc[3])
    assert processor.report["invalid_numeric_values"]["resolution_time_hours"] == 2
    assert processor.report["invalid_record_reasons"] == {
        "0": ["invalid_resolution_time_hours"],
        "1": ["invalid_resolution_time_hours"],
    }
    assert analytics["average_resolution_time_hours_by_category"] == {"billing": 2.0}


def test_invalid_record_reasons_are_ordered_by_source_record(
    tmp_path: Path,
) -> None:
    records = [REQUIRED_HEADER.rstrip("\n")]
    for record_number in range(1, 12):
        resolution_time = (
            "inf" if record_number == 3 else "-inf" if record_number == 11 else "1"
        )
        records.append(
            f"T-{record_number},billing,high,Ticket {record_number},"
            f"{resolution_time},5,resolved"
        )
    path = write_csv(tmp_path / "ordered_issues.csv", "\n".join(records) + "\n")
    processor = TicketDataProcessor(path)

    processor.process()

    assert list(processor.report["invalid_record_reasons"]) == ["2", "10"]


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
