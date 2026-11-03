"""Read a raw ticket CSV into a DataFrame. Loading only: no cleaning, no rules."""

from __future__ import annotations

import csv
from pathlib import Path

import pandas as pd

from .errors import EmptyDatasetError, InvalidCSVError


class CsvTicketLoader:
    """Load one CSV file and turn parser failures into clear package errors."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def load(self) -> pd.DataFrame:
        try:
            self._check_field_counts()
            frame = pd.read_csv(
                self.path,
                keep_default_na=False,  # keep text such as "NA" or "None" as data
                na_values=[""],  # only truly empty cells are missing
                index_col=False,  # never treat the first column as an index
            )
        except pd.errors.EmptyDataError as exc:
            raise EmptyDatasetError("The CSV file is empty and has no header row.") from exc
        except (pd.errors.ParserError, UnicodeDecodeError, OSError) as exc:
            raise self._invalid(str(exc)) from exc

        if frame.empty:
            raise EmptyDatasetError("The CSV has a header but contains no ticket rows.")
        return frame

    def _check_field_counts(self) -> None:
        """Reject any record whose field count differs from the header.

        Without this check pandas treats a row with one extra field as having
        an index column, which silently shifts every value one column left.
        """
        with self.path.open(newline="", encoding="utf-8-sig") as handle:
            reader = csv.reader(handle)
            header = next(reader, None)
            if header is None:
                return  # empty file: reported by the pandas read
            for record in reader:
                if not record:
                    continue  # blank line, skipped the same way pandas does
                if len(record) != len(header):
                    raise self._invalid(
                        f"line {reader.line_num} expected {len(header)} fields, "
                        f"found {len(record)}"
                    )

    def _invalid(self, detail: str) -> InvalidCSVError:
        return InvalidCSVError(f"Could not read a valid CSV from '{self.path}': {detail}")
