from game import GameManager


def start_chess():
    game_manager = GameManager()
    game_manager.create_game()
    game_manager.manage_game()


if __name__ == '__main__':
    start_chess()
