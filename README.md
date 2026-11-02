# Day 1 — Python Engineering & Support-Ticket Data Pipeline

A small, testable Python project for loading, validating, cleaning, and analysing support-ticket CSV data. It implements **only the reliable data-foundation scope** from the Day 1 assignment; it does not train an ML model or implement RAG/agents.

## 1. Project layout

```text
day1_ticket_pipeline/
├── data/
│   └── tickets.csv                 # Raw sample input; never overwritten
├── src/
│   └── ticket_pipeline/
│       ├── __init__.py
│       ├── processor.py            # CSV loading, validation, cleaning, report
│       └── analytics.py            # Required summary analytics
├── tests/
│   └── test_processor.py           # 10 automated tests
├── run_pipeline.py                 # End-to-end runner
├── requirements.txt
├── pyproject.toml
├── test_results.txt                # Actual pytest output from this run
├── sample_analytics_output.json    # Actual output from the supplied sample CSV
├── VIVA_ANSWERS.md
├── DAY1_CODING_PLAN.md
└── README.md
```

## 2. Setup

Use Python 3.10 or newer. From this project directory, create and activate a virtual environment, then install dependencies:

```bash
python -m venv .venv
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# macOS/Linux:
source .venv/bin/activate

python -m pip install --upgrade pip
pip install -r requirements.txt
```

## 3. Run the pipeline

From the project root:

```bash
python run_pipeline.py
```

The script reads `data/tickets.csv`, cleans it, writes `data/cleaned_tickets.csv`, and prints a JSON analytics report. The raw file is not modified. The cleaned output is generated locally and is excluded from Git by `.gitignore`.

You can also use the package in your own Python code:

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

By default, `TicketDataProcessor` keeps the first occurrence of a duplicate ID. To fail closed and force a human review instead:

```python
processor = TicketDataProcessor(raw_file, duplicate_policy="raise")
```

## 4. Cleaning rules and assumptions

These are explicit **training-project assumptions**, not universal business rules:

| Data issue | Rule applied |
|---|---|
| Missing required column | Stop before cleaning and raise `MissingColumnsError` with the missing column names. |
| CSV cannot be parsed / file cannot be read | Raise `InvalidCSVError` with a useful message. |
| Header exists but there are no records | Raise `EmptyDatasetError`. |
| Missing/blank `ticket_id` | Drop the row because it cannot be reliably tracked; report the count. |
| Duplicate `ticket_id` | Default: retain the first row in source order and report the duplicate IDs and removed-row count. This assumes source order is authoritative. Configure `duplicate_policy="raise"` to reject duplicates instead. |
| Missing `category`, `priority`, or `status` | Fill with the explicit label `unknown`. |
| Missing `description` | Fill with an empty string. |
| Missing numeric value | Keep as `NaN`; do not invent or impute a value. |
| Invalid `resolution_time_hours` | Convert non-numeric, non-finite, or negative values to `NaN`. Zero is allowed. |
| Invalid `customer_rating` | Convert non-numeric, non-finite, or values outside 1–5 to `NaN`. |
| Whitespace and text case | Trim text; uppercase ticket IDs and lowercase category, priority, and status values. |
| Saving cleaned data | Write to a separate path; explicitly refuse to overwrite the raw input file. |

The processor stores a `report` dictionary with before/after missing-value counts, duplicate details, invalid numeric counts, dropped rows, and invalid-record reasons. Row indexes in `invalid_record_reasons` refer to zero-based row indexes from the loaded CSV (excluding the header).

## 5. Analytics definitions

- **Tickets by priority:** count of retained cleaned tickets, including the `unknown` bucket.
- **Average resolution time by category:** arithmetic mean of valid (non-missing) resolution times; categories with no valid times are omitted.
- **Average customer rating:** arithmetic mean of valid ratings only; returns `null`/`None` if none are valid.
- **Unresolved tickets:** every status other than `resolved` or `closed` is treated as unresolved. This intentionally includes `open`, `pending`, `in_progress`, and `unknown`.
- **Data-quality summary:** reports missing values before and after cleaning, invalid numeric values, duplicate IDs, dropped missing-ID rows, and distinct invalid records.

## 6. Run the tests

```bash
python -m pytest
```

The captured result in `test_results.txt` is:

```text
..........                                                               [100%]
10 passed
```

The tests cover valid input and preservation of the raw file, malformed CSV, empty data, missing required columns, duplicate handling, invalid numeric values, missing-value rules, refusal to overwrite raw data, strict duplicate handling, and analytics calculations.

## 7. Manual verification examples

Using the supplied sample file and the documented rules:

1. **Priority total:** high 7 + low 7 + medium 8 + unknown 1 = **23 retained tickets**. This matches the cleaned row count (25 source rows − 1 missing-ID row − 1 duplicate row = 23).
2. **Billing average resolution time:** valid values are 2.5, 3.5, 6.0, 3.0, and 2.0 hours. Their sum is 17.0; 17.0 ÷ 5 = **3.4 hours**, matching the report.
3. **Unresolved count:** statuses not in `{resolved, closed}` total **10** under the stated definition.

The complete sample output is saved in `sample_analytics_output.json`.

## 8. Limitations and next improvements

- `keep_first` is only safe when source order is a valid business rule. Real systems should use an agreed event timestamp, version, source-of-truth rule, or manual review.
- The project does not infer missing numeric values, validate category/priority vocabularies against an external master list, or deduplicate semantically similar descriptions.
- Analytics are descriptive, not predictive. There is no model training, train/test split, NLP, RAG, agent, API, or deployment code in this Day 1 scope.
- A production pipeline would add structured logging, configuration, schema versioning, stronger data contracts, and monitoring.

## 9. Suggested Git workflow

```bash
git init
git switch -c day1-ticket-pipeline
git add .
git commit -m "Build Day 1 support ticket data pipeline"
```

Do not commit secrets, virtual environments, caches, or generated output files. Include the branch name and commit hash in the daily submission.

## 10. Day 1 completion checklist

- [x] `tickets.csv` with more than 20 rows and deliberate quality issues
- [x] Reusable `TicketDataProcessor`
- [x] Required-column validation and explicit cleaning rules
- [x] Separate cleaned CSV output; raw file preserved
- [x] Structured analytics report
- [x] At least five automated tests (10 included)
- [x] Actual test output captured
- [x] README, assumptions, limitations, and Git commands
- [ ] Student's own Git branch/commit/PR reference added
- [ ] Student completes the daily report in their own words

**Training reminder:** use this project as a guided reference, not as a substitute for understanding. Explain each rule, change a test or add an edge case, rerun the suite, and be ready to modify the code live.
