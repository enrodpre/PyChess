from typing import Optional, Callable

import pygame as pg
from pygame import SRCALPHA

from piece import Point

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

        return dict(zip('kqrbnpKQRBNP', grid_images))


BoardRepresentation = tuple[Optional[str], ...]

SquareData = tuple[Optional[str], pg.Rect]
SquareDataSet = list[SquareData]


class Ui:
    _squares_per_side = 8
    _white_square_color = pg.Color('Orange')
    _black_square_color = pg.Color('Brown')
    _action_square_color = pg.Color('Yellow')
    _square_side: int
    _window_resolution: tuple[int, int]
    _squares: SquareDataSet
    _posible_movements: dict[int, list[int]]
    _sprites: dict[str, pg.Surface]

    _selected_square: Optional[int] = None

    def __init__(self, board: BoardRepresentation, filename_sheets: str, make_move_callback: Callable):
        self._square_side = 70
        self._window_resolution = (560, 560)
        self._squares = []
        self._master = pg.display.set_mode(self._window_resolution, SRCALPHA)
        self._sprites = SpriteSheet(filename_sheets).load_sheet()
        self._pintar_casillas(board)
        self._make_move_callback = make_move_callback

    def next_turn(self, posible_movements: dict[int, list[int]]):
        self._posible_movements = posible_movements

    def loop(self):
        def _get_coordinate(pixel: tuple[int, int]) -> Point:
            x, y = pixel
            return Point(x // self._square_side, y // self._square_side)

        running = True
        while running:
            for event in pg.event.get():
                if event.type == pg.MOUSEBUTTONDOWN:
                    self._handle_click(_get_coordinate(pg.mouse.get_pos()))
                elif event.type == pg.QUIT:
                    running = False

            pg.display.flip()

        pg.quit()

    def _handle_click(self, clicked_coordinate: Point):
        print(clicked_coordinate)
        if self._selected_square is None:
            self._enlighten_square(self._get_square(clicked_coordinate))
        else:
            self._make_move_callback(self._selected_square, self._get_square(clicked_coordinate))

    def _get_square(self, point: Point) -> SquareData:
        return self._squares[point.flat_integer()]

    def _enlighten_square(self, data: SquareData):
        piece, rect_object = data
        if piece is not None:
            self.draw_sprite(piece, rect_object)
        self.draw_rect(rect_object, self._action_square_color)

    def draw_sprite(self, piece: str, rect_object: pg.rect.Rect):
        sprite = self._sprites[piece]
        self._master.blit(sprite, sprite.get_rect(center=rect_object.center))

    def draw_rect(self, rect_object: pg.Rect, color: pg.Color) -> pg.rect.Rect:
        return pg.draw.rect(self._master, color, rect_object)

    def _create_rect(self, point: Point) -> pg.rect.Rect:
        def _get_color(square_number: int):
            return (self._white_square_color, self._black_square_color)[
                (-square_number - square_number // self._squares_per_side) % 2]

        print(point)
        rect_object = pg.Rect((point.x * self._square_side, point.y * self._square_side),
                              (self._square_side, self._square_side))
        r = self.draw_rect(rect_object, _get_color(point.flat_integer()))
        pg.display.flip()
        return r

    def _pintar_casillas(self, board: BoardRepresentation):
        for i, square_content in enumerate(board):
            rect = self._create_rect(Point.from_divmod(i))

            if square_content is not None:
                self.draw_sprite(square_content, rect)
            self._squares.append((square_content, rect))
