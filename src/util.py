import os
import sys
from collections.abc import Iterator
from typing import Iterable, MutableSequence, Generator, Callable, Type

from aenum import Enum
from makefun import wraps


def is_inbound(x: int, y: int) -> bool:
    return 0 <= y <= 7 and 0 <= x <= 7


def extract_attribute(it: Iterable, attrs: list[str], iterable_type: type) -> Type[MutableSequence] | Type[Generator]:
    iter_obj = (tuple(getattr(obj, attr) for attr in attrs) for obj in it)
    if issubclass(iterable_type, Iterator):
        obj = iter_obj
    elif issubclass(iterable_type, MutableSequence):
        obj = iterable_type()
        for i, a in enumerate(iter_obj):
            obj.insert(i, a)

        return obj
    else:
        raise TypeError

    return obj


def decorator_bool_enum(fn: Callable):
    @wraps(fn)
    def inner(self: Enum, other: Enum | bool):
        if isinstance(other, bool):
            return self.value == other
        return fn(self, other)


def return_extracting(attr: str, iterable_type: type):
    def decorator(fn: Callable):
        @wraps(fn)
        def inner(*args, **kwargs) -> Iterable:
            return extract_attribute(fn(*args, **kwargs), attr, iterable_type)

        return decorator

    return return_extracting


pattern = r'debug\((.*)\)'
separator = '_' * 20


def getpath():
    if getattr(sys, 'frozen', False):
        # If the application is run as a bundle, the PyInstaller bootloader
        # extends the sys module by a flag frozen=True and sets the app
        # path into variable _MEIPASS'.
        application_path = getattr(sys, '_MEIPASS')
    else:
        application_path = os.path.dirname(os.path.abspath(__file__))

    return application_path


def get_sprite_filename() -> str:
    return getpath() + '/resources/sprites.png'


def get_font_filename() -> str:
    return getpath() + '/resources/seguisym.ttf'


def get_games_db_filename() -> str:
    return getpath() + '/resources/lichess_db_202gb.pgn'


def safe_division(y: int, x: int):
    try:
        return y / x
    except ArithmeticError:
        return 0


def safe_truedivision(y: int, x: int):
    try:
        return y // x
    except ArithmeticError:
        return 0


def from_san_to_int(algebraic_notation: str) -> int:
    col, row = algebraic_notation
    return ord(col) - 97 + (int(row) - 1) * 8


def from_int_to_san(square: int) -> str:
    row, column = divmod(square, 8)
    return chr(column + 90) + str(row)
