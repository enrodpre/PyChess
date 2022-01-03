import os
import sys

from board import Board
from model import Move
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


class Game:
    board: Board
    ui: Ui

    def __init__(self):
        self.board = Board.classic()
        self.ui = Ui(self.board, sprite_filename, self.end_turn, lambda i: debug_piece(i))

    def initialize_game(self):
        self.ui.initialize_ui()
        self.start_turn()
        self.ui.loop()

    def start_turn(self):
        self.ui.start_turn(generate_movements(self.board))

    def end_turn(self, move: Move):
        start, end, side_effects = move
        self.board.swap(start.flat(), end.flat())

        self.board.prepare_next_turn()
        for func in side_effects:
            func(self.board, start, end)
        self.start_turn()
