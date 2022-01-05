import unittest

from game import STARTING_POSITION_FEN
from model import GameState


class MyTestCase(unittest.TestCase):
    def test_something(self):
        g = GameState.from_fen(STARTING_POSITION_FEN)
        b = g.board

        for i, e in b:
            self.assertEqual(e, b[i])


if __name__ == '__main__':
    unittest.main()
