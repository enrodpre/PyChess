import os
import sys

from board import Board
from move import generar_cada_movimiento
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


def make_move(start: int, end: int):
    pass


def iniciar_partida():
    board = Board.classic()

    ui = Ui(board.stringify(), sprite_filename, make_move)
    posible_movements = generar_cada_movimiento(board)
    ui.next_turn(posible_movements)
    ui.loop()
