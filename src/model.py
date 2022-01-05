from __future__ import annotations

import copy
import pprint
from collections import UserDict, deque
from dataclasses import dataclass
from functools import cache
from itertools import groupby, chain
from typing import Callable, Iterator, Optional, Iterable

from aenum import Enum
from more_itertools import partition, divide

from util import _from_int_to_algebraic, _from_algebraic_to_int

COLOR_REPRESENTATION = ('upper', 'lower')
PIECETYPE_REPRESENTATION = ('P', 'N', 'B', 'R', 'Q', 'K')


class Color(Enum):
    def get_representation(self) -> str:
        return COLOR_REPRESENTATION[self.value]

    def __str__(self):
        return self.name

    WHITE = True
    BLACK = False


class PieceType(Enum):
    @classmethod
    def from_representation(cls, representation: str):
        return cls(PIECETYPE_REPRESENTATION.index(representation.upper()))

    def get_representation(self) -> str:
        return PIECETYPE_REPRESENTATION[self.value]

    def __str__(self):
        return self.name

    def __repr__(self):
        return self.__str__()

    PAWN = 0
    KNIGHT = 1
    BISHOP = 2
    ROOK = 3
    QUEEN = 4
    KING = 5


# (COLOR_NAMES, COLOR_VALUES) = zip(*map(lambda col: (col.name, col.value), Color))
# (PIECETYPE_NAMES, PIECETYPE_VALUES) = zip(*map(lambda t: (t.name, t.value), PieceType))


@dataclass
class Piece:
    color: Color
    type: PieceType
    representation: str

    @classmethod
    def fromstr(cls, piece: str):
        def iswhite(p: str) -> bool:
            return p.isupper()

        if piece is None:
            return None
        _color = Color(int(not iswhite(piece)))
        _type = PieceType.from_representation(piece)
        return Piece(_color, _type, piece)

    def tostr(self) -> str:
        return self.representation

    def __iter__(self):
        yield self.color
        yield self.type


"""def _generate_pieces() -> list[Piece]:
    whites = ('P', 'N', 'B', 'R', 'Q', 'K')
    blacks = tuple(w.lower() for w in whites)
    return list(Piece(c, t, r) for (c, t), r in zip(product(COLOR_VALUES, PIECETYPE_VALUES), whites + blacks))


PIECES_LIST = _generate_pieces()
"""


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
LEFT_TOP_DIRECTION = Vector(-1, 1)


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


class Move:
    start: Slot
    end: Slot
    side_effects: deque[Callable]

    def __init__(self, start: Slot, end: Slot):
        self.start = copy.copy(start)
        self.end = end
        self.side_effects = deque()

    def __iter__(self):
        yield self.start
        yield self.end
        yield self.side_effects

    def __str__(self):
        return f'Move(start={self.start}, end={self.end})'

    def __repr__(self):
        return self.__str__()

    def add_side_effect(self, side_effect: Callable):
        self.side_effects.append(side_effect)
        return self

    def translate(self):
        self.start.reverse()
        self.end.reverse()
        return self

    def as_values(self) -> tuple[int, int]:
        return self.start.flat(), self.end.flat()

    @classmethod
    def from_step(cls, start: Slot, step: Vector):
        return cls(start, start + step)


class Moves(UserDict[Slot, list[Move]]):
    def __init__(self, moves: Iterator[Move]):
        super().__init__()
        self.add_moves(moves)
        # self.debug()

    def add_moves(self, moves: Iterator[Move]) -> None:
        def groupby_dict(data: Iterator, key: str) -> dict:
            return {key: list(d) for key, d in groupby(data, key=lambda move: getattr(move, key))}

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

    def _end_iterator(self) -> Iterator[Slot]:
        return (end for _, end, _ in chain.from_iterable(self.values()))

    def search_end(self, target: Slot) -> bool:
        return next((a for a in self._end_iterator() if a == target), False) is not None

    def get_ends(self) -> list[Slot]:
        return list(self._end_iterator())


Square = Optional[Piece]


@cache
def translate(i: int):
    return Slot.translate(*divmod(i, 8)[::-1]).flat()


class Board(list[Square]):
    def __init__(self, seq: Iterable[Square]):
        list.__init__(self, seq)

    def filtered_translated_iterator(self) -> Iterator[tuple[int, Piece]]:
        return ((i, e) for i, e in self.translated_iterator() if e is not None)

    def translated_iterator(self) -> Iterator[tuple[int, Square]]:
        return iter(sorted(map(lambda x: (translate(x[0]), x[1]), enumerate(list.__iter__(self))), key=lambda x: x[0]))

    def __getitem__(self, i: int):
        return list.__getitem__(self, i)

    def __iter__(self):
        return list.__iter__(self)

    def __str__(self):
        row_count = 7
        res = ' ' * 3 + '-' * 17 + '\n'
        for row in divide(8, self):
            res += str(row_count) + ' |' + ' '.join(
                [c.representation if c is not None else '-' for c in row]) + '|' + '\n'
            row_count -= 1
        res += ' ' * 3 + '-' * 17 + '\n'
        res += ' ' * 3 + ' '.join(map(str, range(0, 8, 1)))
        return res

    __repr__ = __str__

    def move(self, start: int, end: int):
        self[end] = self[start]
        self[start] = None


ColorwisePieceSet = Iterator[tuple[int, Piece]]
PieceSet = tuple[ColorwisePieceSet, ColorwisePieceSet]


class StateFlag(Enum):
    NORMAL = 0
    CHECK = 1


@dataclass
class GameState:
    board: Board
    whites_to_move: bool
    white_king_can_castle: bool
    white_queen_can_castle: bool
    black_king_can_castle: bool
    black_queen_can_castle: bool
    en_passant_target: Optional[int]
    halfmove_clock: int
    fullmove_number: int
    state_flag: int

    def get_board_copy(self) -> Board:
        return copy.copy(self.board)

    def get_pieces(self) -> PieceSet:
        return partition(lambda s: s[1].color.value == self.whites_to_move,
                         ((i, e) for i, e in enumerate(self.board) if e is not None))

    def prepare_next_turn(self):
        self.fullmove_number += 1
        self.en_passant_target = None
        wtm = self.whites_to_move
        if not wtm:
            self.halfmove_clock += 1

        self.whites_to_move = not wtm

    def move(self, start: int, end: int):
        self.board.move(translate(start), translate(end))

    @classmethod
    def from_fen(cls, fen_str: str):
        str_squares, next_move, castles, en_passant, halfmove, fullmove = fen_str.split(' ')
        square_list: list[Optional[str]] = []
        for row in str_squares.split('/'):
            for char in row:
                if char.isnumeric():
                    square_list += [None] * int(char)
                    continue

                square_list.append(char)

        squares = Board(map(lambda c: Piece.fromstr(c) if c is not None else None, square_list))
        whites_to_move = next_move == 'w'
        white_king_can_castle = 'K' in castles
        white_queen_can_castle = 'Q' in castles
        black_king_can_castle = 'k' in castles
        black_queen_can_castle = 'q' in castles
        en_passant_target = None if en_passant == '-' else _from_algebraic_to_int(en_passant)
        halfmove_clock = int(halfmove)
        fullmove_number = int(fullmove)

        return GameState(squares, whites_to_move, white_king_can_castle, white_queen_can_castle, black_king_can_castle,
                         black_queen_can_castle, en_passant_target, halfmove_clock, fullmove_number, StateFlag.NORMAL)

    def to_fen(self) -> str:
        rows = []
        squares = self.board
        blank_counter = 1
        for i in range(8):
            row = ''
            for piece in divide(8, squares):
                if piece is None:
                    blank_counter += 1
                else:
                    if blank_counter > 1:
                        row += str(blank_counter)
                        blank_counter = 1
                    row += piece.tostr()
            if blank_counter > 1:
                row += str(blank_counter - 1)
                blank_counter = 1
            rows += [row]

        fen_result = '/'.join(rows)
        fen_result += ' '

        fen_result += 'w' if self.whites_to_move else 'b'
        fen_result += ' '

        castles = ''
        castles += 'K' if self.white_king_can_castle else ''
        castles += 'Q' if self.white_queen_can_castle else ''
        castles += 'k' if self.black_king_can_castle else ''
        castles += 'q' if self.black_queen_can_castle else ''

        fen_result += castles if castles != '' else '-'
        fen_result += ' '

        fen_result += _from_int_to_algebraic(
            self.en_passant_target) if self.en_passant_target is not None else '-'
        fen_result += ' '

        fen_result += str(self.halfmove_clock) + ' ' + str(self.fullmove_number)
        return fen_result
