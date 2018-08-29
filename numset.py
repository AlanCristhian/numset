from __future__ import annotations

from dataclasses import dataclass, field
from typing import (Optional, List, Tuple, Union, Iterable, Generator, Any,
                    Iterator)
import numbers

import name  # type: ignore


class Statement(name.AutoName):  # type: ignore
    def __init__(self, feature: Optional[bool] = None) -> None:
        super().__init__(0)
        self.feature = feature

    def __rshift__(self, other: Statement) -> Statement:
        if self.feature == other.feature:
            return Statement(self.feature)
        else:
            return Statement(not self.feature)

    def __repr__(self) -> str:
        return f"{super().__assigned_name__} is {self.feature}"


_AffirmationType = List[Tuple[Statement, Statement, bool]]


@dataclass(repr=False)
class Given:
    _given: Statement
    _statement: Statement = field(init=False)
    _must_be: bool = field(init=False)
    affirmations: _AffirmationType = field(default_factory=list, init=False)

    def statement(self, statement: Statement) -> Given:
        self._statement = statement
        return self

    def must_be(self, feature: bool) -> Given:
        self._must_be = feature
        self.affirmations.append((self._given, self._statement, self._must_be))
        return self

    def and_given(self, statement: Statement) -> Given:
        self._given = statement
        return self

    @property
    def end(self) -> Statement:
        (p0, t0, b0), (p1, t1, b1) = self.affirmations
        if p0 != p1 and t0 == t1 and b0 != b1:
            return Paradox(self.affirmations)
        else:
            return Statement(True)


class Paradox(Statement):
    def __init__(self, affirmations: _AffirmationType) -> None:
        super().__init__()
        self.affirmations = affirmations


class Class:
    def __init__(self, *elements: Any,
                 belongs_to: Optional[List[Class]] = None) -> None:
        self.belongs_to = belongs_to
        self.elements = elements

    def __iter__(self) -> Iterator[Any]:
        return iter(self.elements)

    def __eq__(A, B: Any) -> bool:
        """[A = B] <=> [x in A <=> x in B]"""
        return all(x in B for x in A) and all(x in A for x in B)

    def is_subset(A, B: Class) -> bool:
        return all(x in B for x in A)

    def is_proper_subset(A, B: Class) -> bool:
        """A is subset of B and A != B"""
        return all(x in B for x in A) and A != B


def is_element(class_: Class) -> bool:
    return False if class_.belongs_to is None else True
