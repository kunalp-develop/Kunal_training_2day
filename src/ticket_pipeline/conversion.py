"""Turn a cleaned DataFrame into validated SupportTicket objects.

This is the boundary between tabular data and the domain model. If a
cleaned row cannot become a ticket, cleaning has a bug, so it fails loudly.
"""

from __future__ import annotations

import pandas as pd

from .errors import InvalidTicketError
from .models import SupportTicket


def frame_to_tickets(frame: pd.DataFrame) -> tuple[SupportTicket, ...]:
    records = frame.astype(object).where(frame.notna(), None).to_dict("records")
    tickets = []
    for position, record in enumerate(records):
        try:
            tickets.append(SupportTicket.from_record(record))
        except InvalidTicketError as exc:
            raise InvalidTicketError(f"cleaned row {position} is not a valid ticket: {exc}") from exc
    return tuple(tickets)
