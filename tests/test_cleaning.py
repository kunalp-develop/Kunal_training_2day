"""TicketCleaner works on in-memory DataFrames: no files are needed to test it."""

import pandas as pd
import pytest

from ticket_pipeline.cleaning import TicketCleaner
from ticket_pipeline.errors import DuplicateTicketError, MissingColumnsError
from ticket_pipeline.models import DuplicatePolicy
from ticket_pipeline.schema import REQUIRED_COLUMNS


def raw_frame(*rows: tuple) -> pd.DataFrame:
    return pd.DataFrame(list(rows), columns=list(REQUIRED_COLUMNS))


def test_text_is_trimmed_and_case_normalised() -> None:
    result = TicketCleaner().clean(raw_frame((" t-1 ", " Billing ", "HIGH", " Refund ", 2, 5, "Resolved")))

    row = result.frame.iloc[0]
    assert (row["ticket_id"], row["category"], row["priority"], row["status"]) == (
        "T-1",
        "billing",
        "high",
        "resolved",
    )
    assert row["description"] == "Refund"


def test_missing_id_row_is_dropped_and_reported() -> None:
    result = TicketCleaner().clean(
        raw_frame((None, "billing", "high", "x", 1, 5, "resolved"), ("T-2", "billing", "low", "y", 2, 4, "open"))
    )

    assert result.frame["ticket_id"].tolist() == ["T-2"]
    assert result.report.rows_dropped_missing_ticket_id == 1
    assert result.report.invalid_record_reasons == {"0": ["missing_ticket_id"]}


def test_whitespace_only_id_counts_as_missing() -> None:
    result = TicketCleaner().clean(raw_frame(("   ", "billing", "high", "x", 1, 5, "resolved")))

    assert result.frame.empty
    assert result.report.rows_dropped_missing_ticket_id == 1


def test_duplicates_keep_first_occurrence_by_default() -> None:
    result = TicketCleaner().clean(
        raw_frame(("T-1", "billing", "high", "First", 2, 5, "resolved"), ("t-1", "billing", "low", "Second", 9, 1, "open"))
    )

    assert result.frame["description"].tolist() == ["First"]
    assert result.report.duplicate_ticket_ids == ("T-1",)
    assert result.report.duplicate_rows_removed == 1
    assert result.report.invalid_record_reasons == {"1": ["duplicate_ticket_id"]}


def test_duplicates_can_fail_closed() -> None:
    cleaner = TicketCleaner(DuplicatePolicy.RAISE)

    with pytest.raises(DuplicateTicketError, match="T-1"):
        cleaner.clean(raw_frame(("T-1", "a", "high", "x", 1, 5, "open"), ("T-1", "a", "low", "y", 1, 5, "open")))


def test_invalid_numbers_become_missing_and_are_counted_per_column() -> None:
    result = TicketCleaner().clean(
        raw_frame(
            ("T-1", "billing", "high", "x", "bad", 5, "resolved"),
            ("T-2", "billing", "low", "y", -1, 6, "open"),
            ("T-3", "billing", "low", "z", "inf", 3, "open"),
        )
    )

    assert result.frame["resolution_time_hours"].isna().all()
    assert result.frame["customer_rating"].tolist()[0] == 5.0
    assert pd.isna(result.frame.loc[1, "customer_rating"])
    assert result.report.invalid_numeric_values == {"resolution_time_hours": 3, "customer_rating": 1}
    assert result.report.invalid_record_reasons["1"] == [
        "invalid_customer_rating",
        "invalid_resolution_time_hours",
    ]


def test_unrecognised_priority_becomes_unknown_and_is_reported() -> None:
    result = TicketCleaner().clean(raw_frame(("T-1", "billing", "Urgent", "x", 1, 5, "open")))

    assert result.frame.loc[0, "priority"] == "unknown"
    assert result.report.invalid_record_reasons == {"0": ["invalid_priority"]}


def test_missing_text_gets_placeholders_but_numbers_stay_missing() -> None:
    result = TicketCleaner().clean(raw_frame(("T-1", None, None, None, None, None, None)))

    row = result.frame.iloc[0]
    assert (row["category"], row["priority"], row["status"], row["description"]) == (
        "unknown",
        "unknown",
        "unknown",
        "",
    )
    assert pd.isna(row["resolution_time_hours"]) and pd.isna(row["customer_rating"])
    assert result.report.missing_values_after_cleaning["customer_rating"] == 1
    assert result.report.missing_values_before_cleaning["category"] == 1


def test_raw_frame_is_not_modified() -> None:
    raw = raw_frame((" t-1 ", "Billing", "HIGH", "x", "bad", 5, "open"))
    snapshot = raw.copy(deep=True)

    TicketCleaner().clean(raw)

    pd.testing.assert_frame_equal(raw, snapshot)


def test_same_cleaner_can_clean_twice_without_leftover_state() -> None:
    cleaner = TicketCleaner()
    first = cleaner.clean(raw_frame(("T-1", "a", "high", "x", "bad", 5, "open")))
    second = cleaner.clean(raw_frame(("T-2", "a", "high", "x", 1, 5, "open")))

    assert first.report.invalid_record_count == 1
    assert second.report.invalid_record_count == 0


def test_missing_columns_are_rejected_before_cleaning() -> None:
    with pytest.raises(MissingColumnsError, match="status"):
        TicketCleaner().clean(pd.DataFrame({"ticket_id": ["T-1"]}))


def test_policy_accepts_the_plain_string_value_too() -> None:
    assert TicketCleaner("raise").duplicate_policy is DuplicatePolicy.RAISE
