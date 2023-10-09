import sys
import typing
import re

from .terminal_colors import TerminalColors


class Printer:
    _newline: bool = True

    @staticmethod
    def clear_line() -> None:
        """Clears the current line in the console."""
        sys.stdout.write(u"\u001b[K")
        sys.stdout.write(u"\u001b[1000D")
        sys.stdout.flush()

    @staticmethod
    def format_hex(text: str, color: str | None = None, background: str | None = None,
                   bold: bool = False, italic: bool = False, underlined: bool = False,
                   strikethrough: bool = False) -> str:
        """Formats a string with the specified customizations. Color strings should be in 6-digit hex format."""
        text_rgb: tuple = Printer.hex_to_rgb(color) if color is not None else None
        bg_rgb: tuple = Printer.hex_to_rgb(background) if background is not None else None
        return Printer.format_rgb(text, text_rgb, bg_rgb, bold, italic, underlined, strikethrough)

    @staticmethod
    def format_rgb(text: str, color: tuple[int, int, int] | None = None, background: tuple[int, int, int] | None = None,
                   bold: bool = False, italic: bool = False, underlined: bool = False,
                   strikethrough: bool = False) -> str:
        """Formats a string with the specified customizations. Color tuples should be in RGB format."""
        bolded = TerminalColors.BOLD if bold else ''
        italicized = TerminalColors.ITALIC if italic else ''
        underlined = TerminalColors.UNDERLINE if underlined else ''
        strikethrough = TerminalColors.STRIKETHROUGH if strikethrough else ''
        end = TerminalColors.END_CHAR
        if background is None:
            if color is None:
                return f'{bolded}{italicized}{underlined}{strikethrough}{text}{end}'
            return f'\033[38;2;{color[0]};{color[1]};{color[2]}m{bolded}{italicized}{underlined}{strikethrough}{text}{end}'
        else:
            if color is None:
                return f'\033[48;2;{background[0]};{background[1]};{background[2]}m{bolded}{italicized}{underlined}{strikethrough}{text}{end}'
            return f'\033[38;2;{color[0]};{color[1]};{color[2]}m' \
                   f'\033[48;2;{background[0]};{background[1]};{background[2]}m{bolded}{italicized}{underlined}{strikethrough}{text}{end}'

    @staticmethod
    def st_test():
        print("\x1b[9m" + "STRIKE THROUGH" + "\x1b[29m" + " NOT STRIKE THROUGH")

    @staticmethod
    def error(text: str, bold: bool = False, italic: bool = False,
              underlined: bool = False, strikethrough: bool = False) -> None:
        """Prints an error message to the console."""
        Printer.print_hex(text, TerminalColors.ERROR, bold=bold, italic=italic,
                          underlined=underlined, strikethrough=strikethrough)

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
    def info(text: str, bold: bool = False, italic: bool = False,
             underlined: bool = False, strikethrough: bool = False) -> None:
        """Prints an info message to the console."""
        Printer.print_hex(text, TerminalColors.INFO, bold=bold, italic=italic,
                          underlined=underlined, strikethrough=strikethrough)

    @staticmethod
    def prevent_newline(prevent: bool = True) -> None:
        """Prevents a newline from being printed to the console."""
        if Printer._newline != prevent:
            return
        Printer._newline = not prevent
        if Printer._newline:
            print()

    @staticmethod
    def print(text: str, color: str|tuple[int, int, int] | None = None,
              background: str | tuple[int, int, int] | None = None,
              bold: bool = False, italic: bool = False,
              underlined: bool = False, strikethrough: bool = False) -> None:
        """Prints a message to the console. Colors strings can be in 6-digit hex format or RGB format."""
        text_hex = Printer.get_color_string(color)
        bg_hex = Printer.get_color_string(background) if background is not None else None
        Printer.print_hex(text, text_hex, bg_hex, bold, italic, underlined, strikethrough)

    @staticmethod
    def print_clear(text_generator: typing.Generator[str, None, None], color: str|tuple[int, int, int] | None = None,
                    background: str | tuple[int, int, int] | None = None,
                    bold: bool = False, italic: bool = False,
                    underlined: bool = False, strikethrough: bool = False) -> None:
        """Prints the messages from a generator to the console, clearing the previous line."""
        was_prevented = Printer._newline
        Printer.prevent_newline()
        for text in text_generator:
            Printer.clear_line()
            Printer.print(text, color, background, bold, italic, underlined, strikethrough)
            # Printer.clear_line()
        if not was_prevented:
            Printer.prevent_newline(False)

    @staticmethod
    def print_hex(text: str, color: str | None = None, background: str | None = None,
                  bold: bool = False, italic: bool = False,
                  underlined: bool = False, strikethrough: bool = False) -> None:
        """Prints a message to the console. Color strings should be in 6-digit hex format."""
        rgb: tuple = Printer.hex_to_rgb(color) if color is not None else None
        bg_rgb: tuple = Printer.hex_to_rgb(background) if background is not None else None
        Printer.print_rgb(text, rgb, bg_rgb, bold, italic, underlined, strikethrough)

    @staticmethod
    def print_rgb(text: str, color: tuple[int, int, int] | None = None, backgroıund: tuple[int, int, int] | None = None,
                  bold: bool = False, italic: bool = False,
                  underlined: bool = False, strikethrough: bool = False) -> None:
        """Prints a message to the console. Color tuples should be in RGB format."""
        formatted_text = text if Printer._formatted(text) else Printer.format_rgb(text, color, backgroıund, bold, italic,
                                                                                  underlined, strikethrough)
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
    def success(text: str, bold: bool = False, italic: bool = False,
                underlined: bool = False, strikethrough: bool = False) -> None:
        """Prints a success message to the console."""
        Printer.print_hex(text, TerminalColors.SUCCESS, bold=bold, italic=italic,
                          underlined=underlined, strikethrough=strikethrough)

    @staticmethod
    def strip_ansi(text: str) -> str:
        """Strips ANSI escape sequences from a string."""
        return re.sub(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])', '', text)

    @staticmethod
    def strip_colors(text: str) -> str:
        stripped_text = re.sub(r'\x1b[\[\d;]+m', '', text)
        return Printer.strip_ansi(stripped_text)

    @staticmethod
    def warning(text: str, bold: bool = False, italic: bool = False,
                underlined: bool = False, strikethrough: bool = False) -> None:
        """Prints a warning message to the console."""
        Printer.print_hex(text, TerminalColors.WARNING, bold=bold, italic=italic,
                          underlined=underlined, strikethrough=strikethrough)

    @staticmethod
    def _formatted(text: str) -> bool:
        return str(text).endswith(TerminalColors.END_CHAR)
