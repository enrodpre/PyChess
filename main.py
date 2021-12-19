from game import iniciar_partida
from src.piece import Piece


def main():
    p = Piece.fromstr('b')
    print(p)
    iniciar_partida()


if __name__ == '__main__':
    main()
