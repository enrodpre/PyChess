import inspect
from itertools import chain
from typing import Iterator, Optional, Any

from board import Board
from piece import PIECES_DATA, Square, SpecialType, RegularType, Point, Piece, PieceType


class Move:
    start: int | Point
    end: int | Point


def sigue_dentro(i: int | Point) -> bool:
    if not isinstance(i, int):
        i = i.flat_integer()
    return 0 <= i <= 63


InjectableDataType = dict[str, dict[type, Any]]


def generar_datos_inyectables(board: Board, posicion: int, square: Square) -> InjectableDataType:
    return {
        'posicion': {int: posicion, Point: Point.from_divmod(posicion)},
        'color': {int: square.color},
        'squares': {tuple[Optional[Piece], ...]: board.squares},
        'white_king_can_castle': {bool: board.white_king_can_castle},
        'white_queen_can_castle': {bool: board.white_queen_can_castle},
        'black_king_can_castle': {bool: board.black_king_can_castle},
        'black_queen_can_castle': {bool: board.black_queen_can_castle},
        'en_passant_target': {int: board.en_passant_target}
    }


def generar_movimientos_regulares(board: Board, i: int, square: Square, regulares: RegularType, repeteable: bool) -> \
        Optional[Iterator[int]]:
    if regulares is None:
        return

    for regular in [r.flat_integer() for r in regulares]:
        current = i + regular
        while sigue_dentro(current):
            current_square = board.squares[current]
            if (current_square is not None and current_square.color
                == current_square.color) or square.type == PieceType.PAWN:
                break
            yield current
            if not repeteable or (current_square is not None and current_square.color != square.color):
                break
            current += regular


MovimientosPosiblesType: dict[int, list[int]]


def generar_movimientos_especiales(specials: SpecialType, data: InjectableDataType) -> Optional[Iterator[int]]:
    if specials is None:
        return

    for special in specials:
        args, *_, annotations = inspect.getfullargspec(special)
        parameters = [data[arg][annotations[arg]] for arg in args]
        yield special(*parameters)


def generar_cada_movimiento(board: Board):
    movimientos = dict()
    for i, square in board.squares.skippingiter():
        piece, (regulares, repeteable, specials) = PIECES_DATA[square.tostr()]

        dependencias_inyectables = generar_datos_inyectables(board, i, square)
        movimientos_regulares = generar_movimientos_regulares(board, i, square, regulares, repeteable)
        movimientos_especiales = generar_movimientos_especiales(specials, dependencias_inyectables)

        movimientos.update({i: list(chain(movimientos_regulares if movimientos_regulares is not None else [],
                                          movimientos_especiales if movimientos_especiales is not None else []))})
