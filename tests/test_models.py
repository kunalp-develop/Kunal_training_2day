"""Task A: SupportTicket cannot be built in an invalid state."""

import dataclasses
import math

import pytest

from ticket_pipeline.errors import InvalidTicketError, TicketPipelineError
from ticket_pipeline.models import (
    CleaningReport,
    DuplicatePolicy,
    Priority,
    SupportTicket,
    ValidationIssue,
)


def make_ticket(**overrides) -> SupportTicket:
    values = {
        "ticket_id": "T-1",
        "category": "billing",
        "priority": Priority.HIGH,
        "description": "Charged twice",
        "resolution_time_hours": 2.5,
        "customer_rating": 5,
        "status": "resolved",
    }
    values.update(overrides)
    return SupportTicket(**values)


# --- normal behaviour -------------------------------------------------------


def test_valid_ticket_keeps_its_values() -> None:
    ticket = make_ticket()

    assert ticket.ticket_id == "T-1"
    assert ticket.priority is Priority.HIGH
    assert ticket.customer_rating == 5.0
    assert isinstance(ticket.customer_rating, float)  # int normalised to float


def test_missing_numbers_are_represented_as_none() -> None:
    ticket = make_ticket(resolution_time_hours=None, customer_rating=None)

    assert ticket.resolution_time_hours is None
    assert ticket.customer_rating is None


@pytest.mark.parametrize("rating", [1, 3.5, 5])
def test_rating_boundaries_are_inclusive(rating: float) -> None:
    assert make_ticket(customer_rating=rating).customer_rating == rating


def test_zero_resolution_time_is_allowed() -> None:
    assert make_ticket(resolution_time_hours=0).resolution_time_hours == 0.0


@pytest.mark.parametrize(
    ("status", "expected"),
    [("resolved", True), ("closed", True), ("open", False), ("unknown", False)],
)
def test_is_resolved_uses_the_shared_status_set(status: str, expected: bool) -> None:
    assert make_ticket(status=status).is_resolved is expected


def test_str_is_short_and_repr_shows_every_field() -> None:
    ticket = make_ticket()

    assert str(ticket) == "T-1 [high/billing] resolved"
    assert repr(ticket).startswith("SupportTicket(ticket_id='T-1'")
    assert "priority=<Priority.HIGH: 'high'>" in repr(ticket)


def test_equal_values_make_equal_hashable_tickets() -> None:
    assert make_ticket() == make_ticket()
    assert len({make_ticket(), make_ticket()}) == 1


def test_from_record_converts_nan_to_none_and_parses_priority() -> None:
    ticket = SupportTicket.from_record(
        {
            "ticket_id": "T-9",
            "category": "account",
            "priority": "unknown",
            "description": "",
            "resolution_time_hours": float("nan"),
            "customer_rating": 4.0,
            "status": "open",
        }
    )

    assert ticket.priority is Priority.UNKNOWN
    assert ticket.resolution_time_hours is None
    assert ticket.customer_rating == 4.0


# --- invalid state is prevented -----------------------------------------------


@pytest.mark.parametrize(
    "overrides",
    [
        {"ticket_id": ""},
        {"ticket_id": "   "},
        {"ticket_id": None},
        {"category": ""},
        {"status": ""},
        {"description": None},
        {"priority": "high"},  # a plain string is not a Priority
        {"customer_rating": 0},
        {"customer_rating": 6},
        {"customer_rating": float("nan")},
        {"customer_rating": math.inf},
        {"customer_rating": "5"},
        {"customer_rating": True},  # bool is an int subclass; reject it explicitly
        {"resolution_time_hours": -1},
        {"resolution_time_hours": math.inf},
        {"resolution_time_hours": -math.inf},
    ],
)
def test_invalid_values_are_rejected(overrides: dict) -> None:
    with pytest.raises(InvalidTicketError):
        make_ticket(**overrides)


def test_invalid_ticket_error_belongs_to_the_package_error_family() -> None:
    with pytest.raises(TicketPipelineError):
        make_ticket(ticket_id="")


def test_tickets_cannot_be_changed_after_creation() -> None:
    ticket = make_ticket()

    with pytest.raises(dataclasses.FrozenInstanceError):
        ticket.customer_rating = 99  # would bypass validation if allowed


def test_unrecognised_priority_text_is_rejected() -> None:
    with pytest.raises(InvalidTicketError, match="unrecognised priority"):
        Priority.from_text("urgent")


def test_missing_priority_text_is_unknown() -> None:
    assert Priority.from_text(None) is Priority.UNKNOWN
    assert Priority.from_text("") is Priority.UNKNOWN


# --- CleaningReport -----------------------------------------------------------


def test_report_mutable_defaults_are_not_shared_between_instances() -> None:
    first = CleaningReport(source_rows=1, cleaned_rows=1, duplicate_policy=DuplicatePolicy.RAISE)
    second = CleaningReport(source_rows=1, cleaned_rows=1, duplicate_policy=DuplicatePolicy.RAISE)

    first.invalid_numeric_values["customer_rating"] = 3

    assert second.invalid_numeric_values == {}


def test_report_groups_issues_by_record_in_source_order() -> None:
    report = CleaningReport(
        source_rows=12,
        cleaned_rows=10,
        duplicate_policy=DuplicatePolicy.KEEP_FIRST,
        issues=(
            ValidationIssue(10, "invalid_customer_rating"),
            ValidationIssue(2, "missing_ticket_id"),
            ValidationIssue(10, "duplicate_ticket_id"),
        ),
    )

    assert report.invalid_record_count == 2
    assert report.invalid_record_reasons == {
        "2": ["missing_ticket_id"],
        "10": ["duplicate_ticket_id", "invalid_customer_rating"],
    }
    assert report.to_dict()["duplicate_policy"] == "keep_first"
