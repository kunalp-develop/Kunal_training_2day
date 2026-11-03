"""Shared test helpers. pytest puts this directory on sys.path, so tests can import it."""

from pathlib import Path

REQUIRED_HEADER = (
    "ticket_id,category,priority,description,resolution_time_hours,"
    "customer_rating,status\n"
)


def write_csv(path: Path, content: str) -> Path:
    path.write_text(content, encoding="utf-8")
    return path
