import typing
import re

from .terminal_colors import TerminalColors


class Printer:
    _newline: bool = True

    @staticmethod
    def apply_background(message, bg_color):
        end_char = '' if Printer._formatted(message) else TerminalColors.END_CHAR
        msg = str.format("{}{}{}", bg_color, message, end_char)
        return msg

    @staticmethod
    def format(text: str, color: str = None, bold: bool = False, underlined: bool = False) -> str:
        """Formats a string with the specified color, boldness, and underlining."""
        color = color if color is not None else ''
        bolded = TerminalColors.BOLD if bold else ''
        underlined = TerminalColors.UNDERLINE if underlined else ''
        end = TerminalColors.END_CHAR
        return f'{color}{bolded}{underlined}{text}{end}'

    @staticmethod
    def format_hex(text: str, text_hex: str, bg_hex: str | None = None,
                   bold: bool = False, underlined: bool = False) -> str:
        """Formats a string with the specified color, boldness, and underlining."""
        if bg_hex is None:
            text_rgb: tuple = Printer.hex_to_rgb(text_hex)
            return Printer.format_rgb(text, text_rgb, None, bold, underlined)
        else:
            text_rgb: tuple = Printer.hex_to_rgb(text_hex)
            bg_rgb: tuple = Printer.hex_to_rgb(bg_hex)
            return Printer.format_rgb(text, text_rgb, bg_rgb, bold, underlined)

    @staticmethod
    def format_rgb(text: str, text_rgb: tuple[int, int, int], bg_rgb: tuple[int, int, int] | None = None,
                   bold: bool = False, underlined: bool = False) -> str:
        """Formats a string with the specified color, boldness, and underlining."""
        bolded = TerminalColors.BOLD if bold else ''
        underlined = TerminalColors.UNDERLINE if underlined else ''
        end = TerminalColors.END_CHAR
        if bg_rgb is None:
            return f'\033[38;2;{text_rgb[0]};{text_rgb[1]};{text_rgb[2]}m{bolded}{underlined}{text}{end}'
        else:
            return f'\033[38;2;{text_rgb[0]};{text_rgb[1]};{text_rgb[2]}m' \
                   f'\033[48;2;{bg_rgb[0]};{bg_rgb[1]};{bg_rgb[2]}m{bolded}{underlined}{text}{end}'

    @staticmethod
    def error(text: str, bold: bool = False, underlined: bool = False) -> None:
        """Prints an error message to the console."""
        Printer.print_hex(text, TerminalColors.ERROR, bold=bold, underlined=underlined)

    @staticmethod
    def get_color_string(color: str | tuple[int, int, int]):
        if isinstance(color, tuple):
            return Printer.rgb_to_hex(color)
        else:
            return color

    @staticmethod
    def hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
        """Converts a hex string to an RGB tuple."""
        hex_without_hash = hex_color.replace('#', '') if hex_color.startswith('#') else hex_color
        return typing.cast(tuple[int, int, int], tuple(int(hex_without_hash[i:i + 2], 16) for i in (0, 2, 4)))

    @staticmethod
    def info(text: str, bold: bool = False, underlined: bool = False) -> None:
        """Prints an info message to the console."""
        Printer.print_hex(text, TerminalColors.INFO, bold=bold, underlined=underlined)

    @staticmethod
    def prevent_newline(prevent: bool = True) -> None:
        """Prevents a newline from being printed to the console."""
        if Printer._newline != prevent:
            return
        Printer._newline = not prevent
        if Printer._newline:
            print()

    @staticmethod
    def print_hex(text: str, text_hex: str, bg_hex: str | None = None,
                  bold: bool = False, underlined: bool = False) -> None:
        """Prints a message to the console."""
        rgb: tuple = Printer.hex_to_rgb(text_hex)
        bg_rgb: tuple = Printer.hex_to_rgb(bg_hex) if bg_hex is not None else None
        Printer.print_rgb(text, rgb, bg_rgb, bold, underlined)

    @staticmethod
    def print_rgb(text: str, text_rgb: tuple[int, int, int], bg_rgb: tuple[int, int, int] | None = None,
                  bold: bool = False, underlined: bool = False) -> None:
        """Prints a message to the console."""
        formatted_text = text if Printer._formatted(text) else Printer.format_rgb(text, text_rgb, bg_rgb, bold,
                                                                                  underlined)
        print(formatted_text, end='\n' if Printer._newline else '', flush=True)

    @staticmethod
    def rgb_to_hex(rgb: tuple[int, int, int]) -> str:
        """Converts an RGB tuple to a hex string."""
        return f'#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}'

    @staticmethod
    def short_hex_to_long_hex(hex_color: str) -> str:
        """Converts a short hex color to a long hex color."""
        hex_without_hash = hex_color.replace('#', '') if hex_color.startswith('#') else hex_color
        return f'#{hex_without_hash[0]}{hex_without_hash[0]}{hex_without_hash[1]}{hex_without_hash[1]}' \
               f'{hex_without_hash[2]}{hex_without_hash[2]}'

    @staticmethod
    def success(text: str, bold: bool = False, underlined: bool = False) -> None:
        """Prints a success message to the console."""
        Printer.print_hex(text, TerminalColors.SUCCESS, bold=bold, underlined=underlined)

    @staticmethod
    def strip_ansi(text: str) -> str:
        """Strips ANSI escape sequences from a string."""
        return re.sub(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])', '', text)

    @staticmethod
    def strip_colors(text: str) -> str:
        stripped_text = re.sub(r'\x1b[\[\d;]+m', '', text)
        return Printer.strip_ansi(stripped_text)

    @staticmethod
    def warning(text: str, bold: bool = False, underlined: bool = False) -> None:
        """Prints a warning message to the console."""
        Printer.print_hex(text, TerminalColors.WARNING, bold=bold, underlined=underlined)

    @staticmethod
    def _formatted(text: str) -> bool:
        return str(text).endswith(TerminalColors.END_CHAR)
