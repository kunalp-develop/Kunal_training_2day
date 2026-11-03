"""Single source of truth for column names and value rules.

Everything here is immutable (tuples, frozensets, frozen dataclasses), so it
is safe to share at module and class level.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

REQUIRED_COLUMNS: tuple[str, ...] = (
    "ticket_id",
    "category",
    "priority",
    "description",
    "resolution_time_hours",
    "customer_rating",
    "status",
)
TEXT_COLUMNS: tuple[str, ...] = ("category", "priority", "status")
RESOLVED_STATUSES: frozenset[str] = frozenset({"resolved", "closed"})
UNKNOWN = "unknown"


@dataclass(frozen=True)
class NumericRule:
    """Allowed range for one numeric column (``maximum=None`` means unbounded)."""

    column: str
    minimum: float
    maximum: float | None = None

    def accepts(self, value: float) -> bool:
        """True when ``value`` is finite and inside the allowed range."""
        if not math.isfinite(value) or value < self.minimum:
            return False
        return self.maximum is None or value <= self.maximum

    @property
    def description(self) -> str:
        if self.maximum is None:
            return f"must be a finite number greater than or equal to {self.minimum:g}"
        return (
            f"must be a finite number between {self.minimum:g} and "
            f"{self.maximum:g}, inclusive"
        )


RESOLUTION_TIME_RULE = NumericRule("resolution_time_hours", minimum=0)
CUSTOMER_RATING_RULE = NumericRule("customer_rating", minimum=1, maximum=5)
NUMERIC_RULES: tuple[NumericRule, ...] = (RESOLUTION_TIME_RULE, CUSTOMER_RATING_RULE)
