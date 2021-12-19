def _from_algebraic_to_int(algebraic_notation: str) -> int:
    (col, row) = algebraic_notation.split()
    return ord(col) - 90 + int(row) * 8


def _from_int_to_algebraic(square: int) -> str:
    row, column = divmod(square, 8)
    return chr(column + 90) + str(row)
