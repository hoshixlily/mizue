from typing import Final
from abc import ABC


class BorderCharacterCodes(ABC):
    class Double(ABC):
        TOPLEFT: Final[str] = u'\u2554'  # 0xC9 -> BOX DRAWINGS DOUBLE DOWN AND RIGHT
        TOPRIGHT: Final[str] = u'\u2557'  # 0xBB -> BOX DRAWINGS DOUBLE DOWN AND LEFT
        BOTTOMLEFT: Final[str] = u'\u255a'  # 0xC8 -> BOX DRAWINGS DOUBLE UP AND RIGHT
        BOTTOMRIGHT: Final[str] = u'\u255d'  # 0xBC -> BOX DRAWINGS DOUBLE UP AND LEFT
        TOPMIDDLE: Final[str] = u'\u2566'  # 0xCB -> BOX DRAWINGS DOUBLE DOWN AND HORIZONTAL
        BOTTOMMIDDLE: Final[str] = u'\u2569'  # 0xCA -> BOX DRAWINGS DOUBLE UP AND HORIZONTAL
        LEFTMIDDLE: Final[str] = u'\u2560'  # 0xCC -> BOX DRAWINGS DOUBLE VERTICAL AND RIGHT
        RIGHTMIDDLE: Final[str] = u'\u2563'  # 0xB9 -> BOX DRAWINGS DOUBLE VERTICAL AND LEFT
        MIDDLEMIDDLE: Final[str] = u'\u256c'  # 0xCE -> BOX DRAWINGS DOUBLE VERTICAL AND HORIZONTAL
        HORIZONTAL: Final[str] = u'\u2550'  # 0xCD -> BOX DRAWINGS DOUBLE HORIZONTAL
        VERTICAL: Final[str] = u'\u2551'  # 0xBA -> BOX DRAWINGS DOUBLE VERTICAL

    class Single(ABC):
        TOPLEFT: Final[str] = u'\u250c'  # 0xDA -> BOX DRAWINGS LIGHT DOWN AND RIGHT
        TOPRIGHT: Final[str] = u'\u2510'  # 0xBF -> BOX DRAWINGS LIGHT DOWN AND LEFT
        BOTTOMLEFT: Final[str] = u'\u2514'  # 0xC0 -> BOX DRAWINGS LIGHT UP AND RIGHT
        BOTTOMRIGHT: Final[str] = u'\u2518'  # 0xD9 -> BOX DRAWINGS LIGHT UP AND LEFT
        TOPMIDDLE: Final[str] = u'\u252c'  # 0xC2 -> BOX DRAWINGS LIGHT DOWN AND HORIZONTAL
        BOTTOMMIDDLE: Final[str] = u'\u2534'  # 0xC1 -> BOX DRAWINGS LIGHT UP AND HORIZONTAL
        LEFTMIDDLE: Final[str]= u'\u251c'  # 0xC3 -> BOX DRAWINGS LIGHT VERTICAL AND RIGHT
        RIGHTMIDDLE: Final[str] = u'\u2524'  # 0xB4 -> BOX DRAWINGS LIGHT VERTICAL AND LEFT
        MIDDLEMIDDLE: Final[str] = u'\u253c'  # 0xC5 -> BOX DRAWINGS LIGHT VERTICAL AND HORIZONTAL
        HORIZONTAL: Final[str] = u'\u2500'  # 0xC4 -> BOX DRAWINGS LIGHT HORIZONTAL
        VERTICAL: Final[str] = u'\u2502'  # 0xB3 -> BOX DRAWINGS LIGHT VERTICAL

    class Basic(ABC):
        TOPLEFT: Final[str] = "+"
        TOPRIGHT: Final[str] = "+"
        BOTTOMLEFT: Final[str] = "+"
        BOTTOMRIGHT: Final[str] = "+"
        TOPMIDDLE: Final[str] = "+"
        BOTTOMMIDDLE: Final[str] = "+"
        LEFTMIDDLE: Final[str] = "+"
        RIGHTMIDDLE: Final[str] = "+"
        MIDDLEMIDDLE: Final[str] = "+"
        HORIZONTAL: Final[str] = "-"
        VERTICAL: Final[str] = "|"

    class Empty(ABC):
        TOPLEFT: Final[str] = ""
        TOPRIGHT: Final[str] = ""
        BOTTOMLEFT: Final[str] = ""
        BOTTOMRIGHT: Final[str] = ""
        TOPMIDDLE: Final[str] = ""
        BOTTOMMIDDLE: Final[str] = ""
        LEFTMIDDLE: Final[str] = ""
        RIGHTMIDDLE: Final[str] = ""
        MIDDLEMIDDLE: Final[str] = ""
        HORIZONTAL: Final[str] = ""
        VERTICAL: Final[str] = ""
