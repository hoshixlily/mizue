# from subprocess import call
from .terminal_colors import TerminalColors


class Printer:
    _newline: bool = True

    @staticmethod
    def _formatted(text: str) -> bool:
        return str(text).endswith(TerminalColors.ENDC)

    @staticmethod
    def format(text: str, color: str, bold: bool = False, underlined: bool = False, no_end: bool = False) -> str:
        # call('', shell=True)  # Enable VT100 mode
        bolded = TerminalColors.BOLD if bold else ''
        underlined = TerminalColors.UNDERLINE if underlined else ''
        end = TerminalColors.ENDC if not no_end else ''
        return f'{color}{bolded}{underlined}{text}{end}'

    @staticmethod
    def error(text: str, bold: bool = False, underlined: bool = False) -> None:
        Printer.print(Printer.format(text, TerminalColors.ERROR, bold, underlined))

    @staticmethod
    def info(text: str, bold: bool = False, underlined: bool = False) -> None:
        Printer.print(Printer.format(text, TerminalColors.INFO, bold, underlined))

    @staticmethod
    def prevent_newline(prevent: bool = True) -> None:
        Printer._newline = not prevent

    @staticmethod
    def print(text: str, color: str = TerminalColors.WHITE, bold: bool = False, underlined: bool = False) -> None:
        formatted_text = text if Printer._formatted(text) else Printer.format(text, color, bold, underlined)
        print(formatted_text, end='\n' if Printer._newline else '', flush=True)

    @staticmethod
    def success(text: str, bold: bool = False, underlined: bool = False) -> None:
        Printer.print(Printer.format(text, TerminalColors.SUCCESS, bold, underlined))

    @staticmethod
    def warning(text: str, bold: bool = False, underlined: bool = False) -> None:
        Printer.print(Printer.format(text, TerminalColors.WARNING, bold, underlined))
