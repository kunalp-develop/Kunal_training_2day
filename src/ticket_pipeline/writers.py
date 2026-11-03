"""Write pipeline outputs to disk. File I/O lives here, not in the processing logic."""

from __future__ import annotations

from collections.abc import Iterable
from csv import DictWriter
from pathlib import Path

import pandas as pd

from .models import CleaningReport


class CleanedCsvWriter:
    """Save the cleaned dataset, refusing to overwrite any protected file (the raw input)."""

    def __init__(self, destination: str | Path, protected: Iterable[str | Path] = ()) -> None:
        self.destination = Path(destination)
        self.protected = tuple(Path(path) for path in protected)

    def write(self, frame: pd.DataFrame) -> Path:
        target = self.destination.resolve()
        if any(target == path.resolve() for path in self.protected):
            raise ValueError("Refusing to overwrite the raw input CSV.")
        self.destination.parent.mkdir(parents=True, exist_ok=True)
        frame.to_csv(self.destination, index=False)
        return self.destination


class QualityReportWriter:
    """Save one row per problem record: its 1-based source number and its issues."""

    def __init__(self, destination: str | Path) -> None:
        self.destination = Path(destination)

    def write(self, report: CleaningReport) -> Path:
        self.destination.parent.mkdir(parents=True, exist_ok=True)
        with self.destination.open("w", newline="", encoding="utf-8") as handle:
            writer = DictWriter(handle, fieldnames=["source_record_number", "issues"])
            writer.writeheader()
            for record_index, reasons in report.invalid_record_reasons.items():
                writer.writerow(
                    {"source_record_number": int(record_index) + 1, "issues": ";".join(reasons)}
                )
        return self.destination
