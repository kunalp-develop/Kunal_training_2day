# Day 1 — Support Ticket Data Pipeline

This project loads a messy support-ticket CSV, checks it, cleans it, and prints a simple summary. 


The main idea: **never change the original file**. Read `data/tickets.csv`, clean a copy, save that copy as `data/cleaned_tickets.csv`, and report what was wrong.

---

## Why this approach?

Support tickets in real files often have blank IDs, duplicate IDs, mixed case, extra spaces, and numbers that are not numbers. If we skip cleaning, later analytics (or models) will be wrong.

So the code:

1. **Stops early** when the file itself is unusable (empty, not a CSV, missing columns).
2. **Cleans in a visible order** so each rule is easy to explain in a viva.
3. **Keeps a report** of what was dropped or marked invalid. Cleaning without a report hides problems.
4. **Writes a new file** instead of overwriting the raw CSV, so you can always go back.

---

## How the pipeline runs

```text
tickets.csv  →  TicketDataProcessor.process()  →  cleaned table
                                              →  processor.report (quality notes)
                 save_cleaned_data()           →  cleaned_tickets.csv
                 build_analytics()             →  JSON summary printed in the terminal
```

`run_pipeline.py` is the script that does those steps in order.

---

## Project files

```text
day1_ticket_pipeline/
├── data/
│   ├── tickets.csv                  Raw sample data (do not overwrite)
│   ├── cleaned_tickets.csv          Cleaned output (created by the run)
│   └── quality_issues.csv           Row-level issues (created by the run)
├── src/ticket_pipeline/
│   ├── __init__.py                  Public names you can import
│   ├── processor.py                 Load, validate, clean
│   └── analytics.py                 Counts and averages
├── tests/test_processor.py          12 automated tests
├── run_pipeline.py                  One command to run everything
├── requirements.txt                 pandas, numpy, pytest
├── pyproject.toml                   Package + pytest settings
├── sample_analytics_output.json     Example summary from the sample CSV
├── DAY1_CODING_PLAN.md              Planning notes
└── README.md
```

---

## Setup

Python 3.10 or newer.

```bash
python -m venv .venv
# Windows PowerShell
.venv\Scripts\Activate.ps1
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
```

---

## Run the pipeline

From the project folder:

```bash
python run_pipeline.py
```

This reads `data/tickets.csv`, writes `data/cleaned_tickets.csv` and `data/quality_issues.csv`, and prints the analytics JSON. The raw file stays unchanged. Both output files are local-only (listed in `.gitignore`). The quality CSV has one row per record with an issue; `source_record_number` is one-based, starting at the first data row after the header, and `issues` contains semicolon-separated issue codes.

Use the same steps in your own code:

```python
from pathlib import Path
from ticket_pipeline import TicketDataProcessor, build_analytics

raw_file = Path("data/tickets.csv")
clean_file = Path("data/cleaned_tickets.csv")

processor = TicketDataProcessor(raw_file, output_path=clean_file)
cleaned = processor.process()
processor.save_cleaned_data(cleaned)
report = build_analytics(cleaned, processor.report)
print(report)
```

---

## Code explained in simple language

### `run_pipeline.py` — `main()`

**What it does:** Creates a processor, cleans the sample CSV, saves the result, builds analytics, prints JSON.

**Why:** One entry point so you do not have to remember import paths. It adds `src/` to Python’s path so `ticket_pipeline` can be imported from the project root.

---

### `src/ticket_pipeline/__init__.py`

**What it does:** Re-exports `TicketDataProcessor`, `build_analytics`, and the three custom errors.

**Why:** Other files can write `from ticket_pipeline import TicketDataProcessor` instead of importing inner modules.

---

### Custom errors in `processor.py`

These are small subclasses of `ValueError`. They exist so tests and callers can catch **specific** failures instead of a generic “something went wrong”.

| Error | When it is raised | Why |
|---|---|---|
| `InvalidCSVError` | File is not a readable CSV | A broken file should not be silently treated as empty data |
| `EmptyDatasetError` | No header, or header but zero ticket rows | Analytics on nothing is misleading |
| `MissingColumnsError` | A required column is absent | Cleaning cannot start if the schema is incomplete |

---

### `TicketDataProcessor.__init__(input_path, output_path, duplicate_policy)`

**What it does:** Stores paths, checks that `duplicate_policy` is `'keep_first'` or `'raise'`, and starts an empty `report`.

**Why:** Setup happens once. The policy is locked before any rows are touched, so cleaning behaviour is predictable.

---

### `_read_csv()`

**What it does:** Reads the CSV with pandas, treating empty cells as missing but preserving text such as `"NA"`, `"N/A"`, and `"NULL"`. Turns pandas/file errors into `InvalidCSVError` or `EmptyDatasetError`.

**Why:** Pandas error messages are technical. The wrapper gives a sentence a teammate can understand. Default NA-token parsing can silently erase legitimate identifiers and text, so only empty CSV fields count as missing.

---

### `_validate_columns(frame)`

**What it does:** Compares the file’s column names to `REQUIRED_COLUMNS` (`ticket_id`, `category`, `priority`, `description`, `resolution_time_hours`, `customer_rating`, `status`). Raises `MissingColumnsError` listing what is missing.

**Why:** If `priority` is missing, later analytics for “tickets by priority” would crash or invent data. Fail before cleaning.

---

### `_normalise_text(series)`

**What it does:** Converts a column to text, trims spaces, and treats `"   "` as missing.

**Why:** `" Billing "` and `"billing"` should be the same. A cell with only spaces is not a real value.

---

### `process()` — the main cleaning function

This is the heart of the project. It runs in this order, for a reason:

1. **Read and check columns**  
   Do not clean a file that is the wrong shape.

2. **Normalise text**  
   Uppercase `ticket_id`. Lowercase `category`, `priority`, `status`. Trim `description`.  
   **Why:** Duplicate IDs like `t-1` and `T-1` should match. Counts by priority should not split `High` and `high`.

3. **Drop rows with no ticket ID**  
   **Why:** Without an ID you cannot track or de-duplicate a ticket. The count of dropped rows goes into the report.

4. **Handle duplicate IDs**  
   Default `keep_first`: keep the first row in file order, drop later copies.  
   `duplicate_policy="raise"`: stop and ask a human to review.  
   **Why:** This is a training default, not a universal business rule. Source order is treated as “first write wins” unless you choose to fail closed.

5. **Fix numeric columns**  
   - `resolution_time_hours`: must be a real number ≥ 0 (zero is allowed).  
   - `customer_rating`: must be a real number from 1 to 5.  
   Bad values (text, infinity, negatives, rating 6) become missing (`NaN`).  
   **Why:** We do not guess a rating or a time. Invented numbers would make averages look better than they are.

6. **Fill remaining text gaps**  
   Missing category / priority / status → `"unknown"`. Missing description → `""`.  
   **Why:** Text fields need a visible placeholder so they still group in counts. Numbers stay `NaN` on purpose.

7. **Build `self.report`**  
   Source row count, cleaned row count, dropped IDs, duplicate IDs, missing values before/after, invalid number counts, and reasons per original row index.

Returns a cleaned pandas DataFrame with a fresh 0-based index.

---

### `save_cleaned_data(cleaned_data, output_path)`

**What it does:** Writes the cleaned table to CSV. Creates parent folders if needed. Refuses if the destination is the same as the raw input.

**Why:** Overwriting the original file would destroy evidence of data quality issues.

---

### `build_analytics(cleaned_data, processing_report)` in `analytics.py`

**What it does:** Builds one dictionary (easy to print as JSON).

| Field | Meaning | Why this definition |
|---|---|---|
| `ticket_count_by_priority` | How many cleaned tickets per priority, including `unknown` | Shows workload mix after cleaning |
| `average_resolution_time_hours_by_category` | Mean of **valid** times only; skip categories with no valid times | Missing times must not become 0 |
| `average_customer_rating` | Mean of valid ratings, rounded to 2 decimals; `None` if none exist | Same reason: do not average in invented scores |
| `unresolved_ticket_count` | Status is unresolved unless it is `resolved` or `closed` | Open, pending, in_progress, and unknown all still need work |
| Quality fields copied from `processor.report` | Missing values, invalid numbers, duplicates, dropped IDs | Analytics and quality stay in one output |

If the cleaned table is empty, counts are zero / empty / `None` instead of crashing.

---

## Cleaning rules (quick table)

| Problem | What the code does |
|---|---|
| Cannot parse the file | `InvalidCSVError` |
| No ticket rows | `EmptyDatasetError` |
| Missing required column | `MissingColumnsError` |
| Blank ticket ID | Drop the row |
| Duplicate ticket ID | Keep first (or raise if policy is `raise`) |
| Missing category / priority / status | Fill `unknown` |
| Missing description | Fill empty string |
| Missing number | Leave as `NaN` |
| Bad resolution time | Set to `NaN` |
| Rating outside 1–5 | Set to `NaN` |
| Extra spaces / mixed case | Trim; ID upper; labels lower |
| Save path = raw path | Refuse to write |

These are **training assumptions**. A real company might use timestamps for duplicates or a fixed list of allowed categories.

## Known limitations

- Duplicate IDs use the first source occurrence because the sample has no timestamp or other rule for choosing a canonical record.
- Resolution times must be finite and nonnegative; customer ratings must be finite and between 1 and 5 inclusive. These ranges are assignment assumptions, not configurable business rules.
- Category, priority, and status values are normalized but not checked against an approved vocabulary. Unrecognized statuses remain unresolved; only `resolved` and `closed` count as complete.
- The quality CSV identifies records by their one-based data-row position rather than ticket ID, so row numbers refer to the unchanged source file.

---

## Tests

```bash
python -m pytest -v --override-ini addopts=
```

There are **13 tests** in `tests/test_processor.py`. Each one checks one behaviour:

| Test | What it proves |
|---|---|
| `test_valid_input_is_cleaned_and_raw_file_is_unchanged` | Happy path works; original CSV is not edited |
| `test_na_like_text_values_are_preserved_but_empty_cells_are_missing` | NA-like text is retained while blank fields remain missing |
| `test_invalid_csv_raises_clear_exception` | Broken CSV → `InvalidCSVError` |
| `test_empty_dataset_raises_clear_exception` | Header only → `EmptyDatasetError` |
| `test_missing_required_columns_are_reported` | Missing columns are named in the error |
| `test_duplicate_ids_keep_first_and_are_reported` | First duplicate is kept; report lists the ID |
| `test_invalid_numeric_values_become_missing_and_are_counted` | Bad times/ratings become `NaN` and are counted |
| `test_missing_ticket_id_is_dropped_and_missing_text_gets_placeholder` | Blank ID dropped; other blanks become `unknown` / `""` |
| `test_processor_refuses_to_overwrite_raw_csv` | Save will not replace the input file |
| `test_duplicate_policy_can_fail_closed` | `duplicate_policy="raise"` stops on duplicates |
| `test_analytics_calculates_priority_rating_and_unresolved_count` | Priority counts, billing average, rating, unresolved count |

The `[ 10%]`, `[ 20%]`, … numbers in pytest are **progress**, not a score. `13 passed` means every test succeeded.

---

## Check the sample file by hand

Using `data/tickets.csv` and the rules above:

1. **23 tickets kept:** 25 source rows − 1 missing ID − 1 duplicate = 23. Priorities: high 7 + low 7 + medium 8 + unknown 1.
2. **Billing average 3.4 hours:** valid times 2.5, 3.5, 6.0, 3.0, 2.0 → sum 17.0 → 17 / 5 = 3.4.
3. **10 unresolved:** statuses that are not `resolved` or `closed`.

Full printed output is in `sample_analytics_output.json`.

---

## What this project does not do

- Guess missing numbers
- Check category/priority against an official list
- Detect “same ticket, different wording”
- Train a model, split train/test, or build RAG/agents/APIs

Next steps in a production system: logging, config files, schema versions, and monitoring.

---

## Git

Remote: [https://github.com/kunalp-develop/Kunal_training_1day-](https://github.com/kunalp-develop/Kunal_training_1day-)  
Branch: `day1-ticket-pipeline`

Do not commit `.venv`, `__pycache__`, `.pytest_cache`, or `data/cleaned_tickets.csv`.
