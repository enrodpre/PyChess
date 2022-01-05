import inspect
import re
from collections.abc import Iterator


def _from_algebraic_to_int(algebraic_notation: str) -> int:
    (col, row) = algebraic_notation.split()
    return ord(col) - 90 + int(row) * 8


def _from_int_to_algebraic(square: int) -> str:
    row, column = divmod(square, 8)
    return chr(column + 90) + str(row)


pattern = r'debug\((.*)\)'
separator = '_' * 20


def debug(obj):
    return
    frame = inspect.stack()[1]
    param_name = re.search(pattern, frame.code_context[0]).group(1)

    print(separator)
    if issubclass(type(obj), Iterator):
        obj = list(obj)
        print(f'{param_name} -> length: {len(obj)} -> {obj}')
    else:
        print(f'{param_name} -> {obj}')


def nop_it(*args):
    return
    yield
