"""Study 1: classes and the object model. Run: python study/01_object_model.py

Output required: implement small classes and explain instance state.
"""


class Counter:
    # Class attribute: one value stored on the class, shared by every instance.
    created = 0

    def __init__(self, label: str) -> None:
        # Instance attributes: stored in this object's own __dict__.
        self.label = label
        self.count = 0
        Counter.created += 1  # update the shared value on the class, not on self

    def increment(self, step: int = 1) -> int:
        # `self` is just the instance the method was called on:
        # a.increment() is the same call as Counter.increment(a).
        self.count += step
        return self.count


a = Counter("billing")
b = Counter("technical")
a.increment()
a.increment()
b.increment(5)

print("a.__dict__ =", a.__dict__)  # {'label': 'billing', 'count': 2}
print("b.__dict__ =", b.__dict__)  # each object has its own state
print("Counter.created =", Counter.created)  # 2, shared
assert Counter.increment(a) == a.count == 3  # explicit self

# Attribute lookup order: instance __dict__ first, then the class.
print("a.created via class =", a.created)
a.created = 99  # this does NOT change the class; it adds an instance attribute that hides it
print("a.created =", a.created, "| b.created =", b.created, "| Counter.created =", Counter.created)
assert b.created == Counter.created == 2


class Account:
    """Objects bundle state with the rules that keep that state valid."""

    def __init__(self, owner: str, balance: float = 0.0) -> None:
        if balance < 0:
            raise ValueError("balance cannot start negative")
        self.owner = owner
        self._balance = balance  # leading underscore: internal, change it through methods

    def withdraw(self, amount: float) -> None:
        if amount > self._balance:
            raise ValueError("insufficient funds")
        self._balance -= amount

    @property
    def balance(self) -> float:  # read-only view of internal state
        return self._balance


acct = Account("kunal", 10)
acct.withdraw(4)
print("balance =", acct.balance)
try:
    acct.withdraw(100)
except ValueError as error:
    print("rule enforced:", error)

# Explanation (instance state):
# - Each instance carries its own data in __dict__; methods read and change it through self.
# - Class attributes are shared. Reading one through an instance works, but assigning
#   through an instance creates a new instance attribute instead of changing the shared one.
# - The object guards its own state: Account never lets its balance go negative,
#   because the only way to change _balance is through withdraw(), which checks the rule.
