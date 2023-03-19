import unittest

from game import GameManager
from model import GameState


class MyTestCase(unittest.TestCase):
    def test_fen(self):
        g = GameState.from_fen(GameManager.STARTING_POSITION_FEN)
        b = g.to_fen()
        self.assertEqual(GameManager.STARTING_POSITION_FEN, b)


if __name__ == '__main__':
    unittest.main()
