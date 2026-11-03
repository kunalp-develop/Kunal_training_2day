"""Individual metrics. Each class answers exactly one question about the tickets.

Operations hold no per-run state: ``compute`` only reads its argument, so one
instance can be reused for any number of runs.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Sequence
from statistics import fmean
from typing import ClassVar

from ..models import SupportTicket


def _rounded(value: float) -> float:
    return round(value, 2)


class PriorityCounts:
    name: ClassVar[str] = "ticket_count_by_priority"

    def compute(self, tickets: Sequence[SupportTicket]) -> dict[str, int]:
        counts = Counter(ticket.priority.value for ticket in tickets)
        return dict(sorted(counts.items()))


class AverageResolutionByCategory:
    """Mean resolution time per category, ignoring tickets with no valid time."""

    name: ClassVar[str] = "average_resolution_time_hours_by_category"

    def compute(self, tickets: Sequence[SupportTicket]) -> dict[str, float]:
        times: dict[str, list[float]] = defaultdict(list)
        for ticket in tickets:
            if ticket.resolution_time_hours is not None:
                times[ticket.category].append(ticket.resolution_time_hours)
        return {category: _rounded(fmean(values)) for category, values in sorted(times.items())}


class AverageCustomerRating:
    name: ClassVar[str] = "average_customer_rating"

    def compute(self, tickets: Sequence[SupportTicket]) -> float | None:
        ratings = [t.customer_rating for t in tickets if t.customer_rating is not None]
        return _rounded(fmean(ratings)) if ratings else None


class UnresolvedCount:
    """Tickets whose status is not in SupportTicket.RESOLVED_STATUSES."""

    name: ClassVar[str] = "unresolved_ticket_count"

    def compute(self, tickets: Sequence[SupportTicket]) -> int:
        return sum(1 for ticket in tickets if not ticket.is_resolved)


class ResolutionRateByCategory:
    """Day 2 addition: share of each category's tickets that are resolved (0-1)."""

    name: ClassVar[str] = "resolution_rate_by_category"

    def compute(self, tickets: Sequence[SupportTicket]) -> dict[str, float]:
        totals: Counter[str] = Counter()
        resolved: Counter[str] = Counter()
        for ticket in tickets:
            totals[ticket.category] += 1
            resolved[ticket.category] += ticket.is_resolved
        return {
            category: _rounded(resolved[category] / total)
            for category, total in sorted(totals.items())
        }
