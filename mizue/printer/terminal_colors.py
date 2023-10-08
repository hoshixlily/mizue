from typing import Final


class TerminalColors:
    END_CHAR: Final[str] = '\x1b[0m'
    SUCCESS: Final[str] = '#4CAF50'
    WARNING: Final[str] = '#ff9800'
    ERROR: Final[str] = '#f44336'
    INFO: Final[str] = '#2196F3'
    UNDERLINE: Final[str] = '\x1b[4m'
    BOLD: Final[str] = '\x1b[1m'
    ITALIC: Final[str] = '\x1b[3m'
    STRIKETHROUGH: Final[str] = '\x1b[9m'
    RESET: Final[str] = '\x1b[0m'
