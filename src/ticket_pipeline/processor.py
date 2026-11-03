"""Day 1 compatibility facade: ``TicketDataProcessor`` and ``build_analytics``.

``TicketDataProcessor`` used to read, validate, clean, report and save in one
class, and ``build_analytics`` hard-coded four metrics. Both now only delegate
to the Day 2 components, so existing callers and the Day 1 tests keep
working. New code should use ``TicketPipeline`` or the components directly.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pandas as pd

from .analytics import TicketAnalytics, day1_operations
from .cleaning import TicketCleaner
from .conversion import frame_to_tickets
from .errors import EmptyDatasetError, InvalidCSVError, MissingColumnsError
from .loading import CsvTicketLoader
from .models import DuplicatePolicy
from .writers import CleanedCsvWriter

__all__ = [
    "TicketDataProcessor",
    "build_analytics",
    "EmptyDatasetError",
    "InvalidCSVError",
    "MissingColumnsError",
]


def build_analytics(
    cleaned_data: pd.DataFrame, processing_report: Mapping[str, Any] | None = None
) -> dict[str, Any]:
    """Deprecated: the Day 1 summary (four metrics plus report fields)."""
    tickets = frame_to_tickets(cleaned_data)
    report = processing_report or {}
    return {
        **TicketAnalytics(day1_operations()).run(tickets),
        "missing_values_after_cleaning": report.get(
            "missing_values_after_cleaning", cleaned_data.isna().sum().astype(int).to_dict()
        ),
        "missing_values_before_cleaning": report.get("missing_values_before_cleaning", {}),
        "invalid_numeric_values": report.get("invalid_numeric_values", {}),
        "invalid_record_count": report.get("invalid_record_count", 0),
        "duplicate_ticket_ids": report.get("duplicate_ticket_ids", []),
        "rows_dropped_missing_ticket_id": report.get("rows_dropped_missing_ticket_id", 0),
    }


class TicketDataProcessor:
    """Deprecated wrapper around CsvTicketLoader + TicketCleaner + CleanedCsvWriter."""

    def __init__(
        self,
        input_path: str | Path,
        output_path: str | Path | None = None,
        duplicate_policy: str = "keep_first",
    ) -> None:
        if duplicate_policy not in {policy.value for policy in DuplicatePolicy}:
            raise ValueError("duplicate_policy must be 'keep_first' or 'raise'")

        self.input_path = Path(input_path)
        self.output_path = Path(output_path) if output_path is not None else None
        self.duplicate_policy = duplicate_policy
        # Kept only for the Day 1 API; the new components return the report instead.
        self.report: dict[str, Any] = {}

    def process(self) -> pd.DataFrame:
        raw = CsvTicketLoader(self.input_path).load()
        result = TicketCleaner(DuplicatePolicy(self.duplicate_policy)).clean(raw)
        self.report = result.report.to_dict()
        return result.frame

    def save_cleaned_data(
        self, cleaned_data: pd.DataFrame, output_path: str | Path | None = None
    ) -> Path:
        destination = Path(output_path) if output_path is not None else self.output_path
        if destination is None:
            raise ValueError("Provide output_path in the constructor or save method.")
        return CleanedCsvWriter(destination, protected=[self.input_path]).write(cleaned_data)
