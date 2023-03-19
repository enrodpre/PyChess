import re

from model import Color
from util import get_games_db_filename


class PNGConstant:
    NUMBER_TURN_SUFIX = '.'
    REST_LINE_COMMENT = ';'
    START_COMMENT = '{'
    END_COMMENT = '}'
    KINGSIDE_CASTLE = 'O-O'
    QUEENSIDE_CASTLE = 'O-O-O'
    CAPTURE = 'x'
    KING = 'K'
    QUEEN = 'Q'
    ROOK = 'R'
    BISHOP = 'B'
    KNIGHT = 'N'
    PAWN = 'P'
    PROMOTION = '='
    CHECKING_MOVE = '+'
    CHECKMATING_MOVE = '#'
    START_TAG = '['
    END_TAG = ']'


class PNGRegexp:
    COMMENT = r'{[^{]+}'
    BLACK_MOVE_NOTATION = r'[0-9]+\.{2,}\s'
    GAME_RESULT = r'[01(1/2)]-[01(1/2)]'


class MoveTester:
    color_moving: Color
    fullmove_cursor: int


def read_str_game():
    with open(get_games_db_filename(), 'r', encoding='utf-8') as games_db:
        tag_matcher = re.compile(r'^\[', re.A)
        game_end_matcher = re.compile(PNGRegexp.GAME_RESULT, re.A)
        game_string = ''
        while True:
            line = games_db.readline()
            if not tag_matcher.search(line):
                game_string += line
                if game_end_matcher.search(line):
                    break
        return game_string


def read_game():
    string = read_str_game()
    string = re.sub(PNGRegexp.COMMENT, '', string)
    string = re.sub(PNGRegexp.BLACK_MOVE_NOTATION, '', string)

    return string


NUMBER_GAMES_TO_BE_PARSED = 1

game_regexp = r'^\[[[^\]]\]'


class GameParser:
    pass
