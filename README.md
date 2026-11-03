# Support Ticket Pipeline: Day 2

This project reads a support-ticket CSV file, cleans the data, reports quality problems and produces summary analytics.

Day 1 built a working pipeline. Day 2 restructures it into small classes that each have a single responsibility, while keeping every Day 1 result unchanged. It also adds one new metric through an extension point, without modifying the existing metrics.

The original data file is never modified. All results are written to separate files.

## Contents

1. [Requirements](#requirements)
2. [Installation](#installation)
3. [Running the pipeline](#running-the-pipeline)
4. [Using the package in code](#using-the-package-in-code)
5. [Running the tests](#running-the-tests)
6. [Project structure](#project-structure)
7. [Cleaning rules](#cleaning-rules)
8. [Analytics output](#analytics-output)
9. [Changes from Day 1](#changes-from-day-1)
10. [Known limitations](#known-limitations)
11. [Further documentation](#further-documentation)

## Requirements

- Python 3.10 or newer (tested with Python 3.15)
- pandas 2.0 or newer, numpy 1.24 or newer, and pytest (tested with pandas 3.1 and pytest 9.2)

## Installation

Run these commands from the project folder.

```bash
python -m venv .venv
```

Activate the virtual environment:

| System | Command |
|---|---|
| Windows (PowerShell) | `.venv\Scripts\Activate.ps1` |
| macOS / Linux | `source .venv/bin/activate` |

Install the package and the test tool:

```bash
pip install -e . pytest
```

## Running the pipeline

```bash
python run_pipeline.py
```

The script reads `data/tickets.csv` and produces the following:

| Output | Description |
|---|---|
| `data/cleaned_tickets.csv` | The cleaned dataset |
| `data/quality_issues.csv` | One row for each source record that had a problem, with its issue codes |
| Terminal output | The analytics summary in JSON format |

In `quality_issues.csv`, `source_record_number` counts data rows from 1, starting with the first row after the header. Several issue codes for the same record are separated by semicolons.

The output files are generated locally and are not stored in Git. A reference copy of the analytics output is saved in `sample_analytics_output.json`.

## Using the package in code

```python
from ticket_pipeline import CsvTicketLoader, TicketPipeline

result = TicketPipeline(CsvTicketLoader("data/tickets.csv")).run()

result.frame      # the cleaned table (a pandas DataFrame)
result.tickets    # tuple of validated SupportTicket objects
result.report     # CleaningReport: what was removed or changed, and why
result.analytics  # dictionary of metrics and data-quality figures
```

By default, the first occurrence of a duplicate ticket ID is kept. To reject any file that contains duplicate IDs, pass a cleaner with the `RAISE` policy:

```python
from ticket_pipeline import CsvTicketLoader, DuplicatePolicy, TicketCleaner, TicketPipeline

pipeline = TicketPipeline(
    CsvTicketLoader("data/tickets.csv"),
    cleaner=TicketCleaner(DuplicatePolicy.RAISE),
)
pipeline.run()  # raises DuplicateTicketError, because the sample file contains T-002 twice
```

To save results, use the writer classes:

```python
from ticket_pipeline import CleanedCsvWriter, QualityReportWriter

CleanedCsvWriter("data/cleaned_tickets.csv", protected=["data/tickets.csv"]).write(result.frame)
QualityReportWriter("data/quality_issues.csv").write(result.report)
```

The `protected` argument prevents the writer from overwriting the original file.

## Running the tests

```bash
python -m pytest
```

The suite contains 107 tests. To list each test by name, run `python -m pytest -v --override-ini addopts=`. The output of the most recent full run is saved in `test_results.txt`.

| Test file | What it verifies |
|---|---|
| `tests/test_models.py` | Valid tickets are accepted; every invalid value is rejected; tickets cannot be changed after creation |
| `tests/test_loading.py` | Unreadable or malformed files produce clear errors, including rows with too many or too few fields |
| `tests/test_validation.py` | Numeric limits, required columns and priority values are checked correctly |
| `tests/test_cleaning.py` | Each cleaning rule works on in-memory data, and the input data is never altered |
| `tests/test_conversion_and_writers.py` | Cleaned rows convert to tickets correctly; output files are written in the expected format |
| `tests/test_analytics.py` | Each metric is correct; new metrics can be added without changing existing code |
| `tests/test_pipeline.py` | The full pipeline works end to end, and the Day 1 results are unchanged |
| `tests/test_processor.py` | The original 13 Day 1 tests, unmodified, still pass |

## Project structure

```
day2_ticket_pipeline/
├── data/tickets.csv            Sample input data (never modified)
├── src/ticket_pipeline/        The package
├── tests/                      Automated tests
├── study/                      Day 2 study exercises
├── docs/DESIGN.md              Design rationale
├── logs/                       Saved pipeline output and the Day 1 baseline
├── run_pipeline.py             Command-line entry point
├── sample_analytics_output.json
├── test_results.txt
├── VIVA_ANSWERS.md
├── DAILY_REPORT.md
├── pyproject.toml
└── requirements.txt
```

### How the components fit together

```
CsvTicketLoader  →  TicketCleaner  →  frame_to_tickets  →  TicketAnalytics
 reads the file      cleans the data    converts rows        calculates
 and checks rows     and reports it     into tickets         the metrics
```

`TicketPipeline` connects these four steps. Writing files is handled separately by `CleanedCsvWriter` and `QualityReportWriter`.

### Modules

| Module | Responsibility |
|---|---|
| `models.py` | Defines `SupportTicket`, `Priority`, `DuplicatePolicy` and `CleaningReport` |
| `schema.py` | Defines column names, resolved statuses and numeric limits, each in one place |
| `errors.py` | Defines the error types raised by the package |
| `loading.py` | Reads a CSV file into a table and reports file problems |
| `validation.py` | Identifies invalid values |
| `cleaning.py` | Decides how to handle invalid values and records what was done |
| `conversion.py` | Converts the cleaned table into `SupportTicket` objects |
| `analytics/` | Contains one class per metric and the engine that runs them |
| `writers.py` | Writes all output files |
| `pipeline.py` | Connects the components; contains no cleaning rules of its own |
| `processor.py` | Keeps the Day 1 interface working (see [Changes from Day 1](#changes-from-day-1)) |

## Cleaning rules

| Situation | Result |
|---|---|
| The file is missing, is not valid UTF-8, or cannot be parsed | `InvalidCSVError` is raised |
| A row has more or fewer fields than the header | `InvalidCSVError` is raised, stating the line number |
| The file is empty, or contains only a header | `EmptyDatasetError` is raised |
| A required column is missing | `MissingColumnsError` is raised, listing the missing columns |
| A ticket ID is empty or contains only spaces | The row is removed and reported |
| A ticket ID appears more than once | The first occurrence is kept and later copies are removed and reported. With `DuplicatePolicy.RAISE`, `DuplicateTicketError` is raised instead |
| A resolution time is not a number, is negative or is infinite | The value is set to missing and reported |
| A customer rating is not a number, is outside 1–5 or is infinite | The value is set to missing and reported |
| A priority is not `low`, `medium` or `high` | The value is set to `unknown` and reported as `invalid_priority` |
| A category, priority or status is missing | The value is set to `unknown` |
| A description is missing | The value is set to an empty string |
| Text has extra spaces or mixed case | Spaces are trimmed; IDs are converted to upper case; category, priority and status are converted to lower case |
| An output path is the same as the input file | The write is refused |

These are the assumptions behind the rules:

- A ticket counts as resolved only when its status is `resolved` or `closed`.
- Values such as `NA`, `N/A` and `NULL` are treated as real text. Only empty cells count as missing.
- The data contains no timestamps, so the order of rows in the file decides which duplicate is kept.
- Missing numbers are never estimated. They stay missing, so averages use only real values.

## Analytics output

| Field | Meaning |
|---|---|
| `ticket_count_by_priority` | Number of tickets for each priority |
| `average_resolution_time_hours_by_category` | Average resolution time for each category, using valid times only |
| `average_customer_rating` | Average of all valid ratings, or `null` if there are none |
| `unresolved_ticket_count` | Number of tickets that are not `resolved` or `closed` |
| `resolution_rate_by_category` | **New in Day 2.** Share of tickets resolved in each category, from 0 to 1 |
| `missing_values_before_cleaning` | Empty cells per column in the original file |
| `missing_values_after_cleaning` | Missing values per column after cleaning |
| `invalid_numeric_values` | Number of invalid numeric values per column |
| `invalid_record_count` | Number of source records with at least one problem |
| `duplicate_ticket_ids` | Ticket IDs that appeared more than once |
| `rows_dropped_missing_ticket_id` | Number of rows removed because they had no ticket ID |

Averages and rates are rounded to two decimal places.

### Checking the sample results by hand

The sample file contains 25 rows. One row has no ticket ID and one is a duplicate, so 23 tickets remain.

The resolution rates for the sample data can be checked by counting statuses:

| Category | Resolved / total | Rate |
|---|---|---|
| account | 4 / 5 | 0.80 |
| billing | 4 / 6 | 0.67 |
| shipping | 3 / 5 | 0.60 |
| technical | 2 / 6 | 0.33 |
| unknown | 0 / 1 | 0.00 |

The JSON output prints these values without trailing zeros, for example `0.8`.

## Changes from Day 1

Day 1 results are unchanged. An automated test confirms that the analytics output for the sample file matches the Day 1 output exactly, apart from the one new field.

The Day 1 classes `TicketDataProcessor` and `build_analytics` are still available. They now call the new components internally, and the 13 Day 1 tests pass without modification. New code should use `TicketPipeline`.

There are three deliberate changes in behaviour:

1. **Rows with the wrong number of fields are rejected.** In Day 1, a row with one extra field caused every value in that row to shift one column to the left, without any error. The loader now stops with an error that names the line.
2. **Unrecognised priorities are reported.** A priority other than `low`, `medium` or `high` is set to `unknown` and recorded as an issue. The sample data has no such values.
3. **`build_analytics` is stricter.** It now validates every row. A table that was not produced by the cleaner, for example one with the priority `urgent`, raises `InvalidTicketError`. Day 1 accepted such tables without complaint.

## Known limitations

- **The data is held twice.** Cleaning works on a pandas table and analytics works on `SupportTicket` objects, so the data is copied once. This is acceptable for small files but not for very large ones.
- **The whole file is read into memory.** The file is read twice, once to check row lengths and once to load it. Streaming is not supported.
- **One malformed row stops the whole run.** This is intentional, because silently shifted data is worse than no data.
- **Categories and statuses are not checked against an approved list.** Any status other than `resolved` or `closed` counts as unresolved.
- **`missing_values_before_cleaning` counts empty cells only.** A cell that contains only spaces is not counted there, although cleaning treats it as missing. In text columns such a cell is then filled with `unknown`, so it is not counted in `missing_values_after_cleaning` either. This matches the Day 1 behaviour.

## Further documentation

| Document | Contents |
|---|---|
| [docs/DESIGN.md](docs/DESIGN.md) | Why each component exists, the comparison of inheritance and composition, and how to add a new metric |
| `study/` | The four Day 2 study exercises |
| `VIVA_ANSWERS.md` | Answers to the Day 2 viva questions |
| `DAILY_REPORT.md` | The Day 2 daily report |
