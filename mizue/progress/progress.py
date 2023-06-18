import sys
from time import sleep

from mizue.printer import Printer
from mizue.util import Utility
from mizue.util.stoppable_thread import StoppableThread
from .progress_renderer_args import ProgressBarRendererArgs, SpinnerRendererArgs, LabelRendererArgs, \
    InfoSeparatorRendererArgs, InfoTextRendererArgs, PercentageRendererArgs


class Progress:
    def __init__(self, start: int = 0, end: int = 100, value: int = 0):
        self._active = False
        self._end = end
        self._interval = 0.1
        self._spinner = [
            "▹▹▹▹▹",
            "▸▹▹▹▹",
            "▹▸▹▹▹",
            "▹▹▸▹▹",
            "▹▹▹▸▹",
            "▹▹▹▹▸"
        ]
        self._spinner_end_symbol = "⠿"
        self._spinner_index = 0
        self._start = start
        self._thread = None
        self._value = value
        self._width = 10

        self.info_separator = " | "
        self.info_separator_renderer = lambda args: self._info_separator_renderer()  # InfoSeparatorRendererArgs

        self.info_text = ""
        """Set the info text to be displayed after the progress bar"""

        self.info_text_renderer = lambda args: self._info_text_renderer(args.text)  # InfoTextRendererArgs
        self.label = ""
        self.label_renderer = lambda args: args.label  # LabelRendererArgs
        self.percentage_renderer = lambda args: "{:.2f}%".format(args.percentage)  # PercentageRendererArgs
        self.spinner_renderer = lambda args: args.spinner  # SpinnerRendererArgs
        self.progress_bar_renderer = lambda args: self._progress_bar_renderer()  # ProgressBarRendererArgs

    def set_end_value(self, end: int) -> None:
        """Update the maximum value of the progress bar"""
        self._end = end

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
        sleep(1)
        self._active = False
        self._spinner_index = 0
        self._thread.join()
        Utility.show_cursor()

    def terminate(self) -> None:
        """Terminate the progress bar.
            This method is generally used when the progress bar is needed to be stopped (e.g. on Ctrl+C)"""
        sleep(1)
        self._active = False
        self._spinner_index = 0
        self._thread.stop()
        self._thread.join()
        Utility.show_cursor()

    def update_value(self, value: int) -> None:
        """Update the value of the progress bar"""
        self._value = value

    def _get_bar_full_width(self) -> int:
        percentage = self._value * 100 / self._end
        bar_width = int(percentage * self._width / 100)
        return bar_width

    def _get_progress_text(self) -> str:
        percentage_value = self._value * 100 / self._end
        percentage = self.percentage_renderer(PercentageRendererArgs(percentage_value, self._value))
        spinner_symbol = self.spinner_renderer(SpinnerRendererArgs(
            spinner=self._spinner[self._spinner_index % len(self._spinner)],
            value=self._value,
            percentage=percentage_value
        ))
        bar_string = self._progress_bar_renderer()
        bar = self.progress_bar_renderer(ProgressBarRendererArgs(
            percentage=percentage_value,
            text=bar_string,
            value=self._value,
            width=self._get_bar_full_width()
        ))
        label = self.label_renderer(LabelRendererArgs(
            label=self.label,
            value=self._value,
            percentage=percentage_value
        ))
        separator = self.info_separator_renderer(InfoSeparatorRendererArgs(
            separator=self.info_separator,
            value=self._value,
            percentage=percentage_value
        ))
        info_text = self.info_text_renderer(InfoTextRendererArgs(
            text=self.info_text,
            value=self._value,
            percentage=percentage_value
        ))
        progress_text = str.format("{}{} {} {}{}{}", label, bar, spinner_symbol, percentage, separator,
                                   info_text)
        text_length = len(Printer.strip_colors(progress_text))
        if text_length > Utility.get_terminal_width():
            progress_text = str.format("{}{} {} {}{}", label, bar, spinner_symbol, percentage, '')
            if text_length > Utility.get_terminal_width():
                progress_text = str.format("{}{} {} {}{}", '', bar, spinner_symbol, percentage, '')
        return progress_text

    def _info_separator_renderer(self) -> str:
        return self.info_separator if len(self.info_text) > 0 else ""

    @staticmethod
    def _info_text_renderer(info_text: str) -> str:
        return info_text

    def _print(self) -> None:
        while self._active:
            progress_text = self._get_progress_text()
            self._spinner_index += 1
            sys.stdout.write(
                u"\u001b[K")  # Erase from cursor to end of line [http://matthieu.benoit.free.fr/68hc11/vt100.htm]
            sys.stdout.write(
                u"\u001b[1000D" + progress_text)  # Move terminal cursor 1000 characters left (go to start of line)
            sys.stdout.flush()
            sleep(self._interval)

    def _progress_bar_renderer(self) -> str:
        bar_start = "⟪"
        bar_end = "⟫"
        width = self._get_bar_full_width()
        bar = bar_start + "◆" * int(width) + " " * int((self._width - width)) + bar_end
        return bar
