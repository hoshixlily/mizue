import os
import re
from math import ceil, floor
from typing import Callable

from wcwidth import wcswidth, wcwidth

from mizue.printer import Printer
from mizue.util import Utility
from .alignment import Alignment
from .border_character_codes import BorderCharacterCodes
from .border_style import BorderStyle
from .cell_renderer_args import CellRendererArgs
from .column import Column
from .column_settings import ColumnSettings
from .row_border_position import RowBorderPosition


class Grid:
    def __init__(self, columns: list[ColumnSettings], data: list[list[str]]):
        self.border_color = None
        self.border_style = BorderStyle.BASIC
        self.cell_renderer: Callable[[CellRendererArgs], str] = lambda args: Grid._get_default_cell_renderer(args)
        self.columns = []
        self.data = data
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
        for index, cell_value in enumerate(row):
            cell = str(cell_value)
            column = self.columns[index]

            renderer = self._get_cell_renderer(column)
            if renderer is not None:
                rendered_cell = renderer(CellRendererArgs(cell=cell, index=index, is_header=is_header_row,
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
        else:
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
            cell = str(row[column.index])
            length = 0
            for char in str(cell):
                if Grid._is_wide_char(char):
                    length += 2
                else:
                    length += 1
            length = length + 1 if Grid._has_variation_selector(cell) else length
            max_width = max(max_width, length)
        return max_width

    def _format_cell_with_colors(self, rendered_cell: str, column_width: int) -> str:
        color_parts = self._split_text_into_color_parts(rendered_cell)
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
                else:
                    visible_text = self._format_long_cell(text, column_width - processed_width)
                    formatted_text = f"{color_part[0]}{visible_text}{color_part[2]}"
                    formatted_parts.append(formatted_text)
                    break
            return "".join(formatted_parts)

    @staticmethod
    def _format_long_cell(cell: str, col_width: int) -> str:
        if col_width <= 3:
            if col_width == 1:
                return cell[0] if wcwidth(cell[0]) == 1 else "…"
            if col_width == 2:
                if len(cell) == 1:
                    return cell[0] if wcwidth(cell[0]) == 1 else "…"
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
            return cell[:col_width - 1] + "…"
        else:
            first_part = cell[:text_length]
            first_part_original = cell[:text_length]
            first_part_terminal_width = Grid._get_terminal_width_of_cell(first_part)
            full_width = Grid._get_terminal_width_of_cell(cell)
            while first_part_terminal_width > col_width - 1:
                first_part = first_part[:-1]
                first_part_terminal_width = Grid._get_terminal_width_of_cell(first_part)
            return first_part + "…" \
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

    def _get_cell_renderer(self, column: Column):
        if column.renderer:
            return column.renderer
        return self.cell_renderer

    @staticmethod
    def _get_default_cell_renderer(args: CellRendererArgs) -> str:
        if args.is_header:
            return Printer.format_hex(args.cell, '#FFCC75')
        return args.cell

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
        for i, column_setting in enumerate(column_data):
            column = Column(settings=column_setting)
            column.index = i
            column.width = column_setting["width"] if "width" in column_setting else self._find_max_cell_width(column)
            columns.append(column)
        self.columns = columns
        self._resize_columns_to_fit()

    def _resize_columns_to_fit2(self):
        terminal_width = Utility.get_terminal_width()
        total_column_width = sum(column.width for column in self.columns)
        if total_column_width > terminal_width:
            for cx in range(0, len(self.columns)):
                self.columns[cx].width = int((terminal_width * self.columns[cx].width) / total_column_width) - 4

    def _resize_columns_to_fit(self):
        terminal_width = Utility.get_terminal_width()
        new_column_width = int(terminal_width / len(self.columns))
        long_columns = [column for column in self.columns if column.width >= new_column_width]

        remaining_width = 0
        for column in self.columns:
            if column.width > new_column_width:
                column.width = new_column_width
            else:
                remaining_width += (new_column_width - column.width - 4 * len(self.columns))

        padding = int(remaining_width / len(long_columns)) if len(long_columns) > 0 else 0
        for column in long_columns:
            column.width += padding

    @staticmethod
    def _split_text_into_color_parts(text: str) -> list[tuple[str, str, str]]:
        matcher = re.compile(r"(\x1b\[[0-9;]*m)(.*?)(\x1b\[00m)")
        groups = matcher.findall(text)
        return groups if groups else []
