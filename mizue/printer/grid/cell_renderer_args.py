from typing import TypedDict


class CellRendererArgs(TypedDict):
    cell: str
    index: int
    is_header: bool
    width: int
