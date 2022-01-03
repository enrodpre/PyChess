from __future__ import annotations

import copy
from itertools import chain, permutations, repeat, starmap
from typing import Iterator, Callable

from aenum import Enum

from board import Board
from model import LEFT_TOP_DIRECTION, LEFT_BOTTOM_DIRECTION, RIGHT_BOTTOM_DIRECTION, RIGHT_TOP_DIRECTION, \
    LEFT_DIRECTION, BOTTOM_DIRECTION, Slot, Vector, RIGHT_DIRECTION, TOP_DIRECTION, Move, Moves
from piece import Color, PieceType, Piece

MovesIterator = Iterator[Move]


def _get_direction(color: int) -> int:
    return 1 if color == Color.WHITE else -1


def _is_inbound(slot: Slot) -> bool:
    x, y = slot
    return 0 <= y <= 7 and 0 <= x <= 7


class MoveGenerator:
    class MovementFlag(Enum):
        ILLEGAL = 0
        TAKABLE = 1
        EMPTY_SAFE = 2
        EMPTY_THREATENED = 3

    board: Board

    def get_flag_move(self, slot: Slot, color: int, can_take: bool) -> int:
        if not _is_inbound(slot):
            return self.MovementFlag.ILLEGAL
        position = slot.flat()
        target = self.board.squares[position]
        if target is not None or self.board.en_passant_target == position:
            if target.color == color:
                return self.MovementFlag.ILLEGAL
            if can_take:
                return self.MovementFlag.TAKABLE
        return self.MovementFlag.EMPTY_SAFE

    def _filter_moves(self, v: MovesIterator, color: int, can_take: bool, checker_function: Callable) -> MovesIterator:
        # try:
        for move in v:
            if move is not None and checker_function(self.get_flag_move(move.end, color, can_take)):
                yield move
            else:
                pass
                # print(f'Discarded move -> {move}')
        # except TypeError:
        #    pass

    def pawn_movement(self, posicion: int, color: int) -> MovesIterator:
        start = Slot.fromflat(posicion)
        direction_vector = _get_direction(color)

        def _forward_movements(s: Slot, c: int, d: int) -> MovesIterator:
            def set_en_passant(board: Board, slot: Slot, _):
                board.en_passant_target = (slot + (0, 1)).flat()

            yield Move(s, s + Vector(0, 1, d))

            v = None
            if s.y == 1 and c == Color.WHITE:
                v = 0, 2
            if s.y == 6 and c == Color.BLACK:
                v = 0, 2
            if v is not None:
                yield Move(s, s + v).add_side_effect(set_en_passant)

        def _attack(s: Slot, direction: int) -> MovesIterator:
            yield from (Move(s, s + Vector(*v, d)) for v, d in zip([(1, 1), (1, -1)], repeat(direction, 2)))

        yield from self._filter_moves(_forward_movements(start, color, direction_vector), color,
                                      False, lambda flag: flag == self.MovementFlag.EMPTY_SAFE)
        yield from self._filter_moves(_attack(start, direction_vector), color, True,
                                      lambda flag: flag == self.MovementFlag.TAKABLE)

    def knight_movement(self, posicion: int, color: int) -> MovesIterator:
        start = Slot.fromflat(posicion)
        steps = ((1, 2), (-1, 2), (1, -2), (-1, -2), (2, 1), (-2, 1), (2, -1), (-2, -1))
        yield from self._filter_moves(
            (Move(start, start + step) for step in steps),
            color, False, lambda flag: flag != self.MovementFlag.ILLEGAL
        )

    def _travel_squares(self, posicion: int, color: int, directions: tuple[Vector, ...]) -> MovesIterator:
        for direction in directions:
            current = Slot.fromflat(posicion)
            while True:
                current += direction
                step_result = self.get_flag_move(current, color, True)
                if step_result != self.MovementFlag.ILLEGAL:
                    yield Move(Slot.fromflat(posicion), current)
                if step_result != self.MovementFlag.EMPTY_SAFE:
                    break

    BISHOP_MOVEMENTS = (LEFT_TOP_DIRECTION, LEFT_BOTTOM_DIRECTION, RIGHT_BOTTOM_DIRECTION, RIGHT_TOP_DIRECTION)

    def bishop_movement(self, posicion: int, color: int) -> MovesIterator:
        yield from self._travel_squares(posicion, color, self.BISHOP_MOVEMENTS)

    ROOK_MOVEMENTS = (TOP_DIRECTION, RIGHT_DIRECTION, BOTTOM_DIRECTION, LEFT_DIRECTION)

    def rook_movement(self, posicion: int, color: int) -> MovesIterator:
        yield from self._travel_squares(posicion, color, self.ROOK_MOVEMENTS)

    QUEEN_MOVEMENTS = BISHOP_MOVEMENTS + ROOK_MOVEMENTS

    def queen_movement(self, posicion: int, color: int) -> MovesIterator:
        yield from self.bishop_movement(posicion, color)
        yield from self.rook_movement(posicion, color)

    def king_movements(self, posicion: int, color: int) -> MovesIterator:
        start = Slot.fromflat(posicion)
        king_direction, queen_direction = Vector(2, 0), Vector(-2, 0)
        rook_king_direction, rook_queen_direction = Vector(-2, 0), Vector(3, 0)
        rook_king_position, rook_queen_position = Slot(7, 0).reverse(), Slot(0, 0).reverse()

        def _castle_travel_squares(end: Slot, next_step: Vector) -> bool:
            current = copy.copy(start)
            while True:
                current += next_step
                if self.MovementFlag.EMPTY_SAFE != self.get_flag_move(current, color, False):
                    return False
                if current == end:
                    return True

        def _try_castling(vector: Vector, king_step: Vector, rook_position: Slot, rook_direction: Vector,
                          rook_step: Vector) -> bool:
            return _castle_travel_squares(start + vector, king_step) and _castle_travel_squares(
                rook_position + rook_direction, rook_step)

        def _castle() -> MovesIterator:
            def build_move(king_start: Slot, king_move: Vector, rook_start: Slot, rook_move: Vector) -> Move:
                return Move(king_start, king_start + king_move).add_side_effect(
                    lambda board, *_: board.swap(rook_start.flat(), (rook_start + rook_move).flat()))

            if color == Color.WHITE:
                if (self.board.white_king_can_castle and
                        _try_castling(king_direction, RIGHT_DIRECTION, rook_king_position, rook_king_direction,
                                      LEFT_DIRECTION)):
                    yield build_move(start, king_direction, rook_king_position, rook_queen_position)

                if (self.board.white_queen_can_castle and
                        _try_castling(queen_direction, LEFT_DIRECTION, rook_queen_position, rook_queen_direction,
                                      RIGHT_DIRECTION)):
                    yield build_move(start, queen_direction, rook_queen_position, rook_queen_direction)
            else:
                if self.board.black_king_can_castle and _try_castling(king_direction, RIGHT_DIRECTION,
                                                                      rook_king_position.reverse(),
                                                                      rook_king_direction, LEFT_DIRECTION):
                    yield build_move(start, king_direction, rook_king_position.reverse(), rook_king_direction)
                if self.board.black_queen_can_castle and _try_castling(queen_direction, LEFT_DIRECTION,
                                                                       rook_queen_position.reverse(),
                                                                       rook_queen_direction, RIGHT_DIRECTION):
                    yield build_move(start, queen_direction, rook_queen_position.reverse(), rook_queen_direction)

        def forbid_castle(board: Board, start_position: Slot, _: Slot) -> None:
            piece_type, piece_color = board.squares[start_position.flat()]

            def check_rook(*compared_position) -> bool:
                return piece_type is piece_type.ROOK and start_position == compared_position

            is_king = piece_type is PieceType.KING
            if piece_color == Color.WHITE:
                if check_rook(0, 0) or is_king:
                    board.white_queen_can_castle = False
                elif check_rook(7, 0) or is_king:
                    board.white_king_can_castle = False
            elif piece_color == Color.BLACK:
                if check_rook(0, 7) or is_king:
                    board.black_queen_can_castle = False
                elif check_rook(7, 7) or is_king:
                    board.black_king_can_castle = False

        for step in filter(lambda p: p != [0, 0], permutations([1, 0, -1], 2)):
            yield Move(start, start + step).add_side_effect(forbid_castle)
        yield from _castle()


generator = MoveGenerator()


def _generate_movements_per_piece(i: int, piece: Piece) -> MovesIterator:
    switch: dict[int, Callable[[int, int], MovesIterator]]
    switch = {0: generator.pawn_movement, 1: generator.knight_movement, 2: generator.bishop_movement,
              3: generator.rook_movement, 4: generator.queen_movement, 5: generator.king_movements}
    func = switch[PieceType(piece.type).value]
    if not (0 <= i <= 63):
        pass
    res = func(i, piece.color)
    return res
    # return (translate_move(m) for m in res)


def debug_piece(i: int):
    piece = None  # generator.board.squares[i]
    if piece is not None:
        print(list(_generate_movements_per_piece(i, piece)))


def translate_move(move: Move) -> Move:
    start, end, side_effects = move
    move.start = Slot.translate(start)
    move.end = Slot.translate(end)
    return move


def generate_movements(board: Board) -> Moves:
    generator.board = board
    pieces = board.get_current_turn_pieces()
    moves = starmap(_generate_movements_per_piece, pieces)
    return Moves(chain.from_iterable(moves))

    """
    match piece_type:  # type: ignore
            case PieceType.PAWN:
                func = generator.pawn_movement
            case PieceType.KNIGHT:
                func = generator.knight_movement
            case PieceType.BISHOP:
                func = generator.bishop_movement
            case PieceType.ROOK:
                func = generator.rook_movement
            case PieceType.QUEEN:
                func = generator.queen_movement
            case PieceType.KING:
                func = generator.king_movements
            case _:
                raise ValueError"""
