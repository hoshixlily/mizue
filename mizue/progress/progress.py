import sys
from collections.abc import Callable
from time import sleep

from mizue.printer import Printer, TerminalColors
from mizue.util import Utility
from mizue.util.stoppable_thread import StoppableThread


class Progress:
    def __init__(self, start: int = 0, end: int = 100, value: int = 0, width: int = 10):
        self._active = False
        self._color = TerminalColors.BRIGHT_WHITE
        self._end = end
        self._info_callback: Callable[[int], str] | None = None
        self._info_text = ""
        self._interval = 0.1
        self._label_text = ""
        self._spinner = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        self._spinner_end_symbol = "⠿"
        self._spinner_index = 0
        self._start = start
        self._thread = None
        self._value = value
        self._width = width

    def set_info(self, info: str) -> None:
        """Set the info text to be displayed after the progress bar"""
        self._info_text = info

    def set_info_callback(self, callback: Callable[[int], str]) -> None:
        """Set the callback function to be called to get the info text to be displayed after the progress bar"""
        self._info_callback = callback

    def set_label(self, label: str) -> None:
        """Set the label text to be displayed before the progress bar"""
        self._label_text = label

    def set_update_interval(self, interval: float) -> None:
        """Set the update interval of the progress bar"""
        self._interval = interval

    def start(self) -> None:
        """Start the progress bar"""
        Utility.hide_cursor()
        self._thread = StoppableThread(target=self._print, args=())
        self._active = True
        self._thread.start()

    def stop(self) -> None:
        """Stop the progress bar"""
        self._active = False
        self._spinner_index = 0
        sleep(1)
        self._thread.join()
        Utility.show_cursor()

    def terminate(self) -> None:
        """Terminate the progress bar.
            This method is generally used when the progress bar is needed to be stopped (e.g. on Ctrl+C)"""
        self._active = False
        self._spinner_index = 0
        self._thread.stop()
        self._thread.join()
        Utility.show_cursor()

    def update_max(self, end: int) -> None:
        """Update the maximum value of the progress bar"""
        self._end = end

    def update_value(self, value: int) -> None:
        """Update the value of the progress bar"""
        self._value = value

    def _print(self) -> None:
        progress_text = ""
        while self._active:
            progress_text = self._get_progress_text()
            self._spinner_index += 1
            sys.stdout.write(
                u"\u001b[K")  # Erase from cursor to end of line [http://matthieu.benoit.free.fr/68hc11/vt100.htm]
            sys.stdout.write(
                u"\u001b[1000D" + progress_text)  # Move terminal cursor 1000 characters left (go to start of line)
            sys.stdout.flush()
            sleep(self._interval)
        progress_text = progress_text.translate({ord(x): self._spinner_end_symbol for x in self._spinner})
        sys.stdout.write(
            u"\u001b[K")  # Erase from cursor to end of line [http://matthieu.benoit.free.fr/68hc11/vt100.htm]
        sys.stdout.write(
            u"\u001b[1000D" + progress_text)  # Move terminal cursor 1000 characters left (go to start of line)

    def _get_bar_full_width(self) -> int:
        percentage = self._value * 100 / self._end
        bar_width = int(percentage * self._width / 100)
        return bar_width

    def _get_colored_text(self, character: str) -> str:
        if self._value < 40:
            return Printer.format(character, TerminalColors.BRIGHT_RED)
        elif self._value < 80:
            return Printer.format(character, TerminalColors.BRIGHT_YELLOW)
        else:
            return Printer.format(character, TerminalColors.BRIGHT_GREEN)

    def _get_progress_text(self) -> str:
        width = self._get_bar_full_width()
        percentage = "{:.2f}%".format(self._value * 100 / self._end)
        spinner_symbol = self._spinner[self._spinner_index % len(self._spinner)]
        bar_start = "["
        bar_end = "]"
        bar = bar_start + "#" * int(width) + " " * int((self._width - width)) + bar_end
        separator = " | " if len(self._info_text) > 0 else ""
        info_text = self._info_text if self._info_callback is None else self._info_callback(self._value)
        progress_text = str.format("{}{} {} {}{}{}", self._label_text, bar, spinner_symbol, percentage, separator,
                                   info_text)
        if len(progress_text) > Utility.get_terminal_width():
            progress_text = str.format("{}{} {} {}{}", self._label_text, bar, spinner_symbol, percentage, '')
            if len(progress_text) > Utility.get_terminal_width():
                progress_text = str.format("{}{} {} {}{}", '', bar, spinner_symbol, percentage, '')
        progress_text = self._get_colored_text(progress_text)
        return progress_text


