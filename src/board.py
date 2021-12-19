from dataclasses import dataclass
from typing import Optional, Iterable, Iterator

from piece import Piece, Square
from util import _from_algebraic_to_int, _from_int_to_algebraic

STARTING_POSITION_FEN = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1'

Square = Optional[Piece]


class Squares(tuple[Square, ...]):
    def __new__(cls, squares: Iterable):
        obj = super(Squares, cls).__new__(cls, squares)
        if len(obj) != 64:
            raise ValueError('La cantidad de squares debe ser 64')

        return obj

    def skippingiter(self) -> Iterator[tuple[int, Piece]]:
        class SquaresIterator(Iterator):
            def __init__(self, data: Iterator[Square]):
                self.iter = data
                self.i = -1

            def __next__(self) -> tuple[int, Square]:
                while True:
                    self.i += 1
                    item = next(self.iter)
                    if item is not None:
                        return self.i, item

        return SquaresIterator(super().__iter__())

    def __setitem__(self, key, value):
        new_tuple = list(self)
        new_tuple[key:key + 1] = [value]
        return self.__new__(self.__class__, new_tuple)

    def __str__(self):
        return '(' + ','.join(str(p) for p in self) + ')'


@dataclass
class Board:
    squares: Squares
    whites_to_move: bool
    white_king_can_castle: bool
    white_queen_can_castle: bool
    black_king_can_castle: bool
    black_queen_can_castle: bool
    en_passant_target: Optional[int]
    halfmove_clock: int
    fullmove_number: int

    @classmethod
    def classic(cls):
        return cls.fromfen(STARTING_POSITION_FEN)

    @classmethod
    def fromfen(cls, fen_str: str):
        return _from_fen(fen_str)

    def tofen(self) -> str:
        return _to_fen(self)

    def stringify(self) -> tuple[Optional[str], ...]:
        return tuple(map(lambda sq: str(sq.representation) if sq is not None else None, self.squares))


def _from_fen(fen_str: str) -> Board:
    str_squares, next_move, castles, en_passant, halfmove, fullmove = fen_str.split(' ')
    square_list: list[Optional[str]] = []
    for i, row in enumerate(str_squares.split('/')):
        j = 0
        while j < 8:
            ch = row[j]
            if ch.isnumeric():
                number_of_blank_squares = int(ch)
                square_list += [None] * number_of_blank_squares
                j += number_of_blank_squares
                continue

            square_list.append(ch)
            j += 1

    squares = Squares(Piece.fromstr(c) for c in square_list)
    whites_to_move = next_move == 'w'
    white_king_can_castle = 'K' in castles
    white_queen_can_castle = 'Q' in castles
    black_king_can_castle = 'k' in castles
    black_queen_can_castle = 'q' in castles
    en_passant_target = None if en_passant == '-' else _from_algebraic_to_int(en_passant)
    halfmove_clock = int(halfmove)
    fullmove_number = int(fullmove)

    return Board(squares, whites_to_move, white_king_can_castle, white_queen_can_castle, black_king_can_castle,
                 black_queen_can_castle, en_passant_target, halfmove_clock, fullmove_number)


def _to_fen(board: Board) -> str:
    rows = []
    squares = board.squares
    blank_counter = 1
    data = squares
    for i in range(8):
        row_str, data = data[:8], data[8:]
        row = ''
        for piece in row_str:
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

    fen_result += 'w' if board.whites_to_move else 'b'
    fen_result += ' '

    castles = ''
    castles += 'K' if board.white_king_can_castle else ''
    castles += 'Q' if board.white_queen_can_castle else ''
    castles += 'k' if board.black_king_can_castle else ''
    castles += 'q' if board.black_queen_can_castle else ''

    fen_result += castles if castles != '' else '-'
    fen_result += ' '

    fen_result += _from_int_to_algebraic(board.en_passant_target) if board.en_passant_target is not None else '-'
    fen_result += ' '

    fen_result += str(board.halfmove_clock) + ' ' + str(board.fullmove_number)
    return fen_result
