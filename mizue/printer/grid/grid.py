import itertools
import os
import re
import textwrap
from math import ceil, floor
from typing import Callable

from wcwidth import wcswidth, wcwidth

from mizue.printer import Printer, TerminalColors
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
        self._columns = []
        self.border_color = None
        self.border_style = BorderStyle.BASIC
        self.cell_renderer: Callable[[CellRendererArgs], str] = lambda args: Grid._get_default_cell_renderer(args)
        self.data = data
        self.separated_rows = False
        if len(columns) > 0:
            self._prepare_columns(columns)

    @property
    def columns(self) -> list[Column]:
        return self._columns

    @columns.setter
    def columns(self, value: list[ColumnSettings]) -> None:
        self._prepare_columns(value)

    def fill_screen(self):
        terminal_width = Utility.get_terminal_width()
        total_width = sum([column.width for column in self.columns]) + (4 * len(self.columns))
        if total_width < terminal_width:
            remaining_width = terminal_width - sum([column.width for column in self.columns]) - (4 * len(self.columns))
            for column in self.columns:
                column.width += int(remaining_width / len(self.columns))

    def print(self) -> None:
        """Print the grid"""
        print(self._buffer())

    def _buffer(self) -> str:
        buffer = [self._create_row_border(RowBorderPosition.TOP), os.linesep]
        title_list = [column.title for column in self.columns]
        buffer.append(self._create_row(title_list, True, False)[0])
        buffer.append(os.linesep)
        buffer.append(self._create_row_border(RowBorderPosition.MIDDLE))
        buffer.append(os.linesep)
        for row_index, row in enumerate(self.data):
            rendered_row, rendered_cells = self._create_row(row, False, True)
            for index, cell in enumerate(rendered_cells):
                row[index] = cell
            row_with_offset_rows = Grid._get_multiline_cell_offset_rows(row)
            for offset_row in row_with_offset_rows:
                offset_row = [Grid._replace_tabs(str(cell)) for cell in offset_row]
                buffer.append(self._create_row(offset_row, False, False)[0])
                buffer.append(os.linesep)
            if self.separated_rows and row_index != len(self.data) - 1:
                buffer.append(self._create_row_border(RowBorderPosition.MIDDLE))
                buffer.append(os.linesep)
        buffer.append(self._create_row_border(RowBorderPosition.BOTTOM))
        return "".join(buffer)

    def _create_row(self, row: list[str], is_header_row: bool, wrap: bool) -> (str, list[str]):
        border_style = self._get_border_style()
        row_buffer = []
        rendered_cells: list[str] = []
        for index, cell_value in enumerate(row):
            cell = str(cell_value)
            column = self.columns[index]

            wide_char_count = sum([1 for char in cell if Grid._is_wide_char(char)])
            renderer = self._get_cell_renderer(column)
            width = column.width - wide_char_count
            rendered_cell = renderer(CellRendererArgs(cell=cell, index=index, is_header=is_header_row,
                                                      width=width))
            wrapped_cell = Grid._split_string_keep_rgb_colors(rendered_cell, width) \
                if wrap and column.wrap else [cell]
            colored_cells = []
            if renderer is not None:
                for wrapped_cell_part in wrapped_cell:
                    rendered_cell_parts = renderer(CellRendererArgs(cell=wrapped_cell_part, index=index, is_header=is_header_row,
                                                              width=column.width))
                    rendered_cell_parts = self._format_cell_with_colors(rendered_cell_parts, column.width) \
                        if not (wrap or column.wrap) else rendered_cell_parts
                    colored_cells.append(rendered_cell_parts)
            else:
                for wrapped_cell_part in wrapped_cell:
                    rendered_cell_parts = self._format_cell_with_colors(wrapped_cell_part, column.width) \
                        if not (wrap or column.wrap) else wrapped_cell_part
                    colored_cells.append(rendered_cell_parts)

            border = Printer.format_hex(border_style.VERTICAL, self.border_color) \
                if self.border_color else border_style.VERTICAL
            if index == 0:
                row_buffer.append(f"{border}")

            rendered_cell = os.linesep.join(colored_cells)

            rendered_cells.append(rendered_cell)
            row_buffer.append(" ")
            row_buffer.append(self._get_left_cell_space(column, self._get_raw_cell_text_after_rendering(rendered_cell)))
            row_buffer.append(rendered_cell)
            row_buffer.append(
                self._get_right_cell_space(column, self._get_raw_cell_text_after_rendering(rendered_cell)))
            row_buffer.append(" ")
            row_buffer.append(border)
        return "".join(row_buffer), rendered_cells

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
            for cx, color_part in enumerate(color_parts):
                text = color_part[1]
                text_width = wcswidth(text)
                if processed_width + text_width <= column_width:
                    if processed_width + text_width == column_width:
                        text = text[:-1] + "…" if Grid._is_wide_char(text[-1]) else text
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
                if len(cell) == 1:
                    return cell[0] if wcwidth(cell[0]) == 1 else "…"
                return "…" if wcwidth(cell[0]) == 1 else "…"
            if col_width == 2:
                if len(cell) == 1:
                    return cell[0] if wcwidth(cell[0]) == 1 else "…"
                if len(cell) == 2:
                    return cell[0] + cell[1] if wcwidth(cell[0]) == 1 and wcwidth(cell[1]) == 1 else "…"
                return "…" if wcwidth(cell[0]) == 1 else "…"
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
    def _get_line_count(text: str) -> int:
        return len(text.splitlines())

    @staticmethod
    def _get_multiline_cell_offset_rows(row: list[str]) -> list[list[str]]:
        rows: list[list[str]] = []
        row_lines = map(lambda cell: cell.splitlines(), row)
        max_line_count = max(map(lambda lines: len(lines), row_lines))
        for i in range(max_line_count):
            rows.append([])
        for cell in row:
            lines = cell.splitlines()
            for i in range(max_line_count):
                if i < len(lines):
                    rows[i].append(lines[i])
                else:
                    rows[i].append("")
        return rows

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
    def _has_multiline_cell(row: list[str]):
        return any(Grid._get_line_count(str(cell)) > 1 for cell in row)

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
        self._columns = columns
        # self._resize_columns_to_fit()

    @staticmethod
    def _replace_tabs(text: str) -> str:
        return text.replace("\t", "    ")

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
    def _split_string_keep_rgb_colors(input_string: str, line_length: int) -> list[str]:
        """Splits a string into multiple lines, keeping the rgb colors intact."""
        if line_length <= 0:
            raise ValueError("The line length must be greater than zero")
        if line_length == 1:
            return list(input_string)
        if line_length >= len(input_string):
            return [input_string]

        parts = Grid._split_text_into_color_parts(input_string)
        if len(parts) == 0:
            return textwrap.wrap(input_string, line_length)

        dict = {}
        for px, part in enumerate(parts):
            dict[px] = (part[0], part[1], part[2])

        dx = 0
        line = ""
        colored_line_data = []
        line_group = 0
        diff = 0
        while dx < len(dict.keys()):
            color, string, reset = dict[dx]
            line_width = wcswidth(line)
            string_width = wcswidth(string)
            if string_width + line_width == line_length:
                colored_line_data.append((color, string, reset, line_group))
                line = ""
                dx += 1
                line_group += 1
            elif string_width + line_width < line_length:
                diff = line_length - (string_width + line_width)
                line += string
                colored_line_data.append((color, string, reset, line_group))
                dx += 1
            else:
                if diff != 0:
                    substr_width = wcswidth(string[:diff])
                    line += string[:substr_width]
                    colored_line_data.append((color, string[:substr_width], reset, line_group))
                    dict[dx] = (color, string[substr_width:], reset)
                    line = ""
                    diff = 0
                    line_group += 1
                else:
                    substr_width = min(wcswidth(string[:line_length]), line_length)
                    line += string[:substr_width]
                    colored_line_data.append((color, string[:substr_width], reset, line_group))
                    dict[dx] = (color, string[substr_width:], reset)
                    line_group += 1
                    if dict[dx][1] == "":
                        dx += 1

        lines = []
        for key, group in itertools.groupby(colored_line_data, lambda x: x[3]):
            line = ""
            for color, string, reset, line_group in group:
                line += color + string + reset
            lines.append(line)
        return lines

    @staticmethod
    def _split_text_into_color_parts(text: str) -> list[tuple[str, str, str]]:
        matcher = re.compile(r"(\x1b\[38;2;\d+;\d+;\d+m(?:\x1b\[\d+m)*)(.*?)(\x1b\[0m)")
        substring_tuples = []
        for m in re.finditer(matcher, text):
            substring_tuples.append(m.span())

        substrings = []
        last_end = 0
        for start, end in sorted(substring_tuples):
            if start > last_end:
                substrings.append(text[last_end:start] or "")
            substrings.append(text[start:end] or "")
            last_end = end
        if last_end < len(text):
            substrings.append(text[last_end:] or "")

        parts: list[tuple[str, str, str]] = []
        for substring in substrings:
            if re.match(matcher, substring):
                g = re.match(matcher, substring).groups()
                parts.append(g)
            else:
                parts.append(("", substring, ""))
        return parts
