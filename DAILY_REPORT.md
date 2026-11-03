# Daily report: Day 02 (2026-11-03)

## 1. Topics learned

- **Classes and the object model:** instance vs class attributes, `self`, attribute lookup order.
- **OOP design:** encapsulation, composition over inheritance, polymorphism, abstract interfaces (`ABC`, `typing.Protocol`).
- **The Python data model:** properties, `__repr__` vs `__str__`, dataclasses (`frozen`, `slots`, `__post_init__`, `field(default_factory=...)`), Enums.
- **Design review:** single responsibility, cohesion, coupling, dependency direction, testability.

## 2. What I can explain without notes

- Why `TicketPipeline` uses composition and why the errors are the only inheritance.
- Why a mutable class attribute is shared, and how `default_factory` fixes it.
- How `SupportTicket` makes invalid state impossible: it is validated once and then frozen.
- How a new metric is added without changing the engine.
- How the fake loader lets the pipeline be tested without files.
- The root cause of the Day 1 extra-field bug.

## 3. Implementation completed

- **P0 fix:** CSV rows whose field count differs from the header are rejected, with the line number.
- **Task A:** `SupportTicket` model with validation and immutability; `Priority` and `DuplicatePolicy` enums; `CleaningReport`.
- **Task B:** the Day 1 god class split into `CsvTicketLoader`, `validation`, `TicketCleaner`, `frame_to_tickets` and the writers. The Day 1 API is kept as thin wrappers.
- **Task C:** analytics rebuilt as metric classes behind the `AnalyticsOperation` protocol; new `resolution_rate_by_category` metric.
- **Task D:** 107 tests, `docs/DESIGN.md`, README, the study outputs and the viva answers. Each step is committed separately.

## 4. Test results

`python -m pytest -v --override-ini addopts=` → **107 passed**. The full output is in `test_results.txt`.
- The 13 Day 1 tests pass without changes.
- The golden test confirms the sample output equals the Day 1 baseline plus only the new metric.
- `cleaned_tickets.csv` and `quality_issues.csv` are byte-identical to the Day 1 versions.

## 5. One bug and its root cause

**Bug:** a CSV row with one extra field, such as `T-101,Billing,High,Valid,2,5,Closed,UNEXPECTED`, loaded with every value shifted one column to the left, and no error was raised.

**Root cause:** when a data row has more fields than the header, `pandas.read_csv` assumes the first field is an index column. The ticket ID became the row label and `Billing` landed in `ticket_id`.

**Fix:** before parsing, the loader reads the file with Python's `csv` module and checks every record against the header length. Quoted commas are handled correctly. A mismatch raises `InvalidCSVError` naming the line. `index_col=False` is also passed to pandas. A test with the exact reproducer was written first, failed, and passes now.

## 6. One design decision and why

**Analytics as a list of small metric objects behind a `Protocol`, composed by `TicketAnalytics`.** Day 1's `build_analytics` hard-coded every metric, so adding one meant editing working code. Now a metric is a class with `name` and `compute(tickets)`, and the engine just runs a list of them.
- Adding `resolution_rate_by_category` needed no change to the engine or to the other metrics.
- Each metric is tested on a few hand-built tickets.
- I used a `Protocol` (structural typing) rather than a base class, so metrics do not need to inherit anything.

## 7. Blocker and what I tried

**Blocker:** the first commit in the new Day 2 repository failed with "Author identity unknown". The new repo had no git user configured, and there was no global identity.

**What I tried:** I checked the Day 1 repository and found the identity was set locally there, not globally. I set the same name and email locally in the Day 2 repo (`git config user.name` / `user.email`), and the commit succeeded. Lesson: local git config does not carry over to a new clone.

## 8. Tomorrow's plan

- Create the Day 2 GitHub repository and push.
- Re-read the viva answers and practise explaining `models.py`, `cleaning.py` and `analytics/` without notes.
- Read the Day 3 brief and find which Day 2 components it builds on.
