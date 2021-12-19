import unittest

from src.board import *


class MyTestCase(unittest.TestCase):
    def test_fen(self):
        board = Board.fromfen(STARTING_POSITION_FEN)
        fen = board.tofen()

        self.assertEqual(STARTING_POSITION_FEN, fen)


if __name__ == '__main__':
    unittest.main()
