from dataclasses import dataclass
from itertools import product, tee
from typing import Callable, NamedTuple, Optional, Iterator

from aenum import Enum

COLOR_REPRESENTATION = ('upper', 'lower')
PIECETYPE_REPRESENTATION = ('P', 'N', 'B', 'R', 'Q', 'K')


class Color(Enum):
    def get_representation(self) -> str:
        return COLOR_REPRESENTATION[self.value]

    def get_direction(self) -> int:
        return 1 if self.value == 0 else -1

    def __str__(self):
        return self.name

    WHITE = 0
    BLACK = 1


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


(COLOR_NAMES, COLOR_VALUES) = zip(*map(lambda col: (col.name, col.value), Color))
(PIECETYPE_NAMES, PIECETYPE_VALUES) = zip(*map(lambda t: (t.name, t.value), PieceType))


def iswhite(piece: str) -> bool:
    return piece.isupper()


@dataclass
class Piece:
    color: Color
    type: PieceType
    representation: str

    @classmethod
    def fromstr(cls, piece: str):
        if piece is None:
            return None
        _color = Color(int(not iswhite(piece)))
        _type = PieceType.from_representation(piece)
        return Piece(_color, _type, piece)

    def tostr(self) -> str:
        return self.representation


def _generate_pieces() -> list[Piece]:
    whites = ('P', 'N', 'B', 'R', 'Q', 'K')
    blacks = tuple(w.lower() for w in whites)
    return list(Piece(c, t, r) for (c, t), r in zip(product(COLOR_VALUES, PIECETYPE_VALUES), whites + blacks))


PIECES_LIST = _generate_pieces()


class Point:
    x: int  # row
    y: int  # column

    def __init__(self, x: int, y: int):
        self.x = x
        self.y = 7 - y

    def __str__(self):
        return f'Point(x={self.x},y={self.y})'

    def flat_integer(self) -> int:
        return self.x * 8 + self.y

    @classmethod
    def from_divmod(cls, flat: int):
        return Point(*divmod(flat, 8))

    @classmethod
    def from_tuple(cls, t: tuple[int, int]):
        return Point(x=t[0], y=t[1])

    def __add__(self, other):
        if isinstance(other, tuple):
            if len(other) != 2:
                return
            other = Point.from_tuple(other)
        return Point(*map(sum, zip(self, other)))

    def __rmul__(self, other: int):
        return Point(self.x * other, self.y * other)

    def __rdiv__(self, other: int):
        return Point(self.x // other, self.y // other)

    def __floordiv__(self, other: int):
        return self.__rdiv__(other)

    def __iter__(self):
        yield self.x
        yield self.y

    def aim(self, color: Color):
        return Point(*map(lambda x: x * Color(color).get_direction(), iter(self)))


SpecialReturnType = Point | tuple[Point, ...]
Square = Optional[Piece]
RegularType = Optional[tuple[Point, ...]]
SpecialType = Optional[tuple[Callable[..., SpecialReturnType], ...]]


class MovementType(NamedTuple):
    regular: RegularType  # generally can be played always
    repeteable: bool
    special: SpecialType  # depends


def _move_two_forward(posicion: Point, color: int) -> SpecialReturnType:
    if posicion.x == 1 and color == Color.WHITE:
        return posicion + (2, 0)
    if posicion.x == 6 and color == Color.BLACK:
        return posicion + (-2, 0)
    return tuple()


def _pawn_aims(posicion: Point, color: int) -> Iterator[tuple[int, int]]:
    d = Color(color).get_direction()
    m = [(d * a, d * b) for (a, b) in [(1, 1), (1, -1)]]
    return ((a1 + b1, a2 + b2) for (a1, a2), (b1, b2) in
            zip(m, tee(posicion, 2)))


def _pawn_forward(posicion: Point, color: int) -> SpecialReturnType:
    return posicion + Color(color).get_direction() * (1, 0)


def _pawn_takes(posicion: int, color: int, squares: tuple[Square, ...]) -> SpecialReturnType:
    aimed = _pawn_aims(Point.from_divmod(posicion), color)
    res = tuple()
    for (a, b) in aimed:
        index = a * 8 + b
        if 0 <= index <= 63:
            square = squares[index]
            if square is not None and square.color != color:
                res += (Point.from_divmod(index),)
    return res


def _en_passant_take(posicion: int, color: int, en_passant_target: int) -> SpecialReturnType:
    direction = Color(color).get_direction()
    possibles = [(x * direction + posicion, y * direction + posicion) for (x, y) in ((1, 1), (1, -1))]
    return tuple(Point.from_divmod(p) for p in possibles if p == en_passant_target)


def _bishop_movement() -> tuple[Point, ...]:
    return tuple(Point(a, b) for a, b in product([1], [-1]))


def _rook_movement() -> tuple[Point, ...]:
    return tuple(Point(a, b) for (a, b) in ((1, 0), (-1, 0), (0, 1), (0, -1)))


def _castle(color: int, white_king_can_castle: bool, white_queen_can_castle: bool, black_king_can_castle: bool,
            black_queen_can_castle: bool) -> Iterator[tuple[int, int]]:
    king_direction, queen_direction = (2, 0), (-2, 0)
    if color == Color.WHITE:
        if white_king_can_castle:
            yield king_direction
        if white_queen_can_castle:
            yield queen_direction
    else:
        if black_king_can_castle:
            yield king_direction
        if black_queen_can_castle:
            yield queen_direction


def _castle_movement(posicion: Point, color: int, white_king_can_castle: bool, white_queen_can_castle: bool,
                     black_king_can_castle: bool, black_queen_can_castle: bool) -> SpecialReturnType:
    return tuple(posicion + c for c in
                 _castle(int, white_king_can_castle, white_queen_can_castle, black_king_can_castle,
                         black_queen_can_castle))


MOVEMENT_TYPES: dict[int, MovementType]
MOVEMENT_TYPES = {PieceType.PAWN:
                      MovementType(None,
                                   False,
                                   (_pawn_forward,
                                    _move_two_forward,
                                    _pawn_takes,
                                    _en_passant_take
                                    )),
                  PieceType.KNIGHT:
                      MovementType(tuple(Point(*p) for p in
                                         (list(product([-1, +1], [-2, +2])) + list(product([-2, +2], [-1, +1])))),
                                   False,
                                   None),
                  PieceType.BISHOP:
                      MovementType(_bishop_movement(),
                                   True,
                                   None),
                  PieceType.ROOK:
                      MovementType(
                          _rook_movement(),
                          True,
                          None),
                  PieceType.QUEEN:
                      MovementType(
                          _rook_movement() + _bishop_movement(),
                          True,
                          None),
                  PieceType.KING:
                      MovementType(_rook_movement() + _bishop_movement(),
                                   False,
                                   (_castle_movement,)
                                   )
                  }

PIECES_DATA: dict[str, tuple[Piece, MovementType]]
PIECES_DATA = dict(((p.representation, (p, MOVEMENT_TYPES[PieceType(p.type)])) for p in
                    PIECES_LIST))
