"""Load, validate, and clean support-ticket data without changing the raw CSV."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


REQUIRED_COLUMNS = {
    "ticket_id",
    "category",
    "priority",
    "description",
    "resolution_time_hours",
    "customer_rating",
    "status",
}
NUMERIC_RULES = {
    "resolution_time_hours": "must be a finite number greater than or equal to 0",
    "customer_rating": "must be a finite number between 1 and 5, inclusive",
}


class InvalidCSVError(ValueError):
    """Raised when the input file cannot be parsed as a CSV."""


class EmptyDatasetError(ValueError):
    """Raised when the CSV contains headers but no ticket records."""


class MissingColumnsError(ValueError):
    """Raised when one or more required columns are absent."""


class TicketDataProcessor:
    """Process support tickets using explicit, auditable cleaning rules.

    Duplicate handling is configurable. The training default, ``keep_first``,
    assumes source order is authoritative and retains the first occurrence of
    each non-empty ticket ID. Use ``raise`` when duplicates must be reviewed
    before any data is accepted.
    """

    def __init__(
        self,
        input_path: str | Path,
        output_path: str | Path | None = None,
        duplicate_policy: str = "keep_first",
    ) -> None:
        if duplicate_policy not in {"keep_first", "raise"}:
            raise ValueError("duplicate_policy must be 'keep_first' or 'raise'")

        self.input_path = Path(input_path)
        self.output_path = Path(output_path) if output_path is not None else None
        self.duplicate_policy = duplicate_policy
        self.report: dict[str, Any] = {}

    def _read_csv(self) -> pd.DataFrame:
        """Read the raw CSV and translate common parsing errors clearly."""
        try:
            frame = pd.read_csv(
                self.input_path,
                keep_default_na=False,
                na_values=[""],
            )
        except pd.errors.EmptyDataError as exc:
            raise EmptyDatasetError("The CSV file is empty and has no header row.") from exc
        except (pd.errors.ParserError, UnicodeDecodeError, OSError) as exc:
            raise InvalidCSVError(
                f"Could not read a valid CSV from '{self.input_path}': {exc}"
            ) from exc

        if frame.empty:
            raise EmptyDatasetError("The CSV has a header but contains no ticket rows.")
        return frame

    @staticmethod
    def _normalise_text(series: pd.Series) -> pd.Series:
        """Trim text and treat whitespace-only cells as missing."""
        values = series.astype("string").str.strip()
        return values.mask(values.eq(""))

    def _validate_columns(self, frame: pd.DataFrame) -> None:
        missing = sorted(REQUIRED_COLUMNS.difference(frame.columns))
        if missing:
            raise MissingColumnsError(
                "Missing required column(s): " + ", ".join(missing)
            )

    def process(self) -> pd.DataFrame:
        """Return a cleaned DataFrame and retain a structured cleaning report."""
        raw = self._read_csv()
        self._validate_columns(raw)
        original_rows = len(raw)
        missing_before = raw.isna().sum().astype(int).to_dict()
        invalid_reasons: dict[str, set[str]] = {}

        def mark_invalid(mask: pd.Series, reason: str) -> None:
            for row_index in raw.index[mask.fillna(False)]:
                invalid_reasons.setdefault(str(row_index), set()).add(reason)

        cleaned = raw.copy(deep=True)

        # Normalise identifiers and categorical/text fields.
        cleaned["ticket_id"] = self._normalise_text(cleaned["ticket_id"]).str.upper()
        for column in ("category", "priority", "status"):
            cleaned[column] = self._normalise_text(cleaned[column]).str.lower()
        cleaned["description"] = self._normalise_text(cleaned["description"])

        # A row without an ID cannot be reliably tracked or deduplicated.
        missing_id = cleaned["ticket_id"].isna()
        mark_invalid(missing_id, "missing_ticket_id")
        rows_dropped_missing_id = int(missing_id.sum())
        cleaned = cleaned.loc[~missing_id].copy()

        # Without a timestamp/business rule, this training project explicitly
        # treats the first source occurrence as canonical (or can fail closed).
        duplicate_mask = cleaned["ticket_id"].duplicated(keep="first")
        duplicate_ids = sorted(cleaned.loc[duplicate_mask, "ticket_id"].unique().tolist())
        if duplicate_mask.any() and self.duplicate_policy == "raise":
            raise ValueError(
                "Duplicate ticket IDs found; review them before processing: "
                + ", ".join(duplicate_ids)
            )
        mark_invalid(duplicate_mask.reindex(raw.index, fill_value=False), "duplicate_ticket_id")
        duplicate_rows_removed = int(duplicate_mask.sum())
        cleaned = cleaned.loc[~duplicate_mask].copy()

        invalid_numeric_values: dict[str, int] = {}
        for column in NUMERIC_RULES:
            original_values = cleaned[column].copy()
            numeric = pd.to_numeric(original_values, errors="coerce")
            parse_error = original_values.notna() & numeric.isna()
            finite_values = np.isfinite(numeric.to_numpy(dtype=float, na_value=np.nan))
            non_finite = pd.Series(~finite_values, index=cleaned.index) & numeric.notna()
            invalid = parse_error | non_finite

            if column == "resolution_time_hours":
                invalid |= numeric.notna() & numeric.lt(0)
            elif column == "customer_rating":
                invalid |= numeric.notna() & ~numeric.between(1, 5, inclusive="both")

            mark_invalid(invalid.reindex(raw.index, fill_value=False), f"invalid_{column}")
            invalid_numeric_values[column] = int(invalid.sum())
            cleaned[column] = numeric.mask(invalid).astype("float64")

        # Explicit missing-value policy: keep tickets, but use transparent
        # placeholders for categorical/text fields. Numeric values stay NaN.
        cleaned["category"] = cleaned["category"].fillna("unknown")
        cleaned["priority"] = cleaned["priority"].fillna("unknown")
        cleaned["status"] = cleaned["status"].fillna("unknown")
        cleaned["description"] = cleaned["description"].fillna("")

        self.report = {
            "source_rows": original_rows,
            "cleaned_rows": len(cleaned),
            "rows_dropped_missing_ticket_id": rows_dropped_missing_id,
            "duplicate_ticket_ids": duplicate_ids,
            "duplicate_rows_removed": duplicate_rows_removed,
            "missing_values_before_cleaning": missing_before,
            "missing_values_after_cleaning": (
                cleaned.isna().sum().astype(int).to_dict()
            ),
            "invalid_numeric_values": invalid_numeric_values,
            "invalid_record_count": len(invalid_reasons),
            "invalid_record_reasons": {
                row_index: sorted(reasons)
                for row_index, reasons in sorted(
                    invalid_reasons.items(), key=lambda item: int(item[0])
                )
            },
            "duplicate_policy": self.duplicate_policy,
        }
        return cleaned.reset_index(drop=True)

    def save_cleaned_data(
        self, cleaned_data: pd.DataFrame, output_path: str | Path | None = None
    ) -> Path:
        """Write cleaned records to a separate file; never overwrite raw input."""
        destination = Path(output_path) if output_path is not None else self.output_path
        if destination is None:
            raise ValueError("Provide output_path in the constructor or save method.")
        if destination.resolve() == self.input_path.resolve():
            raise ValueError("Refusing to overwrite the raw input CSV.")

        destination.parent.mkdir(parents=True, exist_ok=True)
        cleaned_data.to_csv(destination, index=False)
        return destination
