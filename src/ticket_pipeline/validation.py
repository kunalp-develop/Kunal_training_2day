"""Decide which values are invalid. Deciding what to *do* about them is cleaning's job."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

import numpy as np
import pandas as pd

from .errors import MissingColumnsError
from .models import Priority
from .schema import REQUIRED_COLUMNS, NumericRule

KNOWN_PRIORITIES: frozenset[str] = frozenset(priority.value for priority in Priority)


class SchemaValidator:
    """Check that every required column is present."""

    def __init__(self, required_columns: Iterable[str] = REQUIRED_COLUMNS) -> None:
        self.required_columns = tuple(required_columns)

    def validate(self, frame: pd.DataFrame) -> None:
        missing = sorted(set(self.required_columns).difference(frame.columns))
        if missing:
            raise MissingColumnsError("Missing required column(s): " + ", ".join(missing))


@dataclass(frozen=True)
class NumericCheck:
    """Result of checking one column: parsed numbers plus a mask of bad values."""

    values: pd.Series  # float64, NaN where the cell was empty or unparseable
    invalid: pd.Series  # True where the cell had a value that breaks the rule


def check_numeric(series: pd.Series, rule: NumericRule) -> NumericCheck:
    """Parse ``series`` as numbers and flag text, non-finite and out-of-range values.

    Empty cells are *missing*, not invalid, so they are not flagged.
    """
    parsed = pd.to_numeric(series, errors="coerce")
    values = pd.Series(
        parsed.to_numpy(dtype=float, na_value=np.nan), index=series.index, dtype="float64"
    )
    unparseable = series.notna() & values.isna()
    present = values.notna()
    breaks_rule = pd.Series(False, index=series.index)
    breaks_rule[present] = ~values[present].map(rule.accepts).astype(bool)
    return NumericCheck(values=values, invalid=unparseable | breaks_rule)


def unrecognised_priority_mask(priorities: pd.Series) -> pd.Series:
    """True for normalised priority text that is present but not a known Priority."""
    return priorities.notna() & ~priorities.isin(KNOWN_PRIORITIES)
