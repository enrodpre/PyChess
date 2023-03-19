from __future__ import annotations

import copy
from collections import Counter
from enum import Flag, auto, Enum
from itertools import chain
from typing import Iterator, Callable, Optional

from model import Slot, Vector, Move, Moves, GameState, PieceType, Piece, KNIGHT_MOVEMENTS, PAWN_ATTACK_MOVEMENTS, \
    WHITE_PAWN, BLACK_PAWN, \
    TOP_DIRECTION, BISHOP_MOVEMENTS, ROOK_MOVEMENTS, \
    GameStateFlag, ColorPieceSet, WHITE_KING, WHITE_QUEEN_ROOK_INITIAL_STATE, \
    WHITE_KING_ROOK_INITIAL_STATE, BLACK_QUEEN_ROOK_INITIAL_STATE, BLACK_KING_ROOK_INITIAL_STATE, GODLIKE_MOVEMENTS
from superclasses import flatten_until
from util import is_inbound

MovesIterator = Iterator[Move]


def none_iter():
    return iter(())


def pipe(*args):
    return args


def true(*_):
    return True


def nop(*_):
    return None


def pawn_attack(start: Slot, piece: Piece):
    for v in PAWN_ATTACK_MOVEMENTS:
        yield Move.from_step(piece, start, Vector(*v, piece.direction()))


def pawn_regular_movement(start: Slot, piece: Piece) -> MovesIterator:
    yield Move(piece, start, start + TOP_DIRECTION * piece.direction())


def pawn_twostep_movement(start: Slot, piece: Piece) -> MovesIterator:
    v = None
    if start.y == 1 and piece == WHITE_PAWN:
        v = 0, 2
    if start.y == 6 and piece == BLACK_PAWN:
        v = 0, -2
    if v is not None:
        yield Move(piece, start, start + v)


def promote_pawn(gm, m):
    if (m.piece == BLACK_PAWN and m.end.y == 0) or (m.piece == WHITE_PAWN and m.end.y == 7):
        gm.promote_pawn(m)


def remove_en_passant_target_pawn(gm, m: Move):
    (start_x, start_y), (end_x, end_y), _ = m
    gm.game_state.remove(Slot(end_x, start_y))


def not_double_check(mg): return not mg.game_state.check_flag(GameStateFlag.DOUBLE_CHECK)


def move_rook_in_castle(gm, move: Move):
    start, end, _ = move
    end_x, end_y = end
    rook_start = Slot(7 if 4 < end_x else 0, end_y)
    rook_end = start + (end - start) // 2
    gm.game_state.move(rook_start, rook_end)


def forbid_castle_king(gm, move: Move):
    gm = gm.game_state
    if move.piece == WHITE_KING:
        gm.white_king_can_castle = False
        gm.white_queen_can_castle = False
    else:
        gm.black_queen_can_castle = False
        gm.black_king_can_castle = False


def regular_king_movements(start: Slot, piece: Piece) -> MovesIterator:
    yield from (Move(piece, start, start + step) for step in GODLIKE_MOVEMENTS)


def forbid_castle_rook(gm, move: Move):
    if WHITE_QUEEN_ROOK_INITIAL_STATE == move.start:
        gm.game_state.white_queen_can_castle = False
    elif WHITE_KING_ROOK_INITIAL_STATE == move.start:
        gm.game_state.white_king_can_castle = False
    elif BLACK_QUEEN_ROOK_INITIAL_STATE == move.start:
        gm.game_state.black_queen_can_castle = False
    elif BLACK_KING_ROOK_INITIAL_STATE == move.start:
        gm.game_state.black_king_can_castle = False


def knight_movement(start: Slot, piece: Piece) -> MovesIterator:
    for step in KNIGHT_MOVEMENTS:
        yield Move(piece, start, start + step)


def is_aligned(start: Slot, step: Vector, stop: Slot):
    current = copy.copy(start)
    steps = 0
    while True:
        current += step
        steps += 1
        if not is_inbound(*current):
            return False
        if current == stop:
            return steps - 1


repeteable_moves_per_piecetype = {
    PieceType.BISHOP: BISHOP_MOVEMENTS,
    PieceType.ROOK: ROOK_MOVEMENTS,
    PieceType.QUEEN: BISHOP_MOVEMENTS + ROOK_MOVEMENTS
}


class GeneratorMode(Enum):
    MOVEMENTS = 0
    THREATS = 1


class TargetSquareFlag(Flag):
    EMPTY = auto()
    ALLY = auto()
    ENEMY = auto()
    ISOLATED = auto()
    GUARDED = auto()

    EMPTY_ISOLATED = EMPTY | ISOLATED
    EMPTY_GUARDED = EMPTY | GUARDED
    ENEMY_ISOLATED = ENEMY | ISOLATED
    ENEMY_GUARDED = ENEMY | GUARDED


class MoveRestrictor:
    """
        If theres one defender, that piece can only move along the slots
        that belong to the line
        If theres no defender, it means the king is checked. Only moves permitted:
            King outside the line
            Other piece to the line
    """
    game_state: GameState
    threatening_slot: Optional[Slot]
    threatening_line_slots: list[Slot]
    forced_movements_per_piece: dict[Slot, list[Slot]]
    forbidden_king_move_slots: list[Slot]

    def __init__(self, game_state: GameState):
        self.game_state = game_state
        self.threatening_slot = None
        self.forced_movements_per_piece = {}
        self.forbidden_king_move_slots = []
        self.threatening_line_slots = []

    def add_threatening_line(self, start: Slot, step: Vector, end: Slot):
        self.threatening_slot = start
        current = copy.copy(start)
        slot_list, defenses_list = [], []
        defenses_color = self.game_state.next_to_move
        while True:
            current += step
            if current == end:
                break
            current_piece = self.game_state.get_piece(current)
            if current_piece is None:
                slot_list.append(copy.copy(current))
            elif current_piece.color is defenses_color:
                defenses_list.append(copy.copy(current))
            else:
                return

        if len(defenses_list) == 1:
            self.forced_movements_per_piece |= {defenses_list.pop(): slot_list}
        elif len(defenses_list) == 0:
            self.game_state.raise_flag(GameStateFlag.CHECK)
            self.threatening_line_slots = slot_list
            self.forbidden_king_move_slots.append(current + step)

    def filter(self, moves: MovesIterator) -> MovesIterator:
        for move in moves:
            if self.game_state.check_flag(GameStateFlag.DOUBLE_CHECK):
                # If double check only king can move
                if move.piece.type is PieceType.KING:
                    yield move
            elif self.game_state.check_flag(GameStateFlag.CHECK):
                if move.piece.type is PieceType.KING:
                    # If check, king cannot move within the line or behind
                    if (move.end not in self.forbidden_king_move_slots
                            and move.end not in self.threatening_line_slots):
                        yield move
                else:
                    # If check, other pieces can only move within the line
                    if move.end in self.threatening_line_slots or move.end == self.threatening_slot:
                        yield move
            else:
                restriction = self.forced_movements_per_piece.get(move.start)
                if restriction is None or move.end in restriction:
                    yield move


class MoveGenerator:
    game_state: GameState

    threats: list[Slot]
    mode: GeneratorMode
    threatening_pieces: ColorPieceSet
    moving_pieces: ColorPieceSet

    restrictor: MoveRestrictor
    moving_king_position: Slot

    def __init__(self, game_state: GameState):
        self.game_state = game_state

    def clear(self):
        self.threatening_pieces, self.moving_pieces = self.game_state.get_pieces(True)
        self.threats = []
        self.moving_king_position = self.game_state.find_king()
        self.restrictor = MoveRestrictor(self.game_state)

    def pawn_en_passant_attack(self, start: Slot, piece: Piece):
        en_passant_target = self.game_state.en_passant_target
        for move in pawn_attack(start, piece):
            if en_passant_target == move.end:
                yield move
                return

    def get_move_flag(self, move: Move) -> TargetSquareFlag:
        start, target_slot, *_ = move
        moving_piece = self.game_state.get_piece(start)
        target_square = self.game_state.get_piece(target_slot)

        def is_target_safe(sl: Slot) -> bool:
            if self.mode is GeneratorMode.MOVEMENTS:
                return sl not in self.threats
            return True

        content_state: TargetSquareFlag
        attacked_state: TargetSquareFlag

        if is_target_safe(target_slot):
            attacked_state = TargetSquareFlag.ISOLATED
        else:
            attacked_state = TargetSquareFlag.GUARDED

        if target_square is None:
            content_state = TargetSquareFlag.EMPTY
        elif target_square.color == moving_piece.color:
            content_state = TargetSquareFlag.ALLY
        else:
            content_state = TargetSquareFlag.ENEMY

        return attacked_state | content_state

    def repeteable_moving_pieces(self, start: Slot, piece: Piece) -> MovesIterator:
        for direction in repeteable_moves_per_piecetype[piece.type]:
            current = copy.copy(start)
            discovering_more_threatening_lines = False
            while True:
                current += direction
                if not is_inbound(*current):
                    break
                step_result = self.get_move_flag(Move(piece, start, current))
                if TargetSquareFlag.ALLY in step_result:
                    break
                if not discovering_more_threatening_lines:
                    yield Move(piece, start, current)
                if TargetSquareFlag.EMPTY not in step_result:
                    if self.mode is GeneratorMode.THREATS:
                        if self.game_state.get_piece(current).type == PieceType.KING:
                            self.restrictor.add_threatening_line(start, direction, current)
                            break
                        discovering_more_threatening_lines = True
                        continue
                    break

    def filter_moves(self, move_iterator: MovesIterator, checker_function: Callable) -> MovesIterator:
        for move in filter(lambda m: m is not None and is_inbound(*m.end), move_iterator):
            flag = self.get_move_flag(move)
            if TargetSquareFlag.ALLY not in flag and checker_function(self, flag):
                yield move

    def king_castle_movements(self, _: Slot, piece: Piece) -> MovesIterator:
        for king_start, rook_start, direction in self.game_state.castle_available_info():
            # check if king's and rook's path is free
            current = copy.copy(king_start)
            while True:
                current += direction
                if current in self.threats:
                    break
                current_square = self.game_state.get_piece(current)
                if current != rook_start and current_square is not None:
                    break
                if current == rook_start:
                    yield Move(piece, king_start, king_start + direction * 2)
                    break

    def generate_piece(self, start: Slot, piece: Piece,
                       prefilter: PrefilterType,
                       generator_method: GeneratorMethodType,
                       side_effect: SideEffectType,
                       condition: ConditionType) -> MovesIterator:
        # prefilter
        if not prefilter(self):
            return

        # generate moves
        try:
            move_iterator = generator_method(self, start, piece)
        except TypeError:
            move_iterator = generator_method(start, piece)

        # restrict moves
        if self.mode is GeneratorMode.MOVEMENTS:
            move_iterator = self.restrictor.filter(move_iterator)

        # filter those that break condition
        move_iterator = self.filter_moves(move_iterator, condition)

        # set side effects
        for move in move_iterator:
            yield move.add_side_effect(side_effect) if side_effect != nop else move

    def generate_type(self, start: Slot, piece: Piece) -> Iterator[Move]:
        movement_types = movement_descriptor(piece)
        if movement_types is None:
            raise TypeError

        for movement_type in movement_types:
            yield from self.generate_piece(start, piece, *movement_type)

    @flatten_until(Move)
    def generate(self, mode: GeneratorMode, pieces: ColorPieceSet) -> list[Move]:
        self.mode = mode
        return list(chain.from_iterable((self.generate_type(*p) for p in pieces)))

    def generate_threats(self):
        move_threats = self.generate(GeneratorMode.THREATS, self.threatening_pieces)
        self.threats = [move.end for move in move_threats]

    def get_flag_from_threats(self) -> Optional[GameStateFlag]:
        check_counter = Counter(self.threats)
        times_checked = check_counter.get(self.moving_king_position)
        if times_checked is None:
            return None
        elif times_checked == 1:
            return GameStateFlag.CHECK
        else:
            return GameStateFlag.DOUBLE_CHECK

    def generate_movements(self) -> Moves:
        return Moves(self.generate(GeneratorMode.MOVEMENTS, self.moving_pieces))


# <editor-fold desc="Description">
PAWN_REGULAR_MOVEMENT = (
    lambda mg: not_double_check(mg) and mg.mode is GeneratorMode.MOVEMENTS, pawn_regular_movement, promote_pawn,
    lambda mg, flag: TargetSquareFlag.EMPTY in flag)
PAWN_TWOSTEPS_MOVEMENT = (
    lambda mg: not_double_check(mg) and mg.mode is GeneratorMode.MOVEMENTS, pawn_twostep_movement,
    lambda gm, m: gm.game_state.set_en_passant(m.start + TOP_DIRECTION * m.piece.direction()),
    lambda mg, flag: TargetSquareFlag.EMPTY in flag)
PAWN_ATTACK_MOVEMENT = (
    not_double_check, pawn_attack, promote_pawn,
    lambda mg, flag: GeneratorMode.THREATS is mg.mode or TargetSquareFlag.ENEMY in flag)
PAWN_EN_PASSANT_ATTACK_MOVEMENT = (
    lambda mg: (not_double_check(mg) and mg.mode is GeneratorMode.MOVEMENTS
                and mg.game_state.check_flag(GameStateFlag.EN_PASSANT)),
    MoveGenerator.pawn_en_passant_attack, remove_en_passant_target_pawn, true)
KNIGHT_MOVEMENT = (not_double_check, knight_movement, nop, pipe)
BISHOP_MOVEMENT = (not_double_check, MoveGenerator.repeteable_moving_pieces, nop, pipe)
ROOK_MOVEMENT = (not_double_check, MoveGenerator.repeteable_moving_pieces, forbid_castle_rook, pipe)
QUEEN_MOVEMENT = (not_double_check, MoveGenerator.repeteable_moving_pieces, nop, pipe)
KING_REGULAR_MOVEMENT = (
    true, regular_king_movements, forbid_castle_king,
    lambda mg, flag: TargetSquareFlag.ISOLATED in flag)
KING_CASTLE_MOVEMENT = (
    lambda mg: mg.mode is not GeneratorMode.THREATS and not_double_check(mg), MoveGenerator.king_castle_movements,
    lambda gm, m: forbid_castle_king(gm, m) or move_rook_in_castle(gm, m),
    pipe)

PrefilterType = Callable[[MoveGenerator], bool]
GeneratorMethodType = Callable[[Slot, Piece], MovesIterator]
SideEffectType = Callable[[GameState, Move], None]
ConditionType = Callable[[MovesIterator, TargetSquareFlag], bool]
MovementDescriptorsType = list[tuple[PrefilterType, GeneratorMethodType, SideEffectType, ConditionType]]
MovementMapperType: tuple[
    MovementDescriptorsType, MovementDescriptorsType,
    MovementDescriptorsType, MovementDescriptorsType,
    MovementDescriptorsType, MovementDescriptorsType
]

MovementMapper = (
    [PAWN_REGULAR_MOVEMENT, PAWN_TWOSTEPS_MOVEMENT, PAWN_ATTACK_MOVEMENT,
     PAWN_EN_PASSANT_ATTACK_MOVEMENT],
    [KNIGHT_MOVEMENT, ],
    [BISHOP_MOVEMENT, ],
    [ROOK_MOVEMENT, ],
    [QUEEN_MOVEMENT, ],
    [KING_REGULAR_MOVEMENT, KING_CASTLE_MOVEMENT]
)


# </editor-fold>

def movement_descriptor(piece: Piece) -> MovementDescriptorsType:
    return MovementMapper[piece.type.value]


"""
Chosen

1 - Generate threats from current position
2 - Evaluate threatening lines
3 - Generate possible movement of current position

"""
