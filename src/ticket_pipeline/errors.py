"""Exception hierarchy for the ticket pipeline.

This is the one place the project uses inheritance: every error *is a*
``TicketPipelineError``, so callers can catch the whole family with one
``except`` or pick out a specific failure. The base class extends
``ValueError`` so code written against the Day 1 API keeps working.
"""


class TicketPipelineError(ValueError):
    """Base class for every error raised by this package."""


class InvalidCSVError(TicketPipelineError):
    """The input file cannot be parsed as a well-formed CSV."""


class EmptyDatasetError(TicketPipelineError):
    """The CSV has no header, or a header but no ticket records."""


class MissingColumnsError(TicketPipelineError):
    """One or more required columns are absent."""


class DuplicateTicketError(TicketPipelineError):
    """Duplicate ticket IDs were found and the policy is to fail closed."""


class InvalidTicketError(TicketPipelineError):
    """A SupportTicket was constructed with a value that breaks its rules."""
