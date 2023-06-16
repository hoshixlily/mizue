from dataclasses import dataclass


@dataclass
class CellRendererArgs:
    cell: str
    index: int
    is_header: bool
    width: int
