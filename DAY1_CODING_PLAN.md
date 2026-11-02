# Day 1 Coding Session Plan — Support-Ticket Pipeline

The assignment allocates four implementation hours after four hours of study. Follow the order below so each stage produces something testable.

## 0–30 minutes — Create and inspect the raw dataset

**Goal:** create `data/tickets.csv` with at least 20 ticket rows and the seven required columns: `ticket_id`, `category`, `priority`, `description`, `resolution_time_hours`, `customer_rating`, and `status`.

**Work:** create realistic billing, technical, account, and shipping examples. Deliberately include missing cells, a repeated ticket ID, a non-numeric resolution time, a negative resolution time, and a rating outside 1–5. Keep the original file unchanged.

**Checkpoint:** open the CSV and confirm its header and row count. Identify the deliberately bad rows before writing cleaning logic.

## 30–120 minutes — Implement `TicketDataProcessor` (90 minutes)

1. **Read safely (15 min):** use `pandas.read_csv`; translate empty-file, parse, and read failures into clear exceptions.
2. **Validate schema (10 min):** compare the input columns with the required-column set; report all missing columns together.
3. **Decide duplicate policy (15 min):** document whether to keep first, keep latest using a timestamp, quarantine, or fail. Never silently deduplicate without a business rule.
4. **Clean values (30 min):** trim text, normalise identifiers, define missing-text placeholders, convert numeric fields, and invalidate bad ranges without fabricating values.
5. **Protect data and report (20 min):** retain the raw file; return the cleaned DataFrame; collect duplicate, missing, dropped-row, and invalid-value details; write to a distinct output path.

**Checkpoint:** run the processor and inspect both `data/tickets.csv` and `data/cleaned_tickets.csv`. Verify that the raw file is byte-for-byte unchanged.

## 120–180 minutes — Build analytics (60 minutes)

Implement one focused function that calculates:

- Ticket counts by priority.
- Average resolution time by category (ignore invalid/missing numeric values).
- Average valid customer rating.
- Unresolved ticket count using a documented status rule.
- Missing-value and invalid-record summaries.

Return a dictionary or readable report. Manually calculate at least two values from the CSV and compare them with the program output.

**Checkpoint:** the totals reconcile with the number of cleaned tickets; explain how missing numeric values affect each average.

## 180–240 minutes — Tests, README, run, and Git (60 minutes)

1. Write tests for valid input, malformed CSV, empty dataset, missing required columns, and duplicate IDs. Add tests for invalid numerics, missing values, raw-file protection, and analytics if time allows.
2. Run `python -m pytest`; fix the root cause of every failure and rerun the relevant tests.
3. Capture the actual test output. Write the README with setup, execution, assumptions, cleaning rules, and limitations.
4. Review the final file tree and ensure secrets, caches, virtual environments, and unnecessary generated files are excluded.
5. Create a clear branch and commit with a meaningful message. Record the branch/commit/PR reference.

**Checkpoint:** a fresh environment can install dependencies, run the script, and pass the tests using the README instructions.

## Definition of done

- At least 20 source rows and all seven required columns.
- Required-column checks and meaningful exceptions.
- Explicit, explainable handling of duplicates, missing values, and invalid numeric values.
- Raw CSV preserved and cleaned result saved separately.
- All four required analytics plus data-quality reporting.
- At least five meaningful passing tests and actual test output.
- README, Git history, and a developer who can explain and change the implementation live.

## Suggested work sequence in one view

| Time | Deliverable |
|---|---|
| 0:00–0:30 | Raw `tickets.csv` |
| 0:30–2:00 | `TicketDataProcessor` + cleaning report |
| 2:00–3:00 | Analytics dictionary/report + two manual checks |
| 3:00–4:00 | Automated tests + captured output + README + Git commit |
