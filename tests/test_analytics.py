"""Analytics operations are tested on hand-built tickets: no CSV or pandas needed."""

from typing import ClassVar

import pytest

from ticket_pipeline.analytics import (
    AnalyticsOperation,
    AverageCustomerRating,
    AverageResolutionByCategory,
    PriorityCounts,
    ResolutionRateByCategory,
    TicketAnalytics,
    UnresolvedCount,
    day1_operations,
    default_operations,
)
from ticket_pipeline.models import Priority, SupportTicket


def ticket(ticket_id, category="billing", priority=Priority.LOW, hours=None, rating=None, status="open"):
    return SupportTicket(ticket_id, category, priority, "", hours, rating, status)


TICKETS = (
    ticket("T-1", "billing", Priority.HIGH, hours=2, rating=5, status="resolved"),
    ticket("T-2", "billing", Priority.LOW, hours=4, rating=3, status="open"),
    ticket("T-3", "account", Priority.HIGH, hours=None, rating=None, status="closed"),
    ticket("T-4", "account", Priority.UNKNOWN, hours=1, rating=4, status="pending"),
    ticket("T-5", "shipping", Priority.MEDIUM, hours=None, rating=None, status="open"),
)


def test_priority_counts_are_sorted_by_priority_name() -> None:
    assert PriorityCounts().compute(TICKETS) == {"high": 2, "low": 1, "medium": 1, "unknown": 1}


def test_average_resolution_skips_missing_times_and_categories_without_any() -> None:
    # shipping has no valid time, so it is left out rather than reported as NaN.
    assert AverageResolutionByCategory().compute(TICKETS) == {"account": 1.0, "billing": 3.0}


def test_average_rating_rounds_to_two_places() -> None:
    assert AverageCustomerRating().compute(TICKETS) == 4.0
    assert AverageCustomerRating().compute([ticket("a", rating=1), ticket("b", rating=2), ticket("c", rating=2)]) == 1.67


def test_unresolved_count_treats_resolved_and_closed_as_done() -> None:
    assert UnresolvedCount().compute(TICKETS) == 3


def test_resolution_rate_by_category() -> None:
    assert ResolutionRateByCategory().compute(TICKETS) == {
        "account": 0.5,
        "billing": 0.5,
        "shipping": 0.0,
    }


@pytest.mark.parametrize(
    ("operation", "expected"),
    [
        (PriorityCounts(), {}),
        (AverageResolutionByCategory(), {}),
        (AverageCustomerRating(), None),
        (UnresolvedCount(), 0),
        (ResolutionRateByCategory(), {}),
    ],
)
def test_every_operation_handles_no_tickets(operation, expected) -> None:
    assert operation.compute(()) == expected


def test_every_operation_satisfies_the_protocol() -> None:
    assert all(isinstance(op, AnalyticsOperation) for op in default_operations())


def test_default_operations_are_day1_plus_the_new_metric_in_order() -> None:
    assert TicketAnalytics().names == (
        "ticket_count_by_priority",
        "average_resolution_time_hours_by_category",
        "average_customer_rating",
        "unresolved_ticket_count",
        "resolution_rate_by_category",
    )
    assert TicketAnalytics(day1_operations()).names == TicketAnalytics().names[:4]


def test_custom_operation_is_added_without_changing_the_engine() -> None:
    class HighPriorityCount:
        name: ClassVar[str] = "high_priority_count"

        def compute(self, tickets):
            return sum(t.priority is Priority.HIGH for t in tickets)

    result = TicketAnalytics([*default_operations(), HighPriorityCount()]).run(TICKETS)

    assert result["high_priority_count"] == 2
    assert result["unresolved_ticket_count"] == 3  # existing metrics unaffected


def test_duplicate_operation_names_are_rejected() -> None:
    with pytest.raises(ValueError, match="unresolved_ticket_count"):
        TicketAnalytics([UnresolvedCount(), UnresolvedCount()])


def test_operations_can_be_reused_across_runs() -> None:
    analytics = TicketAnalytics()

    assert analytics.run(TICKETS) == analytics.run(TICKETS)
    assert analytics.run(())["unresolved_ticket_count"] == 0
