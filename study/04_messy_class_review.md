# Study 4: design review of a messy class

**Class reviewed:** Day 1 `TicketDataProcessor`, as of commit `84f9187`. View it with `git show 84f9187:src/ticket_pipeline/processor.py`. It was not written to be messy, but it grew into the classic god-object shape, so it is a good real example.

## Responsibilities it held (single responsibility check)

`process()` alone was about 85 lines and did all of this:

1. Path handling (`input_path`, `output_path`)
2. CSV reading and error translation (`_read_csv`)
3. Schema checking (`_validate_columns`)
4. Text normalisation
5. Dropping rows with a missing ID
6. Duplicate detection and policy
7. Numeric parsing and range checks
8. Filling missing text
9. Building the report
10. Writing files (`save_cleaned_data`)

Ten reasons to change one class is a single-responsibility failure. A change to the rating range and a change to the output folder both edit the same file.

## Issues found

| # | Issue | Principle | Where | Fixed by |
|---|---|---|---|---|
| 1 | One class does reading, validating, cleaning, reporting and saving | Single responsibility, cohesion | whole class | `CsvTicketLoader`, `validation`, `TicketCleaner`, `writers` |
| 2 | `self.report = {}` until `process()` runs, so callers can read an empty report without any error | Invalid state, temporal coupling | `__init__`, `process` | `clean()` returns `CleaningResult(frame, report)` |
| 3 | Rules hidden in branches: `if column == "resolution_time_hours" ... elif column == "customer_rating"` | Open/closed: a new rule means editing the method | numeric loop | `NumericRule` objects in `schema.py` |
| 4 | The rule *text* (`NUMERIC_RULES` dict of messages) and the rule *logic* (the `if` branches) were defined in two places and could drift | Cohesion | module top and `process` | one `NumericRule` has both `accepts()` and `description` |
| 5 | Duplicate policy is a magic string (`"keep_first"` / `"raise"`) checked by hand | Make invalid state unrepresentable | `__init__` | `DuplicatePolicy` Enum |
| 6 | File I/O inside the processing class: you cannot clean data that is not in a file | Dependency boundaries, testability | `_read_csv`, `save_cleaned_data` | loader and writers are separate; the cleaner takes a DataFrame |
| 7 | Testing any cleaning rule requires writing a CSV to disk first | Testability | tests | `test_cleaning.py` builds DataFrames in memory |
| 8 | A nested function (`mark_invalid`) mutates a dict defined in the outer function | Hidden coupling | `process` | `ValidationIssue` values collected in a list |
| 9 | Duplicate errors raised as plain `ValueError`, so callers cannot tell them apart from other errors | Error design | duplicate branch | `DuplicateTicketError` (still a `ValueError` for compatibility) |
| 10 | The raw read had no field-count check, so an extra field shifted every column (Day 1 P0) | Correctness at the boundary | `_read_csv` | `CsvTicketLoader._check_field_counts` |
| 11 | Analytics (`build_analytics`) also copied the cleaning report into its output, and every metric was hard-coded | Single responsibility, open/closed | `analytics.py` | one class per metric; the pipeline merges the report |

## What was fine and kept

- Never overwriting the raw file: the guard moved to `CleanedCsvWriter`.
- Specific exception classes: kept, now under one base class.
- Explicit, documented cleaning policies: kept unchanged, and the golden test proves it.
