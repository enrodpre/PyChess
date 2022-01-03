from dataclasses import dataclass
from itertools import product

from aenum import Enum

COLOR_REPRESENTATION = ('upper', 'lower')
PIECETYPE_REPRESENTATION = ('P', 'N', 'B', 'R', 'Q', 'K')


class Color(Enum):
    def get_representation(self) -> str:
        return COLOR_REPRESENTATION[self.value]

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
