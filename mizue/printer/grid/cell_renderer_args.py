from collections.abc import Callable
from typing import TypedDict


class CellRendererArgs(TypedDict):
    cell: str
    formatter: Callable[[str, int], str]
    index: int
    is_header: bool
    width: int
