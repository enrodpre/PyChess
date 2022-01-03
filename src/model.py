from __future__ import annotations

import pprint
from collections import UserDict, deque
from itertools import groupby
from typing import Callable, Iterator

from board import Board


def check_unitvector(i: int) -> bool:
    return -1 <= i <= 1


class Point:
    x: int  # column
    y: int  # row

    def __iter__(self):
        yield self.x
        yield self.y

    def __eq__(self, other):
        (x1, y1), (x2, y2) = self, other
        return x1 == x2 and y1 == y2

    def __str__(self):
        return f'{self.__class__.__name__}(x={self.x},y={self.y})'

    def __repr__(self):
        return self.__str__()

    def __iadd__(self, other):
        a, b = other
        self.x += a
        self.y += b
        return self

    def __mul__(self, other: int):
        (x, y) = self
        return x * other, y * other

    def __div__(self, other: int):
        (x, y) = self
        return x // other, y // other


class Vector(Point):
    def __init__(self, x: int, y: int, direction: int = 1):
        self.x = x * direction
        self.y = y * direction

    __iter__ = Point.__iter__
    __iadd__ = Point.__iadd__

    def __add__(self, other):
        (a, b), (x, y) = self, other
        return Vector(a + x, b + y)

    def __mul__(self, other):
        (a, b), (x, y) = self, other
        return Vector(a * x, b * y)


TOP_DIRECTION = Vector(0, 1)
RIGHT_TOP_DIRECTION = Vector(1, 1)
RIGHT_DIRECTION = Vector(1, 0)
RIGHT_BOTTOM_DIRECTION = Vector(1, -1)
BOTTOM_DIRECTION = Vector(0, -1)
LEFT_BOTTOM_DIRECTION = Vector(-1, -1)
LEFT_DIRECTION = Vector(-1, 0)
LEFT_TOP_DIRECTION = Vector(1, -1)


class Slot(Point):
    def __init__(self, x: int, y: int):
        self.x = x
        self.y = y

    __iter__ = Point.__iter__
    __iadd__ = Point.__iadd__

    def __add__(self, other):
        (a, b), (x, y) = self, other
        return Slot(a + x, b + y)

    def __mul__(self, other):
        (a, b) = self
        if isinstance(other, int):
            return Slot(a * other, b * other)

        x, y = other
        return Slot(a * x, b * y)

    def __hash__(self):
        return hash((self.x, self.y))

    def flat(self) -> int:
        return self.y * 8 + self.x

    @classmethod
    def fromflat(cls, flat: int):
        return cls(flat % 8, flat // 8)

    @classmethod
    def translate(cls, x: int, y: int = 0):
        return cls(x, 7 - y)

    def reverse(self):
        self.y = 7 - self.y
        return self


SideEffect = Callable[[Board, Slot, Slot], None]


class Move:
    start: Slot
    end: Slot
    side_effects: deque[SideEffect]

    def __init__(self, start: Slot, end: Slot):
        self.start = start
        self.end = end
        self.side_effects = deque()

    def __iter__(self):
        yield self.start
        yield self.end
        yield self.side_effects

    def __str__(self):
        return f'Move(end={self.end})'

    def __repr__(self):
        return self.__str__()

    def add_side_effect(self, side_effect: SideEffect):
        self.side_effects.append(side_effect)
        return self

    def translate(self):
        self.start.reverse()
        self.end.reverse()
        return self


def groupby_dict(data: Iterator, key: str) -> dict:
    return {key: list(d) for key, d in groupby(data, key=lambda move: getattr(move, key))}


class Moves(UserDict[Slot, list[Move]]):
    def __init__(self, moves: Iterator[Move]):
        super().__init__()
        self.add_moves(moves)
        # self.debug()

    def add_moves(self, moves: Iterator[Move]) -> None:
        self.update(groupby_dict(moves, 'start'))

    def get_move(self, start: Slot, end: Slot) -> Move:
        moves = self.get(start)
        if moves is not None:
            for move in moves:
                if move.end == end:
                    return move
        raise ValueError

    def from_start(self, start: Slot) -> Iterator[Slot]:
        selected_moves = self.get(start)
        if selected_moves is not None:
            yield from (move.end for move in selected_moves)

    def debug(self):
        pprint.pp(self)
