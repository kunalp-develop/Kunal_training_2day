# Viva answers (Day 2)

## 1. When should you use composition instead of inheritance?

Use inheritance only when the child really *is a* kind of the parent and can be used anywhere the parent is expected. Use composition when an object *uses* or *has* another object. That is most of the time.

In this project:
- `TicketPipeline` *has* a source, a cleaner and an analytics engine. It is not a kind of any of them, so they are passed into its constructor.
- To change behaviour I pass different parts, for example `TicketCleaner(DuplicatePolicy.RAISE)`, or a fake loader in tests, instead of writing a subclass.
- The one place I used inheritance is the errors: `InvalidCSVError` really *is a* `TicketPipelineError`, so callers can catch the whole family with one `except`.

Inheritance ties the child to the parent's internals, so a change in the parent can silently break the child. Composition only depends on the small public methods (`load()`, `clean()`, `compute()`).

## 2. What is the risk of mutable class attributes?

A class attribute is created once and shared by every instance. If it is mutable, such as a list or dict, then `self.items.append(x)` changes the one shared object. Every other instance sees the change, even though it never added anything. `study/03_data_model.py` shows this with `BadBasket`.

The fix is to create mutable state per instance:
- in `__init__`, as `self.items = []`;
- in a dataclass, with `field(default_factory=list)`. That is what `CleaningReport` does, and `tests/test_models.py` checks that two reports do not share a dict.

Class attributes are fine for shared values that cannot be changed, like `RESOLVED_STATUSES` (a `frozenset`) or each metric's `name` (a `str`).

## 3. What does encapsulation mean in Python?

Encapsulation means an object controls its own data, so it can keep that data valid. Other code uses the object's methods and does not reach into its internals. Python does not enforce private attributes. It relies on conventions (`_name` means internal) and on tools such as properties and frozen dataclasses.

What it achieves here:
- A `SupportTicket` is checked once in `__post_init__` and is frozen, so no code can set a rating to 9 afterwards.
- Callers of `TicketCleaner` only call `clean(raw)`. How it normalises or de-duplicates can change without breaking them.
- Rules live with the data they protect (`NumericRule.accepts()`) instead of being copied into every place that needs them.

## 4. How do you avoid god objects?

Give each class one reason to change. If describing a class needs "and" several times, as in "it reads *and* validates *and* cleans *and* saves", split it.

What I did:
- I listed every job the Day 1 `TicketDataProcessor` had (ten of them; see `study/04_messy_class_review.md`).
- I moved each group of jobs into its own small component: loader, validation, cleaner, converter, metrics, writers.
- I kept the class that wires them together (`TicketPipeline`) free of rules. It only calls the others.
- Warning signs I watched for: methods over about 30 lines, `if type == ...` branches (replaced with `NumericRule` objects and metric classes), and file I/O mixed with logic.

## 5. How do you test a class that depends on an external system?

Do not create the dependency inside the class; pass it in (dependency injection). Then a test can pass a fake that behaves the same way but needs no file, network or database.

- `TicketPipeline` takes any object with a `load()` method. `tests/test_pipeline.py` passes a `FakeLoader` that returns an in-memory DataFrame and counts how often it was called. No disk is involved.
- `TicketCleaner` takes a DataFrame rather than a path, so every cleaning test builds its data in memory.
- The real file code (`CsvTicketLoader`, the writers) gets its own focused tests using pytest's `tmp_path`. One end-to-end test checks that all the parts work together for real.
