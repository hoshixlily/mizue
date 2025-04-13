import typing

from mizue.printer import TerminalColors


class Colorizer:
    """Colorizer class for printing colored text to the terminal."""

    @staticmethod
    def colorize(text: str, color: str | tuple[int, int, int] | None = None,
                 background: str | tuple[int, int, int] | None = None,
                 bold: bool = False, italic: bool = False, underlined: bool = False,
                 strikethrough: bool = False) -> str:
        """Returns a string with the specified customizations.
           Color strings can be in 6-digit hex format or RGB format."""
        text_rgb = color if isinstance(color, tuple) else Colorizer.hex_to_rgb(color) \
            if color is not None else None
        bg_rgb = background if isinstance(background, tuple) else Colorizer.hex_to_rgb(background) \
            if background is not None else None
        return Colorizer._colorize_rgb(text, text_rgb, bg_rgb, bold, italic, underlined, strikethrough)

    @staticmethod
    def _colorize_rgb(text: str, color: tuple[int, int, int] | None = None,
                      background: tuple[int, int, int] | None = None,
                      bold: bool = False, italic: bool = False, underlined: bool = False,
                      strikethrough: bool = False) -> str:
        """Formats a string with the specified customizations. Color tuples should be in RGB format."""
        style_codes = []
        if color:
            style_codes.append(f'\033[38;2;{color[0]};{color[1]};{color[2]}m')
        if background:
            style_codes.append(f'\033[48;2;{background[0]};{background[1]};{background[2]}m')
        if bold:
            style_codes.append(TerminalColors.BOLD)
        if italic:
            style_codes.append(TerminalColors.ITALIC)
        if underlined:
            style_codes.append(TerminalColors.UNDERLINE)
        if strikethrough:
            style_codes.append(TerminalColors.STRIKETHROUGH)

        if not style_codes:
            return text # No styling needed

        prefix = "".join(style_codes)
        suffix = TerminalColors.END_CHAR
        return f'{prefix}{text}{suffix}'

    @staticmethod
    def get_color_rgb(color: str | tuple[int, int, int]) -> tuple[int, int, int]:
        """Returns a tuple containing the RGB values of the specified color."""
        if isinstance(color, tuple):
            return color
        else:
            return Colorizer.hex_to_rgb(color)

    @staticmethod
    def get_color_string(color: str | tuple[int, int, int]):
        if isinstance(color, tuple):
            return Colorizer.rgb_to_hex(color)
        else:
            return color

    @staticmethod
    def hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
        """Converts a hex string to an RGB tuple."""
        hex_without_hash = hex_color.replace('#', '') if hex_color.startswith('#') else hex_color
        return typing.cast(tuple[int, int, int], tuple(int(hex_without_hash[i:i + 2], 16) for i in (0, 2, 4)))

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
