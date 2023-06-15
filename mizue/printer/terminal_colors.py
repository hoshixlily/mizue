from typing import Final


class TerminalColors:
    END_CHAR: Final[str] = '\033[00m'
    SUCCESS: Final[str] = '#4CAF50'
    WARNING: Final[str] = '#ff9800'
    ERROR: Final[str] = '#f44336'
    INFO: Final[str] = '#2196F3'
    UNDERLINE: Final[str] = '\033[4m'
    BOLD: Final[str] = '\u001b[1m'
    RESET: Final[str] = '\u001b[0m'
