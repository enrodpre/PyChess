import cProfile
import pstats
import random
import unittest
from time import time

from more_itertools import collapse

from game import Game, GameManager
from model import Moves, Move, GameStateFlag, PieceType, Color
from ui import Controller
from util import getpath


def get_random_move(datamoves: Moves) -> Move:
    moves = list(collapse(datamoves.values(), base_type=Move))
    return random.choice(moves)


def nop(*_):
    pass


separator = '=================='


def log_gamestate(gamestate):
    with open(getpath() + '/logs/log', 'a') as log:
        res = [str(gamestate), separator + '\n']

        log.writelines('\n'.join(res))


def log_move(m):
    with open(getpath() + '/logs/log', 'a') as log:
        res = [str(m), separator]

        log.writelines('\n'.join(res) + '\n')


def represent_graphically(game: Game):
    controller = Controller(game.game_state, nop)
    controller.initialize()
    controller.start_turn(game.current_moves)
    print(game.game_state)
    # print(state.to_fen())


class MyTestCase(unittest.TestCase):
    game: Game
    controller: Controller
    iteration: int
    depth: int = 50
    make_move_each_s = 0.05
    profile = False
    last_move: Move

    def setUp(self) -> None:
        self.game = Game(GameManager.STARTING_POSITION_FEN)
        self.iteration = self.depth
        self.controller = Controller(self.game.game_state)
        if self.profile:
            self.pr = cProfile.Profile()
            self.pr.enable()

    def tearDown(self) -> None:
        if self.profile:
            p = pstats.Stats(self.pr)
            p.strip_dirs()
            p.sort_stats('cumtime')
            p.print_stats()

    def test_game_graphics(self):
        self.game.start_game()
        self.controller.initialize()

        while self.iteration > 0:
            log_gamestate(self.game.game_state)
            self.game.next_turn()
            self.controller.start_turn(self.game.current_moves, self.make_move_each_s)
            move_to_make = get_random_move(self.game.current_moves)
            self.game.end_turn(move_to_make)
            log_move(move_to_make)

    def mal(self):
        self.assertTrue(False)
        print(self.game.game_state)
        print(self.game.game_state.to_fen())
        represent_graphically(self.game)

    def bien(self):
        self.assertTrue(True)
        print(self.game.game_state)
        print(self.game.game_state.to_fen())
        represent_graphically(self.game)

    def test_game(self):
        self.controller.initialize()
        self.game.start_game()
        turn_number = 0
        accumulated_time = 0
        while self.iteration > 0:
            start = time()
            self.game.next_turn()
            self.controller.start_turn(self.game.current_moves, self.make_move_each_s)
            self.last_move = get_random_move(self.game.current_moves)
            self.check_move(self.last_move)
            try:
                self.game.end_turn(self.last_move)
                self.check_gamestate()
            except ValueError as e:
                print(self.last_move)
                print(self.game.game_state)

            turn_number += 1
            loop_time = time() - start
            accumulated_time += loop_time
            print(f'Ha tardado {loop_time}s. Acumulado {accumulated_time}')

    def check_move(self, move: Move):
        start, end, _ = move
        state = self.game.game_state
        moving_piece = state.get_piece(start)
        target_slot = state.get_piece(end)

        if moving_piece is None or moving_piece.color is not state.next_to_move:
            self.mal()
        elif target_slot is not None and (
                target_slot.color is moving_piece.color or target_slot.type is PieceType.KING):
            self.mal()

        if move.piece is PieceType.KING:
            if end in self.game.move_generator.threats:
                self.mal()

    def check_gamestate(self):
        self.check_if_forbiden_move_is_made()
        self.check_if_game_has_ended()

    def check_if_forbiden_move_is_made(self):
        try:
            self.game.game_state.find_king(Color.WHITE)
            self.game.game_state.find_king(Color.BLACK)
        except ValueError:
            self.mal()

    def check_if_game_has_ended(self):
        for flag in (GameStateFlag.STALEMATE, GameStateFlag.CHECKMATE, GameStateFlag.DRAW):
            if self.game.game_state.check_flag(flag):
                self.bien()


if __name__ == '__main__':
    unittest.main()
