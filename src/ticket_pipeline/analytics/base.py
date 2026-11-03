"""The one extension point of the package: an analytics operation.

Any object with a ``name`` and a ``compute(tickets)`` method is an operation.
``Protocol`` means operations do not inherit from anything; they only need
the right shape (structural typing).
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any, ClassVar, Protocol, runtime_checkable

from ..models import SupportTicket


@runtime_checkable
class AnalyticsOperation(Protocol):
    name: ClassVar[str]  # the key this metric gets in the analytics output

    def compute(self, tickets: Sequence[SupportTicket]) -> Any:
        """Return a JSON-serialisable value computed from validated tickets."""
        ...
