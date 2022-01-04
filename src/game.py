import os
import sys

from model import GameState, Move, Moves
from move import generate_movements, debug_piece
from ui import Ui


def getpath():
    if getattr(sys, 'frozen', False):
        # If the application is run as a bundle, the PyInstaller bootloader
        # extends the sys module by a flag frozen=True and sets the app
        # path into variable _MEIPASS'.
        application_path = getattr(sys, '_MEIPASS')
    else:
        application_path = os.path.dirname(os.path.abspath(__file__))

    return application_path


sprite_filename = getpath() + '/resources/sprites.png'

STARTING_POSITION_FEN = 'RNBQKBNR/PPPPPPPP/8/8/8/8/pppppppp/rnbqkbnr w KQkq - 0 1'
QUEEN_TESTING = '8/8/3Q4/8/8/3q4/8/8 w KQkq - 0 1'
KING_TESTING = '8/8/3q4/1K6/8/8/8/8 w KQkq - 0 1'
CASTLE_TESTING = 'R3K2R/PPPPPPPP/8/8/8/8/pppppppp/r3k2r w KQkq - 0 1'


class Game:
    game_state: GameState
    ui: Ui
    current_moves: Moves

    def __init__(self):
        self.game_state = GameState.from_fen(STARTING_POSITION_FEN)
        self.ui = Ui(self.game_state, sprite_filename, self.end_turn, lambda i: debug_piece(i))
        self.initialize_game()

    def initialize_game(self):
        self.ui.initialize_ui()
        self.start_turn()
        self.ui.loop()

    def start_turn(self):
        self.ui.start_turn(generate_movements(self.game_state))

    def end_turn(self, move: Move):
        # Make chosen move
        start, end, side_effects = move
        self.game_state.move(start.flat(), end.flat())

        # Change board status
        self.game_state.prepare_next_turn()
        for func in side_effects:
            func(self.game_state, start, end)

        # Next turn
        self.start_turn()
