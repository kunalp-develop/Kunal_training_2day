"""Run a list of analytics operations. The engine knows no metric by name.

Adding a metric means writing one new operation class and adding it to
``default_operations()``. The engine itself never changes (open/closed).
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import Any

from ..models import SupportTicket
from .base import AnalyticsOperation
from .operations import (
    AverageCustomerRating,
    AverageResolutionByCategory,
    PriorityCounts,
    ResolutionRateByCategory,
    UnresolvedCount,
)


def day1_operations() -> tuple[AnalyticsOperation, ...]:
    """The four metrics the Day 1 report produced, in their original order."""
    return (PriorityCounts(), AverageResolutionByCategory(), AverageCustomerRating(), UnresolvedCount())


def default_operations() -> tuple[AnalyticsOperation, ...]:
    return (*day1_operations(), ResolutionRateByCategory())


class TicketAnalytics:
    """Composes operations; each one contributes one key to the result."""

    def __init__(self, operations: Iterable[AnalyticsOperation] | None = None) -> None:
        self.operations = tuple(default_operations() if operations is None else operations)
        names = [operation.name for operation in self.operations]
        repeated = sorted({name for name in names if names.count(name) > 1})
        if repeated:
            raise ValueError("Duplicate analytics operation name(s): " + ", ".join(repeated))

    @property
    def names(self) -> tuple[str, ...]:
        return tuple(operation.name for operation in self.operations)

    def run(self, tickets: Sequence[SupportTicket]) -> dict[str, Any]:
        return {operation.name: operation.compute(tickets) for operation in self.operations}
