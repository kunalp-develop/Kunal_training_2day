"""Study 2: OOP design. Compare two designs and justify one.

Run: python study/02_composition_vs_inheritance.py
"""

from abc import ABC, abstractmethod

TICKETS = [{"id": "T-1", "status": "Open "}, {"id": "T-2", "status": "closed"}]


# --- Design 1: inheritance chain -------------------------------------------------
class BaseProcessor:
    def load(self):
        return [dict(t) for t in TICKETS]  # imagine: reads a real file


class CleaningProcessor(BaseProcessor):
    def clean(self):
        rows = self.load()
        for row in rows:
            row["status"] = row["status"].strip().lower()
        return rows


class AnalyticsProcessor(CleaningProcessor):
    def unresolved(self):
        return sum(row["status"] != "closed" for row in self.clean())


# Problems:
# - An AnalyticsProcessor is not really "a kind of" CleaningProcessor.
# - To test unresolved() with different data you must subclass or patch load().
# - A change to CleaningProcessor.clean silently changes AnalyticsProcessor too.
print("inheritance:", AnalyticsProcessor().unresolved())


# --- Design 2: composition through small interfaces ------------------------------
class Source(ABC):
    """Abstract interface: anything with load() can be a source."""

    @abstractmethod
    def load(self) -> list[dict]: ...


class ListSource(Source):
    def __init__(self, rows):
        self.rows = rows

    def load(self):
        return [dict(r) for r in self.rows]


class StatusCleaner:
    def clean(self, rows):
        return [{**row, "status": row["status"].strip().lower()} for row in rows]


class UnresolvedCount:
    def compute(self, rows):
        return sum(row["status"] != "closed" for row in rows)


class Pipeline:
    def __init__(self, source: Source, cleaner: StatusCleaner, metric: UnresolvedCount):
        self.source, self.cleaner, self.metric = source, cleaner, metric  # has-a, not is-a

    def run(self):
        return self.metric.compute(self.cleaner.clean(self.source.load()))


print("composition:", Pipeline(ListSource(TICKETS), StatusCleaner(), UnresolvedCount()).run())

# Testing with different data is now one line: pass a different source.
assert Pipeline(ListSource([{"id": "x", "status": "OPEN"}]), StatusCleaner(), UnresolvedCount()).run() == 1
# Each part can also be tested alone, without the others.
assert UnresolvedCount().compute([{"status": "closed"}]) == 0


# --- Polymorphism: different classes, same method name, used the same way --------
class ClosedCount:
    def compute(self, rows):
        return sum(row["status"] == "closed" for row in rows)


cleaned = StatusCleaner().clean(TICKETS)
for metric in (UnresolvedCount(), ClosedCount()):
    print(type(metric).__name__, "=", metric.compute(cleaned))

try:
    Source()  # abstract classes cannot be instantiated
except TypeError as error:
    print("abstract interface enforced:", error)

# Justification: Design 2 is chosen for the real project (TicketPipeline).
# - Encapsulation: each class hides how it does its one job.
# - Composition: behaviour is changed by passing different parts, not by subclassing.
# - Polymorphism: the pipeline calls .compute() without knowing which metric it has.
# - Inheritance is kept for true "is-a" relationships, e.g. InvalidCSVError is a
#   TicketPipelineError (see src/ticket_pipeline/errors.py).
