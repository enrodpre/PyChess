from game import Game
from src.piece import Piece


def main():
    p = Piece.fromstr('b')
    g = Game()
    g.initialize_game()


if __name__ == '__main__':
    main()
