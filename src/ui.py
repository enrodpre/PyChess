from enum import Enum
from enum import auto
from time import time
from typing import Optional, Iterator, Iterable

import pygame as pg

from model import Slot, Moves, GameState, Color, Piece, Board, Point, InvalidStateError, PieceType, Move  # type: ignore
from util import get_sprite_filename, get_font_filename

pg.init()
pg.font.init()

UNICODE_CHARACTERS = ('♚', '♛', '♜', '♞', '♝', '♟︎', '♔', '♕', '♖', '♘', '♗', '♙')

Surface = pg.surface.Surface
SpritesData = dict[str, Surface]


class Rect(pg.rect.Rect):
    def __iter__(self):
        yield self.top
        yield self.left
        yield self.width
        yield self.height


class SpritesMode(Enum):
    UNICODE = 0
    CLASSIC = 1


def translate(x: int) -> int:
    return Slot.fromflat(x).reverse().flat()


def map_pieces(pieces_sprites: Iterator[Surface]) -> dict[str, Surface]:
    return dict(zip('kqrnbpKQRNBP', pieces_sprites))


def load_sprites(filename: str) -> Iterator[Surface]:
    sheet = pg.image.load(filename)

    num_rows, num_cols = 2, 6
    x_margin, x_padding, y_margin, y_padding = 0, 0, 0, 0  # 64, 72, 68, 48
    sheet_rect = sheet.get_rect()
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

    return (sheet.subsurface(rect).convert_alpha() for rect in sprite_rects)


sprite_filename = get_sprite_filename()

# configuration
square_side: float = 70
offset = (5 + (square_side // 2), (square_side // 2))
offset_x, offset_y = offset
space_between_squares = 6
half_space = space_between_squares / 2

window_resolution: tuple[float, float] = (640, 640)
background_color = pg.Color('grey')
white_square_color = pg.Color('yellow')
black_square_color = pg.Color('brown')
action_square_color = pg.Color('Blue')
boardside_characters_color = pg.Color('black')
squares_per_side = 8
chosen_sprites = SpritesMode.CLASSIC
FPS = 60

CoordinatesUI = Iterator[tuple[int, Surface]]
unicode_pieces_renderer = pg.font.Font(get_font_filename(), 70)
ui_characters_renderer = pg.font.Font(get_font_filename(), 40)
variable_descriptor_renderer = pg.font.Font(get_font_filename(), 20)


def get_unicode_sprites() -> Iterator[Surface]:
    return (unicode_pieces_renderer.render(char, True, pg.Color('Black')) for char in UNICODE_CHARACTERS)


def load_columns_ui() -> CoordinatesUI:
    for c_i in range(8):
        column_char = chr(c_i + 97)
        yield c_i, ui_characters_renderer.render(column_char, True, boardside_characters_color)


def load_rows_ui() -> CoordinatesUI:
    for r_i in range(8):
        yield 7 - r_i, ui_characters_renderer.render(str(r_i + 1), True, boardside_characters_color)


def load_fake_columns_ui() -> CoordinatesUI:
    for c_i in range(8):
        yield c_i, ui_characters_renderer.render(str(c_i), True, boardside_characters_color)


def load_fake_rows_ui() -> CoordinatesUI:
    for r_i in range(8):
        yield 7 - r_i, ui_characters_renderer.render(str(r_i), True, boardside_characters_color)


def load_boardsides() -> tuple[CoordinatesUI, CoordinatesUI]:
    return load_rows_ui(), load_columns_ui()


def get_square_color(square_number: int):
    return (white_square_color, black_square_color)[
        (-square_number - square_number // squares_per_side) % 2]


square_width = square_side - space_between_squares
square_height = square_side - space_between_squares
square_dimensions = (square_width, square_height)
square_top = square_side + offset_y
square_left = square_side + offset_x


def get_square_descriptor(i: int) -> tuple[float, float, float, float]:
    y, x = divmod(i, squares_per_side)

    left, top = (square_side, square_side)

    left *= x
    top *= y

    half = space_between_squares / 2
    left = left + half + offset_x
    top = top + half + offset_y

    square_descriptor = (left, top, square_width, square_height)

    return square_descriptor


def get_sprites() -> SpritesData:
    if chosen_sprites == SpritesMode.UNICODE:
        sprites = get_unicode_sprites()
    else:
        sprites = load_sprites(sprite_filename)
    return map_pieces(sprites)


GraphicalPiece = tuple[Piece, Surface]


class UiState(Enum):
    IDLE = auto()
    PIECE_SELECTED = auto()
    PROMOTING = auto()


def sum_rects(*rects: Rect) -> Rect:
    f, *rects = rects
    return f.copy().unionall(rects)


class GraphicalSquare:
    master: Surface
    rect: Rect
    surface: Surface
    content: Optional[GraphicalPiece]
    true_color: pg.Color
    momentary_color: Optional[pg.Color]
    slot: Slot

    def __init__(self, master: Surface, rect: Rect, color: pg.Color, slot: Slot):
        self.master = master
        self.rect = rect
        self.surface = master.copy().subsurface(rect)
        self.content = None
        self.true_color = color
        self.momentary_color = None
        self.slot = slot
        self.ui_state = UiState.IDLE

    def __iter__(self):
        yield self.rect
        yield self.content
        yield self.true_color

    @classmethod
    def create(cls, i: int):
        return GraphicalSquare(pg.display.get_surface(), Rect(*get_square_descriptor(i)), get_square_color(i),
                               Slot.fromflat(i).reverse())

    def enlighten(self, color: pg.Color):
        self.momentary_color = color

    def darken(self):
        self.momentary_color = None

    def update(self) -> None:
        if self.momentary_color is None:
            color = self.true_color
        else:
            color = self.momentary_color

        self.surface.fill(color)
        self.master.blit(self.surface, self.rect)

        if self.content is not None:
            _, sprite = self.content
            self.master.blit(sprite, self.rect)


GraphicalSquares = list[GraphicalSquare]


class GraphicalBoard:
    squares: GraphicalSquares
    rect: Rect
    sprites: SpritesData
    selected_square: Optional[GraphicalSquare]
    lit_squares: GraphicalSquares

    def __init__(self):
        self.squares = list(GraphicalSquare.create(i) for i in range(64))
        self.rect = sum_rects(*(s.rect for s in self.squares))
        self.sprites = get_sprites()
        self.selected_square = None
        self.lit_squares = []

    def get_square(self, pos: int) -> GraphicalSquare:
        return self.squares[translate(pos)]

    def select_square(self, selected: Slot) -> None:
        self.selected_square = self.get_square(selected.flat())

    def update(self):
        for square_pos in range(64):
            self.get_square(square_pos).update()

    def update_data(self, board: Board):
        for position, piece in enumerate(board):
            square = self.get_square(position)
            content = None
            if piece is not None:
                content = (piece, self.sprites[piece.representation])
            square.content = content

    def unselect_square(self):
        for lit_square in self.lit_squares:
            lit_square.darken()
        self.lit_squares = []
        self.selected_square = None

    def enlighten_squares(self, points: Iterator[Slot]):
        for p in points:
            square_to_be_lit = self.get_square(p.flat())
            square_to_be_lit.enlighten(action_square_color)
            self.lit_squares.append(square_to_be_lit)

    def search_square(self, point: Point) -> Optional[GraphicalSquare]:
        for s in self.squares:
            if s.rect.collidepoint(*point):
                return s


def get_y_axis_direction_promoting_menu(color: Color) -> int:
    return color.direction() * -1


class PromotingMenuSquare(pg.sprite.Sprite):
    background: Surface
    image: Surface
    rect: Rect
    piece: Piece

    def __init__(self, piece: Piece, image: Surface, rect: Rect):
        super().__init__()
        self.piece = piece
        surface = Surface(image.get_rect().size)
        surface.fill(pg.Color('white'))
        self.background = surface
        self.image = image
        self.rect = rect

    def values(self) -> tuple[Surface, Surface, Rect, Piece]:
        return self.background, self.image, self.rect, self.piece


def create_promoting_menu_data_per_color(color: Color, sprites_data: SpritesData) -> pg.sprite.Group:
    possible_types = (PieceType.QUEEN, PieceType.ROOK, PieceType.BISHOP, PieceType.KNIGHT)
    possible_pieces = tuple(Piece(color, t) for t in possible_types)
    promoting_menu_group = pg.sprite.Group()
    for i, p in enumerate(possible_pieces):
        promoting_sprite = PromotingMenuSquare(p, sprites_data[p.representation],
                                               Rect(square_side * i,
                                                    square_side,
                                                    square_side,
                                                    square_side))
        promoting_menu_group.add(promoting_sprite)

    return promoting_menu_group


class PromotingMenu:
    white_promoting_data: pg.sprite.Group
    black_promoting_data: pg.sprite.Group
    active_color: Color
    slot: Slot

    def __init__(self, master: Surface, sprites: SpritesData):
        self.master = master
        self.white_promoting_data = create_promoting_menu_data_per_color(Color.WHITE, sprites)
        self.black_promoting_data = create_promoting_menu_data_per_color(Color.BLACK, sprites)

    def get_promoting_data(self) -> Iterable[PromotingMenuSquare]:
        if self.active_color is Color.WHITE:
            return self.white_promoting_data
        else:
            return self.black_promoting_data

    def configure(self, slot: Slot, color: Color) -> None:
        x, y = slot * get_y_axis_direction_promoting_menu(color)
        self.slot = slot
        self.active_color = color
        for sprite in self.get_promoting_data():
            pass  # sprite.rect.move(x, y)

    def get_clicked_type(self, point: Point) -> Optional[tuple[Slot, Piece]]:
        for promoting_square in self.get_promoting_data():
            if promoting_square.rect.collidepoint(*point):
                return self.slot, promoting_square.piece

    def draw(self, master: Surface):
        outter_rect = sum_rects(*(s.rect for s in self.get_promoting_data()))
        background = Surface(outter_rect.size)
        background.fill(pg.Color('black'))
        master.blit(background, outter_rect)
        for sprite in self.get_promoting_data():
            img_background, image, rect, piece = sprite.values()
            master.blit(img_background, img_background.get_rect(center=rect.center))
            master.blit(image, image.get_rect(center=rect.center))


class Controller:
    ui_state: UiState
    master: pg.Surface
    graphical_board: GraphicalBoard
    posible_movements: Moves
    game_state: GameState
    ui_objects: list[tuple[Surface, Rect]]

    promoting_menus: PromotingMenu

    def __init__(self, board: GameState):
        self.game_state = board

    def initialize(self):
        self.master = pg.display.set_mode(window_resolution, pg.SRCALPHA)
        self.graphical_board = GraphicalBoard()
        self.promoting_menus = PromotingMenu(self.master, self.graphical_board.sprites)
        self.ui_objects = list(self.create_ui())
        self.ui_state = UiState.IDLE

    def start_turn(self, posible_movements: Moves, timeout: Optional[int | float] = None) -> Move:
        self.posible_movements = posible_movements
        # pprint.pp(posible_movements)
        self.update_data()

        return self.start_main_loop(timeout)

    def update_data(self):
        self.graphical_board.update_data(self.game_state.board)

    def create_ui(self) -> Iterator[tuple[Surface, Rect]]:
        row_surfaces, column_surfaces = load_boardsides()
        x: float
        y: float
        width: float
        height: float
        x, y, width, height = self.graphical_board.squares[0].rect
        new_x = x - (square_side * 3 / 4)
        new_y = y + (square_side * 8) - 5

        for row_i, row_surface in row_surfaces:
            yield row_surface, Rect((new_x, (square_side * row_i) + y), (width, height))

        for column_i, column_surface in column_surfaces:
            yield column_surface, Rect((x + (column_i * square_side), new_y), (width, height / 2))

    def update(self):
        self.master.fill(background_color)
        self.graphical_board.update()
        self.draw_ui()
        pg.display.flip()

    def draw_ui(self):
        for ui_obj in self.ui_objects:
            surface, rect = ui_obj
            self.master.blit(surface, surface.get_rect(center=rect.center))

        if self.ui_state is UiState.PROMOTING:
            self.promoting_menus.draw(self.master)

    def start_main_loop(self, timeout: Optional[float | int] = None) -> Move:
        while True:
            clicked_point = self.loop(timeout)
            ret = self.handle_click(clicked_point) if clicked_point is not None else None
            if ret is not None:
                return ret

    def loop(self, timeout: Optional[float | int] = None) -> Point:
        running = True
        timer = time()
        while running:
            for event in pg.event.get():
                if event.type == pg.MOUSEBUTTONDOWN:
                    left_is_clicked, *_ = pg.mouse.get_pressed()
                    if left_is_clicked:
                        return Point(*pg.mouse.get_pos())
                elif event.type == pg.QUIT:
                    running = False

            if timeout is not None and time() - timer > timeout:
                break
            self.update()

    def handle_click(self, raw_point: Point) -> Optional[Move]:
        if not self.graphical_board.rect.collidepoint(*raw_point):
            return None
        clicked_square = self.graphical_board.search_square(raw_point)
        if clicked_square is None:
            return None
        square_slot, content = clicked_square.slot, clicked_square.content

        if self.ui_state == UiState.IDLE:
            if content is not None and self.game_state.next_to_move is content[0].color:
                self.graphical_board.selected_square = clicked_square
                squares_to_be_lit = self.posible_movements.from_start(square_slot)
                if len(squares_to_be_lit) > 0:
                    self.graphical_board.enlighten_squares(squares_to_be_lit)
                    self.ui_state = UiState.PIECE_SELECTED
        elif self.ui_state == UiState.PIECE_SELECTED:
            selected_square = self.graphical_board.selected_square
            if selected_square is None:
                raise InvalidStateError
            self.graphical_board.unselect_square()
            move = self.posible_movements.search_move(selected_square.slot, square_slot)
            self.ui_state = UiState.IDLE
            if move is not None:
                return move
        else:
            raise InvalidStateError
        return None

    def show_promote_menu(self, slot: Slot, color: Color) -> Optional[tuple[Slot, Piece]]:
        self.ui_state = UiState.PROMOTING
        self.promoting_menus.configure(slot, color)
        while True:
            clicked_point = self.loop()
            if not (promoting_data := self.promoting_menus.get_clicked_type(clicked_point)):
                continue
            self.ui_state = UiState.IDLE
            return promoting_data
