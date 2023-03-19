import random

from model import GameState, Move, Moves, Piece, GameStateFlag, PieceType
from move_generator import MoveGenerator
from ui import Controller


class Game:
    game_state: GameState
    move_generator: MoveGenerator
    current_moves: Moves

    def __init__(self, fen: str):
        self.game_state = GameState.from_fen(fen)
        self.move_generator = MoveGenerator(self.game_state)

    def start_game(self):
        self.prepare_next_turn()

    def prepare_next_turn(self):
        # Configure move generator
        self.move_generator.clear()

        # Generate threats
        self.move_generator.generate_threats()

        # Get flags from threats generated and raise them
        flag = self.move_generator.get_flag_from_threats()
        if flag is not None:
            self.game_state.state_flag = flag

        # generate possible movements and start turn
        self.current_moves = self.move_generator.generate_movements()
        # pprint.pp(self.current_moves)

        # check game state
        self.check_game_state()

    def next_turn(self):
        pass

    def check_game_state(self):
        if self.game_state.halfmove_clock > 49:
            self.game_state.raise_flag(GameStateFlag.DRAW)

        no_movements_allowed = self.current_moves.isempty()
        if no_movements_allowed:
            if self.game_state.check_flag(GameStateFlag.CHECK):
                self.game_state.raise_flag(GameStateFlag.CHECKMATE)
            else:
                self.game_state.raise_flag(GameStateFlag.STALEMATE)

    def end_turn(self, move: Move):
        # Extract datamove
        start, end, side_effects = move

        # Make move
        self.game_state.commit_move(start, end)

        # Execute side effects
        for side_effect in side_effects:
            side_effect(self, move)

        self.prepare_next_turn()

    def promote_pawn(self, move: Move):
        random_piecetype = random.choice((PieceType.QUEEN, PieceType.ROOK, PieceType.BISHOP, PieceType.KNIGHT))
        new_piece = Piece(move.piece.color, random_piecetype)
        self.game_state.promote_pawn(move.end, new_piece)


class GraphicalGame(Game):
    controller: Controller

    def __init__(self, fen: str):
        super(GraphicalGame, self).__init__(fen)
        self.controller = Controller(self.game_state)

    def start_game(self):
        super(GraphicalGame, self).start_game()
        self.controller.initialize()

    def next_turn(self):
        super(GraphicalGame, self).next_turn()
        return self.controller.start_turn(self.current_moves)

    def promote_pawn(self, move: Move):
        slot, piece = self.controller.show_promote_menu(move.end, move.piece.color)
        self.game_state.promote_pawn(slot, piece)
        self.controller.update_data()


class GameManager:
    STARTING_POSITION_FEN = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1'
    QUEEN_TESTING = '8/8/3q4/8/8/3Q4/8/8'
    KING_TESTING = '8/8/3q4/1K6/8/8/8/8'
    CASTLE_TESTING = 'r2k3r/pppppppp/8/8/8/8/PPPPPPPP/R2K3R w KQkq - 0 1'
    THREAT_TESTING = '1k6/8/8/q3R2K/8/8/8/8'
    EN_PASSANT_TESTING = 'k7/8/8/8/5p2/8/4P3/K7 w - - 0 1'
    PROMOTING_TESTING = 'k7/2P5/8/8/8/8/8/K7'
    THREAT2_TESTING = 'k1B5/8/8/8/8/8/8/K7'
    CHECK_TESTING = 'k7/8/8/3K3r/8/8/8/8'
    REST_TESTING = ' w KQkq - 0 1'

    game: GraphicalGame

    def create_game(self):
        self.game = GraphicalGame(self.PROMOTING_TESTING + self.REST_TESTING)

    def create_graphical_game(self):
        self.game = GraphicalGame(self.STARTING_POSITION_FEN)

    def manage_game(self):
        self.game.start_game()
        while True:
            move = self.game.next_turn()
            print(self.game.current_moves)
            self.game.end_turn(move)

            for flag in (GameStateFlag.STALEMATE, GameStateFlag.CHECKMATE, GameStateFlag.DRAW):
                if self.game.game_state.check_flag(flag):
                    print(f'El resultado es {self.game.game_state.state_flag}')
                    break
