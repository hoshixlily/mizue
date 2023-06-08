# from subprocess import call
from .terminal_colors import TerminalColors


class Printer:
    _newline: bool = True

    @staticmethod
    def _formatted(text: str) -> bool:
        return str(text).endswith(TerminalColors.ENDC)

    @staticmethod
    def format(text: str, color: str, bold: bool = False, underlined: bool = False, no_end: bool = False) -> str:
        """Formats a string with the specified color, boldness, and underlining."""
        # call('', shell=True)  # Enable VT100 mode
        bolded = TerminalColors.BOLD if bold else ''
        underlined = TerminalColors.UNDERLINE if underlined else ''
        end = TerminalColors.ENDC if not no_end else ''
        return f'{color}{bolded}{underlined}{text}{end}'

    @staticmethod
    def error(text: str, bold: bool = False, underlined: bool = False) -> None:
        """Prints an error message to the console."""
        Printer.print(Printer.format(text, TerminalColors.ERROR, bold, underlined))

    @staticmethod
    def info(text: str, bold: bool = False, underlined: bool = False) -> None:
        """Prints an info message to the console."""
        Printer.print(Printer.format(text, TerminalColors.INFO, bold, underlined))

    @staticmethod
    def prevent_newline(prevent: bool = True) -> None:
        """Prevents a newline from being printed to the console."""
        if Printer._newline != prevent:
            return
        Printer._newline = not prevent
        if Printer._newline:
            print()

    @staticmethod
    def print(text: str, color: str = TerminalColors.WHITE, bold: bool = False, underlined: bool = False) -> None:
        """Prints a message to the console."""
        formatted_text = text if Printer._formatted(text) else Printer.format(text, color, bold, underlined)
        print(formatted_text, end='\n' if Printer._newline else '', flush=True)

    @staticmethod
    def success(text: str, bold: bool = False, underlined: bool = False) -> None:
        """Prints a success message to the console."""
        Printer.print(Printer.format(text, TerminalColors.SUCCESS, bold, underlined))

    @staticmethod
    def warning(text: str, bold: bool = False, underlined: bool = False) -> None:
        """Prints a warning message to the console."""
        Printer.print(Printer.format(text, TerminalColors.WARNING, bold, underlined))
