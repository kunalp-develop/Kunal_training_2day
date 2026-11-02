"""Descriptive analytics for the cleaned support-ticket dataset."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd


def build_analytics(
    cleaned_data: pd.DataFrame, processing_report: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Build the required ticket summary as a serialisable dictionary.

    A ticket is treated as unresolved unless its status is ``resolved`` or
    ``closed``. This definition is intentionally visible and easy to change.
    """
    if cleaned_data.empty:
        priority_counts: dict[str, int] = {}
        category_averages: dict[str, float] = {}
        average_rating: float | None = None
        unresolved_count = 0
    else:
        priority_counts = {
            str(key): int(value)
            for key, value in cleaned_data["priority"]
            .fillna("unknown")
            .value_counts(dropna=False)
            .sort_index()
            .items()
        }

        means = cleaned_data.groupby("category")["resolution_time_hours"].mean()
        category_averages = {
            str(key): round(float(value), 2)
            for key, value in means.dropna().sort_index().items()
        }

        valid_ratings = cleaned_data["customer_rating"].dropna().to_numpy(dtype=float)
        average_rating = (
            round(float(np.mean(valid_ratings)), 2) if valid_ratings.size else None
        )

        statuses = cleaned_data["status"].fillna("unknown").astype(str).str.lower()
        is_resolved = np.isin(statuses.to_numpy(), ["resolved", "closed"])
        unresolved_count = int((~is_resolved).sum())

    report = processing_report or {}
    return {
        "ticket_count_by_priority": priority_counts,
        "average_resolution_time_hours_by_category": category_averages,
        "average_customer_rating": average_rating,
        "unresolved_ticket_count": unresolved_count,
        "missing_values_after_cleaning": report.get(
            "missing_values_after_cleaning", cleaned_data.isna().sum().astype(int).to_dict()
        ),
        "missing_values_before_cleaning": report.get(
            "missing_values_before_cleaning", {}
        ),
        "invalid_numeric_values": report.get("invalid_numeric_values", {}),
        "invalid_record_count": report.get("invalid_record_count", 0),
        "duplicate_ticket_ids": report.get("duplicate_ticket_ids", []),
        "rows_dropped_missing_ticket_id": report.get(
            "rows_dropped_missing_ticket_id", 0
        ),
    }
