import ctypes
import shutil


class _CursorInfo(ctypes.Structure):
    _fields_ = [("size", ctypes.c_int), ("visible", ctypes.c_byte)]


class Utility:

    @staticmethod
    def get_terminal_size() -> tuple[int, int]:
        """Returns the size of the terminal."""
        return shutil.get_terminal_size()

    @staticmethod
    def get_terminal_width() -> int:
        """Returns the width of the terminal."""
        return Utility.get_terminal_size()[0]

    @staticmethod
    def get_terminal_height() -> int:
        """Returns the height of the terminal."""
        return Utility.get_terminal_size()[1]

    @staticmethod
    def hide_cursor() -> None:
        """Hides the cursor."""
        info = _CursorInfo()
        info.visible = False
        ctypes.windll.kernel32.SetConsoleCursorInfo(ctypes.windll.kernel32.GetStdHandle(-11), ctypes.byref(info))

    @staticmethod
    def is_elevated() -> bool:
        """Returns whether the current process is elevated."""
        return ctypes.windll.shell32.IsUserAnAdmin() != 0

    @staticmethod
    def is_caps_lock_on() -> bool:
        """Returns whether the caps lock key is on."""
        return ctypes.windll.user32.GetKeyState(0x14) != 0

    @staticmethod
    def show_cursor() -> None:
        """Shows the cursor."""
        info = _CursorInfo()
        info.visible = True
        ctypes.windll.kernel32.SetConsoleCursorInfo(ctypes.windll.kernel32.GetStdHandle(-11), ctypes.byref(info))
