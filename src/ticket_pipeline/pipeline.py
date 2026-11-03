"""Wire the components together. The pipeline owns no rules of its own.

Every collaborator is passed in (dependency injection), so tests can swap the
file loader for an in-memory fake. File writing stays outside the pipeline,
at the edge of the program (see run_pipeline.py).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

import pandas as pd

from .analytics import TicketAnalytics
from .cleaning import TicketCleaner
from .conversion import frame_to_tickets
from .models import CleaningReport, SupportTicket


class TicketSource(Protocol):
    """Anything that can supply a raw ticket DataFrame (a CSV file, a fake in tests...)."""

    def load(self) -> pd.DataFrame: ...


@dataclass(frozen=True)
class PipelineResult:
    frame: pd.DataFrame  # cleaned table, ready to save
    tickets: tuple[SupportTicket, ...]
    report: CleaningReport
    analytics: dict[str, Any]  # metrics followed by data-quality fields


class TicketPipeline:
    def __init__(
        self,
        source: TicketSource,
        cleaner: TicketCleaner | None = None,
        analytics: TicketAnalytics | None = None,
    ) -> None:
        self.source = source
        self.cleaner = cleaner or TicketCleaner()
        self.analytics = analytics or TicketAnalytics()

    def run(self) -> PipelineResult:
        cleaned = self.cleaner.clean(self.source.load())
        tickets = frame_to_tickets(cleaned.frame)
        summary = {**self.analytics.run(tickets), **cleaned.report.quality_summary()}
        return PipelineResult(cleaned.frame, tickets, cleaned.report, summary)
