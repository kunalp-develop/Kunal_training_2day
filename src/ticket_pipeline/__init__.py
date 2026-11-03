"""Support-ticket processing built from small, replaceable components (Day 2)."""

from .analytics import AnalyticsOperation, TicketAnalytics, default_operations
from .cleaning import CleaningResult, TicketCleaner
from .errors import (
    DuplicateTicketError,
    EmptyDatasetError,
    InvalidCSVError,
    InvalidTicketError,
    MissingColumnsError,
    TicketPipelineError,
)
from .loading import CsvTicketLoader
from .models import CleaningReport, DuplicatePolicy, Priority, SupportTicket, ValidationIssue
from .pipeline import PipelineResult, TicketPipeline
from .processor import TicketDataProcessor, build_analytics  # Day 1 compatibility
from .writers import CleanedCsvWriter, QualityReportWriter

__all__ = [
    "AnalyticsOperation",
    "CleanedCsvWriter",
    "CleaningReport",
    "CleaningResult",
    "CsvTicketLoader",
    "DuplicatePolicy",
    "DuplicateTicketError",
    "EmptyDatasetError",
    "InvalidCSVError",
    "InvalidTicketError",
    "MissingColumnsError",
    "PipelineResult",
    "Priority",
    "QualityReportWriter",
    "SupportTicket",
    "TicketAnalytics",
    "TicketCleaner",
    "TicketDataProcessor",
    "TicketPipeline",
    "TicketPipelineError",
    "ValidationIssue",
    "build_analytics",
    "default_operations",
]
