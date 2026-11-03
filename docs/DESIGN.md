# Design: why the pipeline is split this way

## The problem with Day 1

Day 1 had one class, `TicketDataProcessor`, that did eight jobs: work out paths, read the CSV, check columns, normalise text, remove duplicates, check numbers, fill gaps, build the report and save files. `build_analytics` hard-coded four metrics and also copied the cleaning report into its output.

That worked, but:
- **Changing one rule meant editing the big `process()` method.** For example, the rating range sat in an `if column == "customer_rating"` branch.
- **Testing analytics needed a CSV file on disk**, because the only way to get a cleaned table was to read one.
- **`processor.report` was `{}` until `process()` ran.** The object was in a half-ready state, and code that read `report` too early got wrong answers without any error.
- **Adding a metric meant editing `build_analytics`**, risking the four metrics that already worked.

## One job per component

| Component | Its one job | Depends on |
|---|---|---|
| `errors.py` | Name each kind of failure | nothing |
| `schema.py` | Column names, resolved statuses, numeric limits (`NumericRule`) | nothing |
| `models.py` | `SupportTicket` (always valid), `Priority`, `CleaningReport` | errors, schema |
| `loading.py` · `CsvTicketLoader` | Turn a file into a raw table, or fail clearly | errors |
| `validation.py` | Decide *what is invalid* (missing columns, bad numbers, unknown priority) | models, schema |
| `cleaning.py` · `TicketCleaner` | Decide *what to do about it* (drop, mask, fill) and report it | validation, models |
| `conversion.py` | Cleaned table → tuple of `SupportTicket` | models |
| `analytics/` | One class per metric; `TicketAnalytics` runs a list of them | models |
| `writers.py` | All file output | models |
| `pipeline.py` · `TicketPipeline` | Wire the parts together; owns no rules | the parts above |
| `processor.py` | Day 1 API kept as thin wrappers | the parts above |
| `run_pipeline.py` | Choose the files and print the result | the package |

Dependencies point one way only: down towards `models`, `schema` and `errors`, which import nothing from the rest of the package. Nothing imports `pipeline.py` except the entry points, so any part can be reused or tested on its own.

```
run_pipeline.py ─► pipeline ─► loading · cleaning · conversion · analytics
                    writers ─┘        │          │          │
                                      ▼          ▼          ▼
                                 validation ─► models ─► schema · errors
```

## Two designs compared

**Design 1, inheritance:** `BaseProcessor` → `CleaningProcessor(BaseProcessor)` → `AnalyticsProcessor(CleaningProcessor)`. Each step inherits the one before it.
- Analytics "is a" cleaning processor? No. The relationship is not true, so the hierarchy is only a way to share code.
- To test analytics you must build, and feed a file to, every parent class.
- Changing a parent can break every child (the fragile base class problem).
- To use a different cleaning policy you need yet another subclass.

**Design 2, composition (chosen):** `TicketPipeline(source, cleaner, analytics)` *has* a source, a cleaner and an analytics engine, passed in through the constructor.
- Each part is a small class you can create and test alone.
- Tests pass in fakes, such as `FakeLoader` in `tests/test_pipeline.py`, so no disk is needed.
- Swapping behaviour means passing a different object, not writing a subclass: `TicketCleaner(DuplicatePolicy.RAISE)` or `TicketAnalytics([...])`.

Inheritance is used once, in `errors.py`, where "every error *is a* `TicketPipelineError`" really is true and lets callers catch the whole family with one `except`.

## How the design prevents invalid state

- **`SupportTicket` is a frozen dataclass.** `__post_init__` rejects an empty ID, a rating outside 1–5, a negative or infinite resolution time, a priority that is not a `Priority`, and wrong types. Being frozen stops changes later, so a ticket that exists is always valid.
- **"Missing" is represented explicitly:** `None` for numbers, and `Priority.UNKNOWN` for a missing or unrecognised priority.
- **`TicketCleaner.clean()` returns `CleaningResult(frame, report)`.** Nothing is stored on the cleaner, so there is no "before `process()`" state, and one cleaner can clean many files.
- **Class-level attributes are immutable only:** `RESOLVED_STATUSES` is a `frozenset` and each operation's `name` is a `str`. Mutable defaults use `field(default_factory=dict)`. `tests/test_models.py` checks that two reports do not share one dict.
- **`frame_to_tickets` is the boundary check.** If a cleaned row cannot become a ticket, cleaning has a bug, so it raises instead of passing bad data on.

## Adding a metric

1. Write a class with `name: ClassVar[str] = "your_key"` and `compute(self, tickets) -> value`.
2. Add it to `default_operations()` in `analytics/engine.py`, or pass it straight to `TicketAnalytics([...])`.
3. Test it on a few hand-built `SupportTicket`s.

Nothing else changes, because the engine has no `if` per metric. `ResolutionRateByCategory` (Task C) was added exactly this way. The golden test in `tests/test_pipeline.py` shows the Day 1 numbers did not move.

## Trade-offs

- **Two representations (DataFrame, then `SupportTicket`).** Cleaning is easier with column operations, while analytics is easier and safer on validated objects. The copy costs a little time; that is fine at this data size.
- **One Protocol, not many.** Only analytics has more than one implementation, so only it gets an interface (`AnalyticsOperation`). The loader and cleaner are plain classes. Adding interfaces for things with one implementation would be ceremony with no benefit.
