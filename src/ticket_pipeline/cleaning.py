"""Apply the cleaning policy to a raw ticket DataFrame.

``TicketCleaner.clean`` returns its report together with the cleaned frame.
Nothing is stored on the cleaner, so it is never half-initialised and the
same instance can safely clean many files.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

import pandas as pd

from .errors import DuplicateTicketError
from .models import CleaningReport, DuplicatePolicy, ValidationIssue
from .schema import NUMERIC_RULES, TEXT_COLUMNS, UNKNOWN, NumericRule
from .validation import SchemaValidator, check_numeric, unrecognised_priority_mask


@dataclass(frozen=True)
class CleaningResult:
    frame: pd.DataFrame
    report: CleaningReport


def _normalise_text(series: pd.Series) -> pd.Series:
    """Trim text and treat whitespace-only cells as missing."""
    values = series.astype("string").str.strip()
    return values.mask(values.eq(""))


def _issues(mask: pd.Series, reason: str) -> list[ValidationIssue]:
    return [ValidationIssue(int(index), reason) for index in mask.index[mask.fillna(False)]]


class TicketCleaner:
    """Normalise text, drop untrackable rows, mask bad numbers, fill placeholders."""

    def __init__(
        self,
        duplicate_policy: DuplicatePolicy = DuplicatePolicy.KEEP_FIRST,
        numeric_rules: Iterable[NumericRule] = NUMERIC_RULES,
        schema_validator: SchemaValidator | None = None,
    ) -> None:
        self.duplicate_policy = DuplicatePolicy(duplicate_policy)
        self.numeric_rules = tuple(numeric_rules)
        self.schema_validator = schema_validator or SchemaValidator()

    def clean(self, raw: pd.DataFrame) -> CleaningResult:
        self.schema_validator.validate(raw)
        missing_before = raw.isna().sum().astype(int).to_dict()
        issues: list[ValidationIssue] = []

        frame = self._normalise(raw)

        # A row without an ID cannot be tracked or de-duplicated, so it is dropped.
        missing_id = frame["ticket_id"].isna()
        issues += _issues(missing_id, "missing_ticket_id")
        frame = frame.loc[~missing_id].copy()

        frame, duplicate_ids, duplicates_removed = self._drop_duplicates(frame, issues)

        invalid_numeric: dict[str, int] = {}
        for rule in self.numeric_rules:
            check = check_numeric(frame[rule.column], rule)
            issues += _issues(check.invalid, f"invalid_{rule.column}")
            invalid_numeric[rule.column] = int(check.invalid.sum())
            frame[rule.column] = check.values.mask(check.invalid)

        unknown_priority = unrecognised_priority_mask(frame["priority"])
        issues += _issues(unknown_priority, "invalid_priority")
        frame["priority"] = frame["priority"].mask(unknown_priority)

        # Missing text gets visible placeholders; missing numbers stay NaN.
        for column in TEXT_COLUMNS:
            frame[column] = frame[column].fillna(UNKNOWN)
        frame["description"] = frame["description"].fillna("")

        report = CleaningReport(
            source_rows=len(raw),
            cleaned_rows=len(frame),
            duplicate_policy=self.duplicate_policy,
            rows_dropped_missing_ticket_id=int(missing_id.sum()),
            duplicate_rows_removed=duplicates_removed,
            duplicate_ticket_ids=duplicate_ids,
            issues=tuple(issues),
            missing_values_before_cleaning=missing_before,
            missing_values_after_cleaning=frame.isna().sum().astype(int).to_dict(),
            invalid_numeric_values=invalid_numeric,
        )
        return CleaningResult(frame=frame.reset_index(drop=True), report=report)

    @staticmethod
    def _normalise(raw: pd.DataFrame) -> pd.DataFrame:
        frame = raw.copy(deep=True)
        frame["ticket_id"] = _normalise_text(frame["ticket_id"]).str.upper()
        for column in TEXT_COLUMNS:
            frame[column] = _normalise_text(frame[column]).str.lower()
        frame["description"] = _normalise_text(frame["description"])
        return frame

    def _drop_duplicates(
        self, frame: pd.DataFrame, issues: list[ValidationIssue]
    ) -> tuple[pd.DataFrame, tuple[str, ...], int]:
        # With no timestamp to say which copy is newer, the first source row wins
        # (or, with DuplicatePolicy.RAISE, the whole file is refused).
        duplicated = frame["ticket_id"].duplicated(keep="first")
        duplicate_ids = tuple(sorted(frame.loc[duplicated, "ticket_id"].unique().tolist()))
        if duplicate_ids and self.duplicate_policy is DuplicatePolicy.RAISE:
            raise DuplicateTicketError(
                "Duplicate ticket IDs found; review them before processing: "
                + ", ".join(duplicate_ids)
            )
        issues += _issues(duplicated, "duplicate_ticket_id")
        return frame.loc[~duplicated].copy(), duplicate_ids, int(duplicated.sum())
