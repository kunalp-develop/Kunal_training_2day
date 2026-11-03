"""Domain objects: a validated SupportTicket and the cleaning report.

A ``SupportTicket`` cannot exist in an invalid state: ``__post_init__`` checks
every field, and ``frozen=True`` stops anyone changing a field afterwards.
Missing numeric values are represented explicitly as ``None``; a missing
priority is ``Priority.UNKNOWN``.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, ClassVar

from .errors import InvalidTicketError
from .schema import (
    CUSTOMER_RATING_RULE,
    RESOLUTION_TIME_RULE,
    RESOLVED_STATUSES,
    UNKNOWN,
    NumericRule,
)


class Priority(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    UNKNOWN = UNKNOWN

    @classmethod
    def from_text(cls, text: str | None) -> Priority:
        """Parse a normalised priority; missing text means ``UNKNOWN``."""
        if text is None or text == "":
            return cls.UNKNOWN
        try:
            return cls(text)
        except ValueError:
            raise InvalidTicketError(f"unrecognised priority: {text!r}") from None


class DuplicatePolicy(Enum):
    KEEP_FIRST = "keep_first"  # source order is authoritative
    RAISE = "raise"  # duplicates must be reviewed before any data is accepted


def _is_missing(value: Any) -> bool:
    return value is None or (isinstance(value, float) and math.isnan(value))


@dataclass(frozen=True, slots=True)
class SupportTicket:
    ticket_id: str
    category: str
    priority: Priority
    description: str
    resolution_time_hours: float | None
    customer_rating: float | None
    status: str

    # Shared, immutable, so it belongs on the class rather than each instance.
    RESOLVED_STATUSES: ClassVar[frozenset[str]] = RESOLVED_STATUSES

    def __post_init__(self) -> None:
        for name in ("ticket_id", "category", "status"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise InvalidTicketError(f"{name} must be a non-empty string, got {value!r}")
        if not isinstance(self.description, str):
            raise InvalidTicketError("description must be a string")
        if not isinstance(self.priority, Priority):
            raise InvalidTicketError(
                f"priority must be a Priority, got {type(self.priority).__name__}"
            )
        self._check_number("resolution_time_hours", RESOLUTION_TIME_RULE)
        self._check_number("customer_rating", CUSTOMER_RATING_RULE)

    def _check_number(self, name: str, rule: NumericRule) -> None:
        value = getattr(self, name)
        if value is None:
            return
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise InvalidTicketError(f"{name} must be a number or None, got {value!r}")
        if not rule.accepts(float(value)):
            raise InvalidTicketError(f"{name} {rule.description}, got {value!r}")
        # Frozen dataclasses block normal assignment; this normalises int -> float once.
        object.__setattr__(self, name, float(value))

    @property
    def is_resolved(self) -> bool:
        return self.status in self.RESOLVED_STATUSES

    @classmethod
    def from_record(cls, record: Mapping[str, Any]) -> SupportTicket:
        """Build a ticket from a cleaned row; NaN numbers become ``None``."""

        def number(key: str) -> float | None:
            value = record.get(key)
            return None if _is_missing(value) else value

        return cls(
            ticket_id=record["ticket_id"],
            category=record["category"],
            priority=Priority.from_text(record.get("priority")),
            description=record.get("description") or "",
            resolution_time_hours=number("resolution_time_hours"),
            customer_rating=number("customer_rating"),
            status=record["status"],
        )

    def __str__(self) -> str:
        return f"{self.ticket_id} [{self.priority.value}/{self.category}] {self.status}"


@dataclass(frozen=True, slots=True)
class ValidationIssue:
    """One problem found in one source record (0-based record index)."""

    record_index: int
    reason: str


@dataclass(frozen=True)
class CleaningReport:
    """What cleaning did, returned as a value rather than stored on the cleaner."""

    source_rows: int
    cleaned_rows: int
    duplicate_policy: DuplicatePolicy
    rows_dropped_missing_ticket_id: int = 0
    duplicate_rows_removed: int = 0
    duplicate_ticket_ids: tuple[str, ...] = ()
    issues: tuple[ValidationIssue, ...] = ()
    # default_factory gives every report its own dict; a plain `= {}` default
    # would be one dict shared by every instance.
    missing_values_before_cleaning: dict[str, int] = field(default_factory=dict)
    missing_values_after_cleaning: dict[str, int] = field(default_factory=dict)
    invalid_numeric_values: dict[str, int] = field(default_factory=dict)

    @property
    def invalid_record_reasons(self) -> dict[str, list[str]]:
        grouped: dict[int, set[str]] = {}
        for issue in self.issues:
            grouped.setdefault(issue.record_index, set()).add(issue.reason)
        return {str(index): sorted(grouped[index]) for index in sorted(grouped)}

    @property
    def invalid_record_count(self) -> int:
        return len({issue.record_index for issue in self.issues})

    def to_dict(self) -> dict[str, Any]:
        """The Day 1 report format, kept so existing callers see no change."""
        return {
            "source_rows": self.source_rows,
            "cleaned_rows": self.cleaned_rows,
            "rows_dropped_missing_ticket_id": self.rows_dropped_missing_ticket_id,
            "duplicate_ticket_ids": list(self.duplicate_ticket_ids),
            "duplicate_rows_removed": self.duplicate_rows_removed,
            "missing_values_before_cleaning": dict(self.missing_values_before_cleaning),
            "missing_values_after_cleaning": dict(self.missing_values_after_cleaning),
            "invalid_numeric_values": dict(self.invalid_numeric_values),
            "invalid_record_count": self.invalid_record_count,
            "invalid_record_reasons": self.invalid_record_reasons,
            "duplicate_policy": self.duplicate_policy.value,
        }
