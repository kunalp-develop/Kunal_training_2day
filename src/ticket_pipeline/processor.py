"""Day 1 compatibility facade.

``TicketDataProcessor`` used to read, validate, clean, report and save in one
class. It now only delegates to the Day 2 components, so existing callers and
the Day 1 tests keep working. New code should use ``TicketPipeline`` or the
components directly.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from .cleaning import TicketCleaner
from .errors import EmptyDatasetError, InvalidCSVError, MissingColumnsError
from .loading import CsvTicketLoader
from .models import DuplicatePolicy
from .writers import CleanedCsvWriter

__all__ = [
    "TicketDataProcessor",
    "EmptyDatasetError",
    "InvalidCSVError",
    "MissingColumnsError",
]


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
