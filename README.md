# Day 2: Support ticket pipeline, refactored into reusable components

Day 1 built a pipeline that reads a messy support-ticket CSV, cleans a copy and prints analytics. Day 2 keeps every Day 1 result the same, but rebuilds the code from small classes that each do one job. It also adds one new metric through a plug-in interface, without touching the existing ones.

The original file is never changed: `data/tickets.csv` is read, and the outputs go to new files.

## Setup

Python 3.10 or newer.

```bash
python -m venv .venv
# Windows PowerShell
.venv\Scripts\Activate.ps1
# macOS / Linux
source .venv/bin/activate

pip install -e . pytest
```

## Run

```bash
python run_pipeline.py
```

This reads `data/tickets.csv` and writes `data/cleaned_tickets.csv` and `data/quality_issues.csv`. It then prints the analytics JSON; the output from the sample file is saved in `sample_analytics_output.json` and `logs/pipeline_run.txt`.

From your own code:

```python
from ticket_pipeline import CsvTicketLoader, DuplicatePolicy, TicketCleaner, TicketPipeline

result = TicketPipeline(
    CsvTicketLoader("data/tickets.csv"),
    cleaner=TicketCleaner(DuplicatePolicy.RAISE),  # optional: refuse files with duplicate IDs
).run()

result.tickets      # tuple of validated SupportTicket objects
result.report       # CleaningReport: what was dropped, masked or filled, and why
result.analytics    # dict: metrics + data-quality fields
```

## Tests

```bash
python -m pytest -v --override-ini addopts=
```

There are 107 tests. The last full run is saved in `test_results.txt`.

| File | Covers |
|---|---|
| `tests/test_models.py` | `SupportTicket` accepts valid values and rejects every kind of invalid one; it is frozen; `__repr__`/`__str__`; mutable defaults are not shared |
| `tests/test_loading.py` | Malformed CSVs, including the Day 1 P0 regression (a row with an extra field), short rows, an empty file, a missing file and bad encoding |
| `tests/test_validation.py` | Numeric rule boundaries, missing-column detection, unrecognised priorities |
| `tests/test_cleaning.py` | Each cleaning policy, tested on in-memory DataFrames; the raw frame is not modified; no state is left over between runs |
| `tests/test_conversion_and_writers.py` | The table → model boundary; the raw-file overwrite guard; the quality CSV format |
| `tests/test_analytics.py` | Each metric on hand-built tickets; adding a custom metric without changing the engine; duplicate metric names |
| `tests/test_pipeline.py` | A fake loader (no disk); the golden test (Day 1 numbers unchanged); an end-to-end run leaves the raw file byte-for-byte the same |
| `tests/test_processor.py` | The 13 original Day 1 tests, **unchanged**, run against the compatibility layer |

## How it is built

```
CsvTicketLoader ──► TicketCleaner ──► frame_to_tickets ──► TicketAnalytics
 (read file,         (normalise, drop,   (DataFrame →         (runs a list of
  check rows)         mask, fill, report)  SupportTicket)        metric objects)
                     └──────────── composed by TicketPipeline ───────────┘
                     file output: CleanedCsvWriter, QualityReportWriter
```

| Module | One job |
|---|---|
| `models.py` | `SupportTicket`, a frozen dataclass that is valid or cannot be created; `Priority`; `CleaningReport` |
| `schema.py` | Column names, resolved statuses and numeric limits, each defined once |
| `loading.py` | File → raw table, with clear errors |
| `validation.py` | Decide what is invalid |
| `cleaning.py` | Decide what to do about it, and report it |
| `conversion.py` | Cleaned table → tickets |
| `analytics/` | One class per metric, plus an engine that runs a list of them |
| `writers.py` | All file output |
| `pipeline.py` | Wiring only |
| `processor.py` | Day 1 API (`TicketDataProcessor`, `build_analytics`) as thin wrappers |

The reasons for each split, the inheritance vs composition comparison, and how to add a metric are in **[docs/DESIGN.md](docs/DESIGN.md)**.

### The new metric (Task C)

`resolution_rate_by_category` is the share of each category's tickets that are `resolved` or `closed`, rounded to 2 places. Checked by hand on the sample data:

| Category | Resolved / total | Rate |
|---|---|---|
| account | 4 / 5 | 0.8 |
| billing | 4 / 6 | 0.67 |
| shipping | 3 / 5 | 0.6 |
| technical | 2 / 6 | 0.33 |
| unknown | 0 / 1 | 0.0 |

## Cleaning rules and assumptions

These are the same as Day 1 unless marked **new**.

| Input problem | Result |
|---|---|
| File missing, not UTF-8, or not parseable | `InvalidCSVError` |
| **New:** a row with more or fewer fields than the header | `InvalidCSVError` naming the line (Day 1 P0 fix) |
| Empty file, or header only | `EmptyDatasetError` |
| Required column missing | `MissingColumnsError` listing the missing columns |
| Blank or whitespace-only ticket ID | Row dropped and reported |
| Duplicate ticket ID | First occurrence kept (or `DuplicateTicketError` with `DuplicatePolicy.RAISE`) |
| Resolution time not a number, negative or infinite | Becomes missing (`NaN` / `None`) and is reported |
| Rating not a number, outside 1–5 or infinite | Becomes missing and is reported |
| **New:** priority other than low / medium / high | Becomes `unknown` and is reported as `invalid_priority` (none in the sample data) |
| Missing category / priority / status | `unknown` |
| Missing description | `""` |
| Saving over the raw file | Refused |

Other assumptions:
- Only `resolved` and `closed` count as resolved.
- Text such as `NA`, `N/A` or `NULL` is real data; only empty cells are missing.
- Source order decides which duplicate wins, because the data has no timestamps.

## Known limitations

- **Two representations.** Cleaning works on a pandas DataFrame and analytics works on `SupportTicket` objects, so the data is copied once. That is fine for files this size, but not for millions of rows.
- **Whole-file loading.** The file is read twice (once for the field-count check, once by pandas) and held in memory; there is no streaming.
- **Open vocabularies.** Category and status are not checked against an approved list. Any status other than `resolved`/`closed` counts as unresolved.
- **Strict row shape.** A row with the wrong number of fields rejects the whole file instead of being skipped, so one bad row stops the run. That is deliberate, because a shifted row is worse than no data.
- **`missing_values_before_cleaning` undercounts.** It counts only empty cells; whitespace-only cells become missing during cleaning, so they are counted only in `missing_values_after_cleaning`. Kept for Day 1 compatibility.
- **Strict compatibility layer.** `build_analytics(df)` now converts the frame to `SupportTicket`s, so a frame that was not produced by the cleaner (for example, one with priority `urgent`) raises `InvalidTicketError`. Day 1 accepted it silently.

## Day 1 compatibility

`TicketDataProcessor` and `build_analytics` still work exactly as before, and the 13 Day 1 tests pass unchanged. Internally they now call the new components. New code should use `TicketPipeline`.

## Other files

- `study/`: the four study-hour outputs (object model, composition vs inheritance, the data model, a design review of the Day 1 class)
- `VIVA_ANSWERS.md`, `DAILY_REPORT.md`
- `logs/day1_baseline_output.json`: Day 1 output captured before the refactor (used by the golden test)
- `logs/pipeline_run.txt`, `test_results.txt`: saved output from the final run
