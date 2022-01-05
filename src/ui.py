from typing import Optional, Callable

import pygame as pg
from pygame import SRCALPHA

from model import Slot, Moves, GameState, Color, Piece  # type: ignore

pg.init()


class SpriteSheet:
    def __init__(self, filename: str):
        self.sheet = pg.image.load(filename).convert_alpha()

    def image_at(self, rectangle):
        rect = pg.Rect(rectangle)
        image = pg.Surface(rect.size).convert_alpha()
        image.blit(self.sheet, (0, 0), rect)
        return image

    def load_sheet(self) -> dict[str, pg.Surface]:
        num_rows, num_cols = 2, 6
        x_margin, x_padding, y_margin, y_padding = 0, 0, 0, 0  # 64, 72, 68, 48
        sheet_rect = self.sheet.get_rect()
        sheet_width, sheet_height = sheet_rect.size

        x_sprite_size = (sheet_width - 2 * x_margin
                         - (num_cols - 1) * x_padding) / num_cols
        y_sprite_size = (sheet_height - 2 * y_margin
                         - (num_rows - 1) * y_padding) / num_rows

        sprite_rects = []
        for row_num in range(num_rows):
            for col_num in range(num_cols):
                # Position of sprite rect is margin + one sprite size
                #   and one padding size for each row. Same for y.
                x = x_margin + col_num * (x_sprite_size + x_padding)
                y = y_margin + row_num * (y_sprite_size + y_padding)
                sprite_rect = (x, y, x_sprite_size, y_sprite_size)
                sprite_rects.append(sprite_rect)

        grid_images = [self.image_at(rect).convert_alpha() for rect in sprite_rects]
        print(f"Loaded {len(grid_images)} grid images.")

        return dict(zip('kqrnbpKQRNBP', grid_images))


Square = tuple[pg.Rect, Optional[Piece]]


class Ui:
    _squares_per_side = 8
    _white_square_color = pg.Color('Orange')
    _black_square_color = pg.Color('Brown')
    _action_square_color = pg.Color('Yellow')
    _square_side: int
    _window_resolution: tuple[int, int]
    _squares: list[Square]
    _posible_movements: Moves
    _sprites: dict[str, pg.Surface]
    _game_state: GameState
    _selected_square: Optional[Slot] = None
    _lit_squares: list[Slot] = []

    def __init__(self, board: GameState, filename_sheets: str, make_move_callback: Callable, debug_square: Callable):
        self._game_state = board
        self._square_side = 70
        self._window_resolution = (560, 560)
        self._squares = []
        self._master = pg.display.set_mode(self._window_resolution, SRCALPHA)
        self._sprites = SpriteSheet(filename_sheets).load_sheet()
        self._make_move_callback = make_move_callback
        self._debug_square = debug_square

    def initialize_ui(self):
        self.create_squares()

    def start_turn(self, posible_movements: Moves):
        self._posible_movements = posible_movements
        self._update_squares()

    def loop(self):
        running = True
        while running:
            for event in pg.event.get():
                if event.type == pg.MOUSEBUTTONDOWN:
                    self.handle_click(self._get_coordinate(*pg.mouse.get_pos()))
                elif event.type == pg.QUIT:
                    running = False

            pg.display.flip()

    def handle_click(self, square_slot: Slot):
        piece = self._game_state.board[square_slot.flat()]
        if self._selected_square is None and piece is not None and self._is_correct_turn(piece.color):
            self.handle_not_selected(square_slot)
            self._debug_square(square_slot.flat())
            print(piece)
        else:
            squares, selected = self._lit_squares, self._selected_square
            self._restore_lit_squares()
            if square_slot in squares:
                self._make_move_callback(self._posible_movements.get_move(selected, square_slot))

    def handle_not_selected(self, source_point: Slot):
        self._selected_square = source_point
        for point in self._posible_movements.from_start(source_point):
            pos = point.flat()
            posible_rect, _ = self._squares[pos]
            self._update_rect(pos, self._action_square_color)
            self._lit_squares.append(point)

    def create_squares(self):
        for position, square_content in self._game_state.board.translated_iterator():
            # x, y = Slot.translate(*divmod(position, 8)[::-1])
            x, y = Slot.translate(*divmod(position, 8)[::-1])
            rect = pg.Rect((x * self._square_side, y * self._square_side, self._square_side, self._square_side))
            self._squares.append((rect, square_content))

    def _update_squares(self):
        for position, square_content in self._game_state.board.translated_iterator():
            r, p = self._squares[position]
            self._squares[position] = (r, square_content)
            self._update_rect(position)

    def _restore_lit_squares(self):
        for lit_square in self._lit_squares:
            self._update_rect(lit_square.flat())
        self._lit_squares = []
        self._selected_square = None

    def _update_rect(self, pos: int, color: Color = None):
        rect_object, piece = self._squares[pos]
        self._draw_rect(rect_object, color if color is not None else self._get_square_color(pos))
        if piece is not None:
            self._draw_sprite(rect_object, piece.representation)

    def _draw_sprite(self, rect_object: pg.Rect, piece: str):
        sprite = self._sprites[piece]
        self._master.blit(sprite, sprite.get_rect(center=rect_object.center))

    def _draw_rect(self, rect_object: pg.Rect, color: pg.Color) -> pg.rect.Rect:
        return pg.draw.rect(self._master, color, rect_object)

    def _get_square_color(self, square_number: int):
        return (self._white_square_color, self._black_square_color)[
            (-square_number - square_number // self._squares_per_side) % 2]

    def _is_correct_turn(self, color: int):
        return (self._game_state.whites_to_move and color == Color.WHITE) or (
                not self._game_state.whites_to_move and color == Color.BLACK)

    def _get_coordinate(self, x: int, y: int) -> Slot:
        return Slot.translate(x // self._square_side, y // self._square_side)
