from collections.abc import Callable
from typing import TypedDict, NotRequired

from mizue.printer.grid import Alignment, CellRendererArgs


class ColumnSettings(TypedDict):
    alignment: NotRequired[Alignment]
    renderer: NotRequired[Callable[[CellRendererArgs], str]]
    title: str
    width: NotRequired[int]
    wrap: NotRequired[bool]
