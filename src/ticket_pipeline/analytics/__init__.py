"""Composable ticket analytics."""

from .base import AnalyticsOperation
from .engine import TicketAnalytics, day1_operations, default_operations
from .operations import (
    AverageCustomerRating,
    AverageResolutionByCategory,
    PriorityCounts,
    ResolutionRateByCategory,
    UnresolvedCount,
)

__all__ = [
    "AnalyticsOperation",
    "TicketAnalytics",
    "day1_operations",
    "default_operations",
    "PriorityCounts",
    "AverageResolutionByCategory",
    "AverageCustomerRating",
    "UnresolvedCount",
    "ResolutionRateByCategory",
]
