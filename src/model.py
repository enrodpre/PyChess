from __future__ import annotations

import copy
import pprint
from collections import UserDict, deque
from enum import Flag, auto, Enum
from itertools import groupby, chain
from typing import Callable, Iterator, Optional, Iterable, Any

from more_itertools import partition, divide

from superclasses import ColorFlag
from util import from_int_to_san, from_san_to_int

COLOR_REPRESENTATION = ('upper', 'lower')
PIECETYPE_REPRESENTATION = ('P', 'N', 'B', 'R', 'Q', 'K')


class WrongFenError(Exception):
    pass


class InvalidStateError(Exception):
    pass


class Color(ColorFlag):
    WHITE = True
    BLACK = False

    def get_representation(self) -> str:
        return COLOR_REPRESENTATION[self.value]


class PieceType(Enum):
    @classmethod
    def from_representation(cls, representation: str):
        return cls(PIECETYPE_REPRESENTATION.index(representation.upper()))

    def get_representation(self) -> str:
        return PIECETYPE_REPRESENTATION[self.value]

    def __str__(self):
        return self.name

    def __hash__(self):
        return int.__hash__(self.value)

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

def get_piece_representation(color: Color, t: PieceType):
    return t.get_representation().upper() if color is color.WHITE else t.get_representation().lower()


class Piece:
    color: Color
    type: PieceType
    representation: str

    def __init__(self, color: Color, t: PieceType):
        self.color = color
        self.type = t
        self.representation = get_piece_representation(color, t)

    def __hash__(self):
        return hash((self.color, self.type))

    def __str__(self):
        return f'{self.color}_{self.type}'

    def __eq__(self, other):
        return type(self) is type(other) and self.color is other.color and self.type is other.type

    __repr__ = __str__

    @classmethod
    def fromstr(cls, piece: str):
        if piece is None:
            return None
        p = Piece(Color(int(piece.isupper())), PieceType.from_representation(piece))
        p.representation = piece
        return p

    def tostr(self) -> str:
        return self.representation

    def __iter__(self):
        yield self.color
        yield self.type

    def is_king(self):
        return self.type == PieceType.KING

    def direction(self) -> int:
        return self.color.direction()


def pieces_const() -> tuple[Piece, ...]:
    color_range, type_range = (Color.WHITE, Color.BLACK), range(6)
    return tuple(Piece(Color(color), PieceType(piece_type)) for piece_type in type_range for color in color_range)


WHITE_PAWN, BLACK_PAWN, WHITE_KNIGHT, BLACK_KNIGHT, WHITE_BISHOP, BLACK_BISHOP, WHITE_ROOK, BLACK_ROOK, WHITE_QUEEN, BLACK_QUEEN, WHITE_KING, BLACK_KING = pieces_const()


class Point:
    x: int  # column
    y: int  # row

    def __init__(self, x: int, y: int):
        self.x = x
        self.y = y

    def __iter__(self):
        yield self.x
        yield self.y

    def __eq__(self, other):
        if type(self) is type(other) or (issubclass(type(other), tuple) and len(other) == 2):
            (x1, y1), (x2, y2) = self, other
            return x1 == x2 and y1 == y2
        return False

    def __abs__(self):
        self.x = abs(self.x)
        self.y = abs(self.y)
        return self

    def __len__(self):
        return 2

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

    def __isub__(self, other):
        if not (type(self) is type(self) or issubclass(type(other), Iterable) or len(other) == 2):
            raise TypeError
        a, b = other
        self.x -= a
        self.y -= b
        return self

    def __sub__(self, other):
        if not (type(self) is type(self) or issubclass(type(other), Iterable) or len(other) == 2):
            raise TypeError
        (a, b), (c, d) = self, other
        return Point(a + c, b + d)


class Vector(Point):
    def __init__(self, x: int, y: int, direction: int = 1):
        Point.__init__(self, x * direction, y * direction)

    __iter__ = Point.__iter__
    __iadd__ = Point.__iadd__

    def __add__(self, other):
        (a, b), (x, y) = self, other
        return Vector(a + x, b + y)

    def __mul__(self, other):
        (a, b) = self
        if isinstance(other, int):
            return Vector(a * other, b * other)

        (x, y) = other
        return Vector(a * x, b * y)

    def __floordiv__(self, other):
        (x1, y1) = self
        if issubclass(type(other), Point) or (issubclass(type(other), tuple) and len(other) == 2):
            (x2, y2) = other
            return Vector(x1 // x2, y1 // y2)
        elif isinstance(other, int):
            return Vector(x1 // other, y1 // other)
        raise TypeError

    @classmethod
    def create(cls, x: int, y: int, direction: int = 1):
        return cls(x, y, direction)


Vector.ZERO = Vector.create(0, 0)

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
        Point.__init__(self, x, y)

    def __eq__(self, other):
        return Point.__eq__(self, other)

    def __add__(self, other) -> Slot:
        (a, b), (x, y) = self, other
        return Slot(a + x, b + y)

    def __mul__(self, other):
        (a, b) = self
        if isinstance(other, int):
            return Slot(a * other, b * other)

        x, y = other
        return Slot(a * x, b * y)

    def __sub__(self, other) -> Vector:
        (a, b), (x, y) = self, other
        return Vector(a - x, b - y)

    def __hash__(self):
        return hash((self.x, self.y))

    def flat(self) -> int:
        return self.y * 8 + self.x

    @classmethod
    def fromflat(cls, flat: int):
        return cls(flat % 8, flat // 8)

    @classmethod
    def from_point(cls, point: Point, divisor: int):
        x, y = point
        return cls(x // divisor, y // divisor)

    def reverse(self):
        self.y = 7 - self.y
        return self


PAWN_ATTACK_MOVEMENTS = (LEFT_TOP_DIRECTION, RIGHT_TOP_DIRECTION)
KNIGHT_MOVEMENTS = (
    Vector(1, 2), Vector(-1, 2), Vector(1, -2), Vector(-1, -2), Vector(2, 1), Vector(-2, 1), Vector(2, -1),
    Vector(-2, -1))
BISHOP_MOVEMENTS = (LEFT_TOP_DIRECTION, LEFT_BOTTOM_DIRECTION, RIGHT_BOTTOM_DIRECTION, RIGHT_TOP_DIRECTION)
ROOK_MOVEMENTS = (TOP_DIRECTION, RIGHT_DIRECTION, BOTTOM_DIRECTION, LEFT_DIRECTION)
GODLIKE_MOVEMENTS = BISHOP_MOVEMENTS + ROOK_MOVEMENTS

SideEffectType = Callable[[Any, Any], None]


class Move:
    piece: Piece
    start: Slot
    end: Slot
    side_effects: deque[SideEffectType]

    def __init__(self, piece: Piece, start: Slot, end: Slot):
        self.piece = piece
        self.start = copy.copy(start)
        self.end = copy.copy(end)
        self.side_effects = deque()

    def __iter__(self):
        yield self.start
        yield self.end
        yield self.side_effects

    def __str__(self):
        return f'Move(piece={self.piece}, start={self.start}, end={self.end})'

    def __repr__(self):
        return self.__str__()

    def add_side_effect(self, side_effect: SideEffectType):
        self.side_effects.append(side_effect)
        return self

    def as_values(self) -> tuple[int, int]:
        return self.start.flat(), self.end.flat()

    @classmethod
    def from_step(cls, piece: Piece, start: Slot, step: Vector):
        return cls(piece, start, start + step)


class Moves(UserDict[Slot, list[Move]]):
    def __init__(self, moves: Iterable[Move]):
        super().__init__()
        self.add_moves(moves)
        # self.debug()

    def add_moves(self, moves: Iterable[Move]) -> None:
        def groupby_dict(data: Iterable, key: str) -> dict:
            return {key: list(d) for key, d in groupby(data, key=lambda move: getattr(move, key))}

        self.update(groupby_dict(moves, 'start'))

    def search_move(self, start: Slot, end: Slot) -> Optional[Move]:
        moves = self.get(start)
        if moves is not None:
            for move in moves:
                if move.end == end:
                    return move
        return None

    def from_start(self, start: Slot) -> list[Slot]:
        moves = self.get(start)
        return [end for _, end, _ in moves] if moves is not None else []

    def debug(self):
        pprint.pp(self)

    def _end_iterator(self) -> Iterator[Slot]:
        return (end for _, end, _ in chain.from_iterable(self.values()))

    def search_end(self, target: Slot) -> bool:
        return next((a for a in self._end_iterator() if a == target), False) is not None

    def get_ends(self) -> list[Slot]:
        return list(self._end_iterator())

    def isempty(self) -> bool:
        return len(self) == 0


Square = Optional[Piece]


class Board(list[Square]):
    def __str__(self):
        row_count = 7
        res = '\n' + ' ' * 2 + '-' * 17 + '\n'
        for row in reversed(divide(8, self)):
            res += str(row_count) + ' |' + ' '.join(
                [c.representation if c is not None else '-' for c in row]) + '|' + '\n'
            row_count -= 1
        res += ' ' * 2 + '-' * 17 + '\n'
        res += ' ' * 3 + ' '.join(map(str, range(0, 8, 1)))
        return res + '\n'

    __repr__ = __str__

    def move(self, start: int, end: int):
        self[end] = self[start]
        self[start] = None

    def set(self, square: int, piece: Optional[Piece]):
        self[square] = piece


LocalizedPiece = tuple[int | Slot, Piece]
ColorPieceSet = list[LocalizedPiece]
PieceSet = tuple[ColorPieceSet, ColorPieceSet]

WHITE_QUEEN_ROOK_INITIAL_STATE = Slot(0, 0)
WHITE_KING_ROOK_INITIAL_STATE = Slot(7, 0)
BLACK_QUEEN_ROOK_INITIAL_STATE = Slot(0, 7)
BLACK_KING_ROOK_INITIAL_STATE = Slot(7, 7)


# --------------
# ENUMS
# --------------


class GameStateFlag(Flag):
    NORMAL = auto()
    CHECK = auto()
    DOUBLE_CHECK = auto()
    KINGSIDE_CASTLE = auto()
    QUEENSIDE_CASTLE = auto()
    EN_PASSANT = auto()
    STALEMATE = auto()
    CHECKMATE = auto()
    DRAW = auto()


# --------------
# ENUMS
# --------------

class GameState:
    _board: Board
    state_flag: GameStateFlag
    next_to_move: Color
    en_passant_target: Optional[Slot]
    halfmove_clock: int
    fullmove_number: int
    white_king_can_castle: bool
    white_queen_can_castle: bool
    black_king_can_castle: bool
    black_queen_can_castle: bool

    def __init__(self, board: Board, st: GameStateFlag, ntm: Color, wk: bool, wq: bool, bk: bool, bq: bool,
                 ept: Optional[Slot], hc: int, fm: int):
        self._board = board
        self.state_flag = st
        self.next_to_move = ntm
        self.white_king_can_castle = wk
        self.white_queen_can_castle = wq
        self.black_king_can_castle = bk
        self.black_queen_can_castle = bq
        self.en_passant_target = ept
        self.halfmove_clock = hc
        self.fullmove_number = fm
        if ept is not None:
            self.raise_flag(GameStateFlag.EN_PASSANT)

    def __str__(self):
        res = ''
        for name, t in self.__annotations__.items():
            obj = getattr(self, name)
            res += f'\n{name}:\n\t{obj}'
        return res

    @property
    def board(self):
        return self._board

    def set_en_passant(self, target: Slot):
        self.raise_flag(GameStateFlag.EN_PASSANT)
        self.en_passant_target = target

    def raise_flag(self, flag: GameStateFlag):
        if flag is GameStateFlag.CHECK and GameStateFlag.CHECK in flag:
            flag = GameStateFlag.DOUBLE_CHECK
        self.state_flag |= flag

    def check_flag(self, flag: GameStateFlag) -> bool:
        return flag in self.state_flag

    def find_king(self, color: Color = None) -> Slot:
        if color is None:
            color = self.next_to_move
        p = WHITE_KING if color == Color.WHITE else BLACK_KING
        return Slot.fromflat(self.board.index(p))

    def get_pieces(self, localiced: bool = False) -> PieceSet:
        f: ColorPieceSet
        t: ColorPieceSet
        if localiced:
            pieces_source = tuple((Slot.fromflat(i), e) for i, e in enumerate(self.board) if e is not None)
            f, t = partition(lambda s: s[1].color == self.next_to_move, pieces_source)
        else:
            f, t = partition(lambda s: s.color == self.next_to_move, self.board)

        return list(f), list(t)

    def get_piece(self, slot: Slot) -> Square:
        return self.board[slot.flat()]

    def commit_move(self, start: Slot, end: Slot):
        self.halfmove_clock = self._change_halfmove_clock(start, end)
        self.move(start.flat(), end.flat())

        self.en_passant_target = None
        if not self.next_to_move:
            self.fullmove_number += 1

        self.state_flag = GameStateFlag.NORMAL
        self.next_to_move = ~self.next_to_move

    def _change_halfmove_clock(self, start: Slot, end: Slot):
        moving_piece = self.get_piece(start)
        if moving_piece is None:
            raise InvalidStateError
        if moving_piece.type is PieceType.PAWN or self.get_piece(end) is not None:
            return 0
        return self.halfmove_clock + 1

    def promote_pawn(self, slot: Slot, piece_to_promote: Piece):
        self._board.set(slot.flat(), piece_to_promote)

    def remove(self, slot: Slot):
        self._board.set(slot.flat(), None)

    def move(self, start: int | Slot, end: int | Slot):
        if isinstance(start, Slot):
            start = start.flat()
        if isinstance(end, Slot):
            end = end.flat()
        self._board.move(start, end)

    def castle_available_info(self) -> Iterator[tuple[Slot, Slot, Vector]]:
        if self.next_to_move and self.white_king_can_castle:
            yield Slot(4, 0), Slot(7, 0), Vector(1, 0)
        if self.next_to_move and self.white_queen_can_castle:
            yield Slot(4, 0), Slot(0, 0), Vector(-1, 0)
        if not self.next_to_move and self.black_king_can_castle:
            yield Slot(4, 7), Slot(0, 7), Vector(-1, 0)
        if not self.next_to_move and self.black_queen_can_castle:
            yield Slot(4, 7), Slot(7, 7), Vector(1, 0)

    @classmethod
    def from_fen(cls, fen_str: str):
        str_squares, next_move, castles, en_passant, halfmove, fullmove = fen_str.split(' ')
        square_list: list[Optional[str]] = []
        for row in reversed(str_squares.split('/')):
            for char in row:
                if char.isnumeric():
                    square_list += [None] * int(char)
                    continue

                square_list.append(char)

        squares = Board(map(lambda c: Piece.fromstr(c) if c is not None else None, square_list))
        if len(squares) != 64:
            raise WrongFenError(fen_str)
        next_to_move = Color(next_move == 'w')
        white_king_can_castle = 'K' in castles
        white_queen_can_castle = 'Q' in castles
        black_king_can_castle = 'k' in castles
        black_queen_can_castle = 'q' in castles
        en_passant_target = None if en_passant == '-' else Slot.fromflat(from_san_to_int(en_passant))
        halfmove_clock = int(halfmove)
        fullmove_number = int(fullmove)

        return GameState(squares, GameStateFlag.NORMAL, next_to_move, white_king_can_castle, white_queen_can_castle,
                         black_king_can_castle,
                         black_queen_can_castle, en_passant_target, halfmove_clock, fullmove_number)

    def to_fen(self) -> str:
        squares = self.board
        rows = []
        for file in divide(8, squares):
            blank_counter = 0
            row = ''
            for piece in file:
                if piece is None:
                    blank_counter += 1
                else:
                    if blank_counter > 0:
                        row += str(blank_counter)
                        blank_counter = 0
                    row += piece.tostr()
            if blank_counter > 0:
                row += str(blank_counter)
            rows.append(row)

        fen_result = '/'.join(reversed(rows))
        fen_result += ' '

        fen_result += 'w' if self.next_to_move else 'b'
        fen_result += ' '

        castles = ''
        castles += 'K' if self.white_king_can_castle else ''
        castles += 'Q' if self.white_queen_can_castle else ''
        castles += 'k' if self.black_king_can_castle else ''
        castles += 'q' if self.black_queen_can_castle else ''

        fen_result += castles if castles != '' else '-'
        fen_result += ' '

        fen_result += from_int_to_san(
            self.en_passant_target.flat()) if self.en_passant_target is not None else '-'
        fen_result += ' '

        fen_result += str(self.halfmove_clock) + ' ' + str(self.fullmove_number)
        return fen_result
