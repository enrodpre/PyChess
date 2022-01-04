from __future__ import annotations

import copy
import pprint
from itertools import chain, repeat, starmap
from typing import Iterator, Callable

from aenum import Enum

from model import LEFT_TOP_DIRECTION, LEFT_BOTTOM_DIRECTION, RIGHT_BOTTOM_DIRECTION, RIGHT_TOP_DIRECTION, \
    LEFT_DIRECTION, BOTTOM_DIRECTION, Slot, Vector, RIGHT_DIRECTION, TOP_DIRECTION, Move, Moves, GameState, Color, \
    PieceType, Piece

MovesIterator = Iterator[Move]


def _get_direction(color: int) -> int:
    return 1 if color == Color.WHITE else -1


def is_legal_status():
    pass


class MoveGenerator:
    class MovementFlag(Enum):
        ILLEGAL = 0
        TAKABLE_SAFE = 1
        TAKABLE_THREATENED = 2
        EMPTY_SAFE = 3
        EMPTY_THREATENED = 4

    game_state: GameState
    threats: set[Slot]
    generating_threats: bool

    def get_flag_move(self, move: Move, can_take: bool) -> int:
        start, target_slot, *_ = move

        def is_target_safe() -> bool:
            if not self.generating_threats:
                return target_slot in self.threats

        def takable() -> int:
            if is_target_safe():
                return self.MovementFlag.TAKABLE_THREATENED
            else:
                return self.MovementFlag.TAKABLE_SAFE

        def is_inbound(slot: Slot) -> bool:
            x, y = slot
            return 0 <= y <= 7 and 0 <= x <= 7

        if not is_inbound(target_slot):
            return self.MovementFlag.ILLEGAL

        piece = self.game_state.board[start.flat()]
        flat_end = target_slot.flat()
        target_square = self.game_state.board[flat_end]
        if target_square is not None:
            if target_square.color == piece.color:
                return self.MovementFlag.ILLEGAL
            if can_take:
                return takable()

        # en passant
        if piece.type == PieceType.PAWN and self.game_state.en_passant_target == flat_end:
            return takable()

        if is_target_safe():
            return self.MovementFlag.EMPTY_SAFE
        else:
            return self.MovementFlag.EMPTY_THREATENED

    def _filter_moves(self, v: MovesIterator, can_take: bool, checker_function: Callable) -> MovesIterator:
        yield from (move for move in v if move is not None and checker_function(
            self.get_flag_move(move, can_take)))  # and self.generating_threats and not can_take)

    def pawn_movement(self, posicion: int) -> MovesIterator:
        start = Slot.fromflat(posicion)
        color = self.game_state.board[posicion].color
        direction_vector = _get_direction(color)

        def _forward_movements(s: Slot, c: int, d: int) -> MovesIterator:
            def set_en_passant(board: GameState, slot: Slot, _):
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

        if self.generating_threats:
            yield from self._filter_moves(_forward_movements(start, color, direction_vector),
                                          False, lambda flag: flag == self.MovementFlag.EMPTY_SAFE)
        yield from self._filter_moves(_attack(start, direction_vector), True,
                                      lambda flag: flag == self.MovementFlag.TAKABLE_SAFE)

    def knight_movement(self, posicion: int) -> MovesIterator:
        start = Slot.fromflat(posicion)
        steps = ((1, 2), (-1, 2), (1, -2), (-1, -2), (2, 1), (-2, 1), (2, -1), (-2, -1))
        yield from self._filter_moves(
            (Move(start, start + step) for step in steps),
            False, lambda flag: flag != self.MovementFlag.ILLEGAL
        )

    def _travel_squares(self, posicion: int, directions: tuple[Vector, ...]) -> MovesIterator:
        start = Slot.fromflat(posicion)
        for direction in directions:
            current = copy.copy(start)
            while True:
                current += direction
                if current == (8, 7):
                    pass
                step_result = self.get_flag_move(Move(start, current), True)
                if step_result != self.MovementFlag.ILLEGAL:
                    yield Move(start, current)
                if step_result != self.MovementFlag.EMPTY_SAFE:
                    break

    BISHOP_MOVEMENTS = (LEFT_TOP_DIRECTION, LEFT_BOTTOM_DIRECTION, RIGHT_BOTTOM_DIRECTION, RIGHT_TOP_DIRECTION)

    def bishop_movement(self, posicion: int) -> MovesIterator:
        yield from self._travel_squares(posicion, self.BISHOP_MOVEMENTS)

    ROOK_MOVEMENTS = (TOP_DIRECTION, RIGHT_DIRECTION, BOTTOM_DIRECTION, LEFT_DIRECTION)

    def rook_movement(self, posicion: int) -> MovesIterator:
        yield from self._travel_squares(posicion, self.ROOK_MOVEMENTS)

    GODLIKE_MOVEMENTS = BISHOP_MOVEMENTS + ROOK_MOVEMENTS

    def queen_movement(self, posicion: int) -> MovesIterator:
        yield from self.bishop_movement(posicion)
        yield from self.rook_movement(posicion)

    def king_movements(self, posicion: int) -> MovesIterator:
        if self.generating_threats:
            return iter(())

        start = Slot.fromflat(posicion)
        color = self.game_state.board[posicion].color
        king_direction, queen_direction = Vector(2, 0), Vector(-2, 0)
        rook_king_direction, rook_queen_direction = Vector(-2, 0), Vector(3, 0)
        rook_king_position, rook_queen_position = Slot(7, 0).reverse(), Slot(0, 0).reverse()

        def _castle_travel_squares(end: Slot, next_step: Vector) -> bool:
            current = copy.copy(start)
            while True:
                current += next_step
                if self.MovementFlag.EMPTY_SAFE != self.get_flag_move(Move(start, current), False):
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
                    lambda board, *_: board.move(rook_start.flat(), (rook_start + rook_move).flat()))

            if color == Color.WHITE:
                if (self.game_state.white_king_can_castle and
                        _try_castling(king_direction, RIGHT_DIRECTION, rook_king_position, rook_king_direction,
                                      LEFT_DIRECTION)):
                    yield build_move(start, king_direction, rook_king_position, rook_queen_position)

                if (self.game_state.white_queen_can_castle and
                        _try_castling(queen_direction, LEFT_DIRECTION, rook_queen_position, rook_queen_direction,
                                      RIGHT_DIRECTION)):
                    yield build_move(start, queen_direction, rook_queen_position, rook_queen_direction)
            else:
                if self.game_state.black_king_can_castle and _try_castling(king_direction, RIGHT_DIRECTION,
                                                                           rook_king_position.reverse(),
                                                                           rook_king_direction, LEFT_DIRECTION):
                    yield build_move(start, king_direction, rook_king_position.reverse(), rook_king_direction)
                if self.game_state.black_queen_can_castle and _try_castling(queen_direction, LEFT_DIRECTION,
                                                                            rook_queen_position.reverse(),
                                                                            rook_queen_direction, RIGHT_DIRECTION):
                    yield build_move(start, queen_direction, rook_queen_position.reverse(), rook_queen_direction)

        def forbid_castle(board: GameState, start_position: Slot, _: Slot) -> None:
            piece_type, piece_color = board.board[start_position.flat()]

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

        def ensure_safety_of_master(level_of_danger: int) -> bool:
            return level_of_danger == self.MovementFlag.EMPTY_SAFE or level_of_danger == self.MovementFlag.TAKABLE_SAFE

        yield from (move.add_side_effect(forbid_castle) for move in
                    self._filter_moves((Move(start, start + step) for step in self.GODLIKE_MOVEMENTS), True,
                                       ensure_safety_of_master))

        yield from _castle()


generator = MoveGenerator()


def _generate_movements_per_piece(i: int, piece: Piece) -> MovesIterator:
    match piece.type:  # type: ignore
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
            raise ValueError

    result = func(i)
    return result


def debug_piece(i: int):
    piece = None  # generator.board.squares[i]
    if piece is not None:
        print(list(_generate_movements_per_piece(i, piece)))


def translate_move(move: Move) -> Move:
    start, end, side_effects = move
    move.start = Slot.translate(start)
    move.end = Slot.translate(end)
    return move


def generate_threats(pieces: Iterator[tuple[int, Piece]]):
    generator.generating_threats = True
    threatening_moves = starmap(_generate_movements_per_piece, pieces)
    generator.threats = set(chain.from_iterable(threatening_moves))
    generator.generating_threats = False

    pass


def generate_movements(game_state: GameState) -> Moves:
    generator.game_state = game_state
    pieces = game_state.get_pieces()
    threatening_pieces, moving_pieces = pieces
    generate_threats(threatening_pieces)

    actual_moves = Moves(chain.from_iterable(starmap(_generate_movements_per_piece, moving_pieces)))
    print('threats')
    pprint.pp(generator.threats)
    print('movements')
    pprint.pp(actual_moves)

    return actual_moves

    """
    switch: dict[int, Callable[[int], MovesIterator]]
    switch = {0: generator.pawn_movement, 1: generator.knight_movement, 2: generator.bishop_movement,
              3: generator.rook_movement, 4: generator.queen_movement, 5: generator.king_movements}
    func = switch[PieceType(piece.type).value]
    r = func(i)
    """
