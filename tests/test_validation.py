"""Validation rules: they flag problems but never change data."""

import math

import pandas as pd
import pytest

from ticket_pipeline.errors import MissingColumnsError
from ticket_pipeline.schema import CUSTOMER_RATING_RULE, RESOLUTION_TIME_RULE, NumericRule
from ticket_pipeline.validation import (
    SchemaValidator,
    check_numeric,
    unrecognised_priority_mask,
)


def test_schema_validator_accepts_all_required_columns() -> None:
    SchemaValidator(["a", "b"]).validate(pd.DataFrame(columns=["b", "a", "extra"]))


def test_schema_validator_lists_every_missing_column_sorted() -> None:
    with pytest.raises(MissingColumnsError, match="Missing required column\\(s\\): priority, status"):
        SchemaValidator(["ticket_id", "status", "priority"]).validate(
            pd.DataFrame(columns=["ticket_id"])
        )


@pytest.mark.parametrize(
    ("rule", "value", "expected"),
    [
        (RESOLUTION_TIME_RULE, 0.0, True),
        (RESOLUTION_TIME_RULE, -0.1, False),
        (RESOLUTION_TIME_RULE, math.inf, False),
        (CUSTOMER_RATING_RULE, 1.0, True),
        (CUSTOMER_RATING_RULE, 5.0, True),
        (CUSTOMER_RATING_RULE, 5.01, False),
        (CUSTOMER_RATING_RULE, math.nan, False),
    ],
)
def test_numeric_rule_boundaries(rule: NumericRule, value: float, expected: bool) -> None:
    assert rule.accepts(value) is expected


def test_numeric_rule_describes_itself() -> None:
    assert CUSTOMER_RATING_RULE.description == "must be a finite number between 1 and 5, inclusive"
    assert RESOLUTION_TIME_RULE.description == (
        "must be a finite number greater than or equal to 0"
    )


def test_check_numeric_flags_text_non_finite_and_out_of_range_but_not_missing() -> None:
    series = pd.Series(["2", "bad", None, "inf", "-1", "0"], index=[10, 11, 12, 13, 14, 15])

    check = check_numeric(series, RESOLUTION_TIME_RULE)

    assert check.invalid.tolist() == [False, True, False, True, True, False]
    assert check.values.dtype == "float64"
    assert check.values.index.tolist() == [10, 11, 12, 13, 14, 15]  # source rows kept
    assert pd.isna(check.values[12])  # missing stays missing


def test_unrecognised_priority_mask_ignores_missing_and_known_values() -> None:
    priorities = pd.Series(["high", "urgent", None, "unknown", "low"], dtype="string")

    assert unrecognised_priority_mask(priorities).tolist() == [False, True, False, False, False]
