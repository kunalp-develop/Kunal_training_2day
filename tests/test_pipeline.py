"""TicketPipeline wiring. The file dependency is replaced by a fake loader."""

import json
from pathlib import Path

import pandas as pd

from ticket_pipeline import (
    CleanedCsvWriter,
    CsvTicketLoader,
    QualityReportWriter,
    TicketAnalytics,
    TicketPipeline,
)
from ticket_pipeline.analytics import UnresolvedCount
from ticket_pipeline.schema import REQUIRED_COLUMNS

ROOT = Path(__file__).resolve().parents[1]


class FakeLoader:
    """Stands in for CsvTicketLoader: returns a frame from memory and counts calls."""

    def __init__(self, rows: list[tuple]) -> None:
        self.frame = pd.DataFrame(rows, columns=list(REQUIRED_COLUMNS))
        self.calls = 0

    def load(self) -> pd.DataFrame:
        self.calls += 1
        return self.frame


def test_pipeline_runs_entirely_in_memory_with_a_fake_source() -> None:
    source = FakeLoader(
        [
            ("T-1", "billing", "high", "Refund", 2, 5, "resolved"),
            ("T-2", "billing", "low", "Invoice", "bad", 3, "open"),
            ("T-2", "billing", "low", "Duplicate", 1, 1, "open"),
        ]
    )

    result = TicketPipeline(source).run()

    assert source.calls == 1
    assert [t.ticket_id for t in result.tickets] == ["T-1", "T-2"]
    assert result.analytics["unresolved_ticket_count"] == 1
    assert result.analytics["duplicate_ticket_ids"] == ["T-2"]
    assert result.analytics["invalid_record_count"] == 2
    assert result.report.invalid_record_reasons == {
        "1": ["invalid_resolution_time_hours"],
        "2": ["duplicate_ticket_id"],
    }


def test_injected_analytics_controls_which_metrics_are_published() -> None:
    source = FakeLoader([("T-1", "billing", "high", "x", 2, 5, "open")])

    result = TicketPipeline(source, analytics=TicketAnalytics([UnresolvedCount()])).run()

    assert "unresolved_ticket_count" in result.analytics
    assert "ticket_count_by_priority" not in result.analytics
    assert "rows_dropped_missing_ticket_id" in result.analytics  # quality fields always included


def test_sample_data_output_is_day1_baseline_plus_only_the_new_metric() -> None:
    """Golden test: the refactor must not change any Day 1 number."""
    baseline = json.loads((ROOT / "logs" / "day1_baseline_output.json").read_text(encoding="utf-8-sig"))

    analytics = TicketPipeline(CsvTicketLoader(ROOT / "data" / "tickets.csv")).run().analytics

    assert {k: v for k, v in analytics.items() if k != "resolution_rate_by_category"} == baseline
    assert list(analytics) == [*list(baseline)[:4], "resolution_rate_by_category", *list(baseline)[4:]]
    assert analytics["resolution_rate_by_category"] == {
        "account": 0.8,  # 4 of 5 resolved/closed
        "billing": 0.67,  # 4 of 6
        "shipping": 0.6,  # 3 of 5
        "technical": 0.33,  # 2 of 6
        "unknown": 0.0,  # 0 of 1
    }


def test_end_to_end_writes_outputs_and_leaves_raw_csv_byte_for_byte_unchanged(tmp_path: Path) -> None:
    raw = tmp_path / "tickets.csv"
    raw.write_bytes((ROOT / "data" / "tickets.csv").read_bytes())
    before = raw.read_bytes()

    result = TicketPipeline(CsvTicketLoader(raw)).run()
    CleanedCsvWriter(tmp_path / "cleaned.csv", protected=[raw]).write(result.frame)
    QualityReportWriter(tmp_path / "issues.csv").write(result.report)

    assert raw.read_bytes() == before
    assert len(pd.read_csv(tmp_path / "cleaned.csv")) == 23
    assert len((tmp_path / "issues.csv").read_text(encoding="utf-8").splitlines()) == 1 + 5
