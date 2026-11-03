"""Study 3: the Python data model. Make objects readable and predictable.

Run: python study/03_data_model.py
"""

from dataclasses import FrozenInstanceError, dataclass, field


# --- The mutable class attribute trap ---------------------------------------------
class BadBasket:
    items = []  # ONE list, created once, shared by every BadBasket

    def add(self, item):
        self.items.append(item)  # mutates the shared list; does not create a new one


first, second = BadBasket(), BadBasket()
first.add("apple")
print("BadBasket second.items =", second.items)  # ['apple'], a bug: second never added anything
assert second.items == ["apple"]


class GoodBasket:
    def __init__(self):
        self.items = []  # a new list for every instance


g1, g2 = GoodBasket(), GoodBasket()
g1.items.append("apple")
assert g2.items == []


@dataclass
class DataclassBasket:
    # `items: list = []` is rejected by dataclasses for exactly this reason.
    items: list[str] = field(default_factory=list)


assert DataclassBasket().items is not DataclassBasket().items


# --- Properties: validated, computed attributes -------------------------------------
class Rating:
    def __init__(self, value: float):
        self.value = value  # goes through the setter below, so it is validated too

    @property
    def value(self) -> float:
        return self._value

    @value.setter
    def value(self, new: float) -> None:
        if not 1 <= new <= 5:
            raise ValueError(f"rating must be 1-5, got {new}")
        self._value = new

    @property
    def stars(self) -> str:  # computed, never stored, never out of date
        return "*" * round(self._value)


r = Rating(4)
print("stars:", r.stars)
try:
    r.value = 9
except ValueError as error:
    print("property blocked:", error)


# --- __repr__ vs __str__ -----------------------------------------------------------
class Ticket:
    def __init__(self, ticket_id: str, status: str):
        self.ticket_id, self.status = ticket_id, status

    def __repr__(self) -> str:  # for developers: unambiguous, ideally valid Python
        return f"Ticket(ticket_id={self.ticket_id!r}, status={self.status!r})"

    def __str__(self) -> str:  # for people and logs: short and readable
        return f"{self.ticket_id} ({self.status})"


t = Ticket("T-1", "open")
print("repr:", repr(t))
print("str: ", str(t))
print("in a list, Python uses repr:", [t])


# --- Dataclasses: generated __init__, __repr__, __eq__; frozen for safety -----------
@dataclass(frozen=True)
class Point:
    x: float
    y: float

    def __post_init__(self):
        if self.x < 0 or self.y < 0:
            raise ValueError("coordinates must be non-negative")


p = Point(1, 2)
print(p, "== Point(1, 2)?", p == Point(1, 2))  # value equality, generated
print("hashable, usable in a set:", {p, Point(1, 2)})
try:
    p.x = 5
except FrozenInstanceError:
    print("frozen: cannot change x after creation")

# Summary:
# - Class attributes are for shared, *immutable* data. Mutable state goes on the instance
#   (in __init__, or with field(default_factory=...) in a dataclass).
# - Properties keep the attribute syntax while adding validation or computed values.
# - __repr__ is for debugging, __str__ for display. Dataclasses generate __repr__ and __eq__.
# - frozen=True + __post_init__ = an object that is valid when created and stays valid.
#   The project's SupportTicket uses exactly this (src/ticket_pipeline/models.py).
