import os
import re
from collections.abc import Callable
from enum import Enum
from math import ceil, floor
from typing import TypedDict, NotRequired

from wcwidth import wcswidth, wcwidth

from mizue.printer import Alignment, BorderStyle, Printer
from mizue.util import Utility


class CellRendererArgs(TypedDict):
    cell: str
    formatter: Callable[[str, int], str]
    index: int
    is_header: bool
    width: int


ColumnRenderer = Callable[[CellRendererArgs], str]
"""The type of the column renderer function. The function takes the cell value, the column index and a boolean value"""


class ColumnSettings(TypedDict):
    alignment: NotRequired[Alignment]
    renderer: NotRequired[ColumnRenderer]
    title: str
    width: NotRequired[int]


class Column:
    def __init__(self, settings: ColumnSettings):
        self.alignment = settings["alignment"] if settings["alignment"] is not None else Alignment.LEFT
        self.index: int = 0
        self.renderer = settings["renderer"] if "renderer" in settings else None
        self.title = settings["title"] if "title" in settings else ""
        self.width = settings["width"] if "width" in settings else None


class Grid:
    def __init__(self, columns: list[ColumnSettings], data: list[list[str]]):
        self.border_color = None
        self.border_style = BorderStyle.BASIC
        self.columns = []
        self.data = data
        self.enumerated = False
        self._prepare_columns(columns)

    def print(self) -> None:
        """Print the grid"""
        print(self._buffer())

    def _buffer(self) -> str:
        buffer = [self._create_row_border(RowBorderPosition.TOP), os.linesep]
        title_list = [column.title for column in self.columns]
        buffer.append(self._create_row(title_list, True))
        buffer.append(os.linesep)
        buffer.append(self._create_row_border(RowBorderPosition.MIDDLE))
        buffer.append(os.linesep)
        for row in self.data:
            buffer.append(self._create_row(row, False))
            buffer.append(os.linesep)
        buffer.append(self._create_row_border(RowBorderPosition.BOTTOM))
        return "".join(buffer)

    def _create_row(self, row: list[str], is_header_row: bool) -> str:
        border_style = self._get_border_style()
        row_buffer = []
        if self.enumerated:
            header_text = "#" if is_header_row else str(self.data.index(row) + 1)
            row_buffer.append(f"{border_style.VERTICAL} ")
            row_buffer.append(self._get_left_cell_space(self.columns[0], str(self.data.index(row))))
            row_buffer.append(header_text)
            row_buffer.append(self._get_right_cell_space(self.columns[0], str(self.data.index(row))))
            row_buffer.append(" ")
            row_buffer.append(border_style.VERTICAL)
            row_buffer.append(" ")
        for index, cell in enumerate(row):
            column = self.columns[index]

            if column.renderer is not None:
                rendered_cell = column.renderer(CellRendererArgs(cell=cell, index=index, is_header=is_header_row,
                                                                 formatter=self._format_long_cell,
                                                                 width=column.width))

                rendered_cell = self._format_cell_with_colors(rendered_cell, column.width)
            else:
                rendered_cell = self._format_cell_with_colors(cell, column.width)

            border = Printer.format_hex(border_style.VERTICAL, self.border_color) \
                if self.border_color else border_style.VERTICAL
            if index == 0:
                row_buffer.append(f"{border}")

            row_buffer.append(" ")
            row_buffer.append(self._get_left_cell_space(column, self._get_raw_cell_text_after_rendering(rendered_cell)))
            row_buffer.append(rendered_cell)
            row_buffer.append(
                self._get_right_cell_space(column, self._get_raw_cell_text_after_rendering(rendered_cell)))
            row_buffer.append(" ")
            row_buffer.append(border)
        return "".join(row_buffer)

    def _format_cell_with_colors(self, rendered_cell: str, column_width: int) -> str:
        color_parts = self._extract_colors(rendered_cell)
        if len(color_parts) == 0:
            return self._format_long_cell(rendered_cell, column_width)
        else:
            processed_width = 0
            formatted_parts = []
            for color_part in color_parts:
                text = color_part[1]
                text_width = wcswidth(text)
                if processed_width + text_width <= column_width:
                    formatted_text = f"{color_part[0]}{text}{color_part[2]}"
                    formatted_parts.append(formatted_text)
                    processed_width += text_width
                    if processed_width == column_width:
                        break
                    print(formatted_text)
                else:
                    visible_text = self._format_long_cell(text, column_width - processed_width)
                    formatted_text = f"{color_part[0]}{visible_text}{color_part[2]}"
                    formatted_parts.append(formatted_text)
                    break
            return "".join(formatted_parts)

    def _create_row_border(self, position):
        dash_list = []
        border_style = self._get_border_style()
        if position is RowBorderPosition.TOP:
            left = border_style.TOPLEFT
            middle = border_style.TOPMIDDLE
            right = border_style.TOPRIGHT
        elif position is RowBorderPosition.BOTTOM:
            left = border_style.BOTTOMLEFT
            middle = border_style.BOTTOMMIDDLE
            right = border_style.BOTTOMRIGHT
        elif position is RowBorderPosition.MIDDLE:
            left = border_style.LEFTMIDDLE
            middle = border_style.MIDDLEMIDDLE
            right = border_style.RIGHTMIDDLE
        dash_list.append(left)
        for index, max_length in enumerate(list(map(lambda column: column.width, self.columns))):
            dash_list.append("".join([border_style.HORIZONTAL] * (max_length + 2)))
            if index != len(self.columns) - 1:
                dash_list.append(middle)
        dash_list.append(right)
        return Printer.format_hex("".join(dash_list), self.border_color) if self.border_color else "".join(dash_list)

    def _find_max_cell_width(self, column: Column) -> int:
        max_width = len(column.title)
        for row in self.data:
            cell = row[column.index]
            length = 0
            for char in cell:
                if Grid._is_wide_char(char):
                    length += 2
                else:
                    length += 1
            length = length + 1 if Grid._has_variation_selector(cell) else length
            max_width = max(max_width, length)
        return max_width

    @staticmethod
    def _format_long_cell(cell: str, col_width: int) -> str:
        if col_width <=3:
            if col_width == 1:
                return cell[0] if wcwidth(cell[0]) == 1 else "…"
            if col_width == 2:
                return cell[0] + cell[1] if wcwidth(cell[0]) == 1 and wcwidth(cell[1]) == 1 else "…"
            if col_width == 3:
                if wcwidth(cell[0]) == 2:
                    return cell[0] + "…"
                if wcwidth(cell[0]) == 1 and wcwidth(cell[1]) == 1:
                    return cell[0] + cell[1] + "…"
                if wcwidth(cell[0]) == 1 and wcwidth(cell[1]) == 2:
                    return "…"
                if wcwidth(cell[0]) == 1 and wcwidth(cell[1]) == 0:  # symbol + variation selector
                    return cell[0] + "…"

        text_width = 0
        text_length = 0
        for char in cell:
            text_length += 1
            if Grid._is_wide_char(char):
                text_width += 2
            else:
                text_width += 1
            if text_width == col_width - 3 or text_width == col_width - 2:
                break

        has_any_wide_char = any([True for char in cell if Grid._is_wide_char(char)])
        if not has_any_wide_char:
            if len(cell) <= col_width:
                return cell
            return cell[:col_width - 3] + "..."
        else:
            first_part = cell[:text_length]
            first_part_original = cell[:text_length]
            first_part_terminal_width = Grid._get_terminal_width_of_cell(first_part)
            full_width = Grid._get_terminal_width_of_cell(cell)
            while first_part_terminal_width > col_width - 3:
                first_part = first_part[:-1]
                first_part_terminal_width = Grid._get_terminal_width_of_cell(first_part)
            return first_part + "..." \
                if len(first_part) < len(first_part_original) or full_width > col_width \
                else first_part

    def _get_border_style(self):
        if self.border_style == BorderStyle.SINGLE:
            return BorderCharacterCodes.Single
        if self.border_style == BorderStyle.DOUBLE:
            return BorderCharacterCodes.Double
        if self.border_style == BorderStyle.BASIC:
            return BorderCharacterCodes.Basic
        if self.border_style == BorderStyle.EMPTY:
            return BorderCharacterCodes.Empty
        return BorderCharacterCodes.Basic

    @staticmethod
    def _get_left_cell_space(column: Column, cell: str) -> str:
        cell_terminal_width = Grid._get_terminal_width_of_cell(cell)
        if column.alignment == Alignment.RIGHT:
            return "".join([" "] * (column.width - cell_terminal_width))
        elif column.alignment == Alignment.CENTER:
            return "".join([" "] * int(floor((column.width - cell_terminal_width) / 2)))
        return ""

    @staticmethod
    def _get_raw_cell_text_after_rendering(rendered_cell: str) -> str:
        # remove all the color codes and other formatting codes, also remove ansi escape codes
        return re.sub(r"\x1b\[[0-9;]*m", "", rendered_cell)

    def _extract_colors(self, text: str) -> list[tuple[str, str, str]]:
        matcher = re.compile(r"(\x1b\[[0-9;]*m)(.*?)(\x1b\[00m)")
        groups = matcher.findall(text)
        return groups if groups else []

    @staticmethod
    def _get_right_cell_space(column: Column, cell: str) -> str:
        cell_terminal_width = Grid._get_terminal_width_of_cell(cell)
        if column.alignment == Alignment.LEFT:
            return "".join([" "] * (column.width - cell_terminal_width))
        elif column.alignment == Alignment.CENTER:
            return "".join([" "] * int(ceil((column.width - cell_terminal_width) / 2)))
        return ""

    @staticmethod
    def _get_terminal_width_of_cell(text):
        return sum([2 if wcswidth(char) == 2 else 1 for char in text])

    @staticmethod
    def _get_visible_text(text: str, max_width: int) -> str:
        current_width = 0
        for ch in text:
            if Grid._is_wide_char(ch):
                current_width += 2
            else:
                current_width += 1
            if current_width > max_width:
                return text[:text.index(ch)]
        return text


    @staticmethod
    def _has_variation_selector(text: str) -> bool:
        return any(Grid._is_variation_selector(c) for c in text)

    @staticmethod
    def _is_variation_selector(char: str) -> bool:
        return 0xFE00 <= ord(char) <= 0xFE0F

    @staticmethod
    def _is_wide_char(char: str) -> bool:
        return wcswidth(char) > 1

    def _prepare_columns(self, column_data: list[ColumnSettings]):
        columns: list[Column] = []
        if self.enumerated:
            columns.append(Column(
                settings=ColumnSettings(
                    alignment=Alignment.RIGHT,
                    title="#",
                    width=len(self.data)
                )
            ))
            columns[0].index = 0
        for i, column_setting in enumerate(column_data):
            column = Column(settings=column_setting)
            column.index = i
            column.width = column_setting["width"] if "width" in column_setting else self._find_max_cell_width(column)
            columns.append(column)
        self.columns = columns
        self._resize_columns_to_fit()

    def _resize_columns_to_fit(self):
        terminal_width = Utility.get_terminal_width()
        total_column_width = sum(column.width for column in self.columns)
        new_column_width = int(terminal_width / len(self.columns))
        short_columns = [column for column in self.columns if column.width < new_column_width]
        long_columns = [column for column in self.columns if column.width >= new_column_width]
        remaining_width = terminal_width - (new_column_width * len(short_columns) if len(short_columns) > 0 else 0)
        padding_width = int(floor(remaining_width / len(long_columns))) if len(long_columns) > 0 else 0

        if total_column_width > terminal_width:
            for cx in range(1, len(self.columns)):
                self.columns[cx].width = self.columns[cx].width \
                    if self.columns[cx].width < new_column_width else new_column_width + padding_width


class BorderCharacterCodes:
    class Double:
        TOPLEFT = u'\u2554'  # 0xC9 -> BOX DRAWINGS DOUBLE DOWN AND RIGHT
        TOPRIGHT = u'\u2557'  # 0xBB -> BOX DRAWINGS DOUBLE DOWN AND LEFT
        BOTTOMLEFT = u'\u255a'  # 0xC8 -> BOX DRAWINGS DOUBLE UP AND RIGHT
        BOTTOMRIGHT = u'\u255d'  # 0xBC -> BOX DRAWINGS DOUBLE UP AND LEFT
        TOPMIDDLE = u'\u2566'  # 0xCB -> BOX DRAWINGS DOUBLE DOWN AND HORIZONTAL
        BOTTOMMIDDLE = u'\u2569'  # 0xCA -> BOX DRAWINGS DOUBLE UP AND HORIZONTAL
        LEFTMIDDLE = u'\u2560'  # 0xCC -> BOX DRAWINGS DOUBLE VERTICAL AND RIGHT
        RIGHTMIDDLE = u'\u2563'  # 0xB9 -> BOX DRAWINGS DOUBLE VERTICAL AND LEFT
        MIDDLEMIDDLE = u'\u256c'  # 0xCE -> BOX DRAWINGS DOUBLE VERTICAL AND HORIZONTAL
        HORIZONTAL = u'\u2550'  # 0xCD -> BOX DRAWINGS DOUBLE HORIZONTAL
        VERTICAL = u'\u2551'  # 0xBA -> BOX DRAWINGS DOUBLE VERTICAL

    class Single:
        TOPLEFT = u'\u250c'  # 0xDA -> BOX DRAWINGS LIGHT DOWN AND RIGHT
        TOPRIGHT = u'\u2510'  # 0xBF -> BOX DRAWINGS LIGHT DOWN AND LEFT
        BOTTOMLEFT = u'\u2514'  # 0xC0 -> BOX DRAWINGS LIGHT UP AND RIGHT
        BOTTOMRIGHT = u'\u2518'  # 0xD9 -> BOX DRAWINGS LIGHT UP AND LEFT
        TOPMIDDLE = u'\u252c'  # 0xC2 -> BOX DRAWINGS LIGHT DOWN AND HORIZONTAL
        BOTTOMMIDDLE = u'\u2534'  # 0xC1 -> BOX DRAWINGS LIGHT UP AND HORIZONTAL
        LEFTMIDDLE = u'\u251c'  # 0xC3 -> BOX DRAWINGS LIGHT VERTICAL AND RIGHT
        RIGHTMIDDLE = u'\u2524'  # 0xB4 -> BOX DRAWINGS LIGHT VERTICAL AND LEFT
        MIDDLEMIDDLE = u'\u253c'  # 0xC5 -> BOX DRAWINGS LIGHT VERTICAL AND HORIZONTAL
        HORIZONTAL = u'\u2500'  # 0xC4 -> BOX DRAWINGS LIGHT HORIZONTAL
        VERTICAL = u'\u2502'  # 0xB3 -> BOX DRAWINGS LIGHT VERTICAL

    class Basic:
        TOPLEFT = "+"
        TOPRIGHT = "+"
        BOTTOMLEFT = "+"
        BOTTOMRIGHT = "+"
        TOPMIDDLE = "+"
        BOTTOMMIDDLE = "+"
        LEFTMIDDLE = "+"
        RIGHTMIDDLE = "+"
        MIDDLEMIDDLE = "+"
        HORIZONTAL = "-"
        VERTICAL = "|"

    class Empty:
        TOPLEFT = ""
        TOPRIGHT = ""
        BOTTOMLEFT = ""
        BOTTOMRIGHT = ""
        TOPMIDDLE = ""
        BOTTOMMIDDLE = ""
        LEFTMIDDLE = ""
        RIGHTMIDDLE = ""
        MIDDLEMIDDLE = ""
        HORIZONTAL = ""
        VERTICAL = ""


class RowBorderPosition(Enum):
    TOP = 1,
    MIDDLE = 2,
    BOTTOM = 3
