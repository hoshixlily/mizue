import sys
import re

from . import Colorizer
from .terminal_colors import TerminalColors


class Printer:
    """Provides static methods for printing styled text to the terminal."""
    _newline: bool = True
    _single_line: bool = False

    @staticmethod
    def clear_line() -> None:
        """
        Clears the current line in the console using ANSI escape codes.
        Moves cursor to beginning of line and erases to the end.
        Note: Behavior depends on terminal support for ANSI codes.
        """
        # \r: Carriage return (moves cursor to beginning of line)
        # \x1b[K: Erases from cursor to end of line
        sys.stdout.write('\r\x1b[K')
        sys.stdout.flush()

    @staticmethod
    def error(text: str, bold: bool = False, italic: bool = False,
              underlined: bool = False, strikethrough: bool = False) -> None:
        """Prints an error message to the console (default color: red)."""
        Printer.print(text, TerminalColors.ERROR, bold=bold, italic=italic,
                      underlined=underlined, strikethrough=strikethrough)

    @staticmethod
    def info(text: str, bold: bool = False, italic: bool = False,
             underlined: bool = False, strikethrough: bool = False) -> None:
        """Prints an info message to the console (default color: blue)."""
        Printer.print(text, TerminalColors.INFO, bold=bold, italic=italic,
                      underlined=underlined, strikethrough=strikethrough)


    @staticmethod
    def print(text: str, color: str | tuple[int, int, int] | None = None,
              background: str | tuple[int, int, int] | None = None,
              bold: bool = False, italic: bool = False,
              underlined: bool = False, strikethrough: bool = False) -> None:
        """
        Prints a message to the console with optional styling.
        Handles single-line mode internally.
        Colors strings can be in 6-digit hex format or RGB tuple format.
        """
        if Printer._single_line:
            Printer.clear_line()

        colored_text = Colorizer.colorize(text, color, background, bold, italic, underlined, strikethrough)

        print(colored_text, end='\n' if Printer._newline else '', flush=True)

    @staticmethod
    def set_single_line_mode(mode: bool):
        """
        Sets the printer to single-line mode (True) or multi-line mode (False).
        In single-line mode, subsequent prints overwrite the current line and
        newlines are suppressed. Exiting single-line mode re-enables newlines.
        """
        Printer._single_line = mode
        Printer._newline = not mode # Suppress newline in single-line mode
        if not mode:
             # When exiting single line mode, print a newline to start fresh
            print()


    @staticmethod
    def success(text: str, bold: bool = False, italic: bool = False,
                underlined: bool = False, strikethrough: bool = False) -> None:
        """Prints a success message to the console (default color: green)."""
        Printer.print(text, TerminalColors.SUCCESS, bold=bold, italic=italic,
                      underlined=underlined, strikethrough=strikethrough)

    @staticmethod
    def strip_ansi(text: str) -> str:
        """
        Strips all ANSI escape sequences (including colors and styles) from a string.
        """
        # This regex covers various ANSI sequence forms
        ansi_escape_pattern = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
        return ansi_escape_pattern.sub('', text)

    # Removed strip_colors as strip_ansi covers its functionality

    @staticmethod
    def warning(text: str, bold: bool = False, italic: bool = False,
                underlined: bool = False, strikethrough: bool = False) -> None:
        """Prints a warning message to the console (default color: orange)."""
        Printer.print(text, TerminalColors.WARNING, bold=bold, italic=italic,
                      underlined=underlined, strikethrough=strikethrough)