import os.path
import signal
import sys
from time import sleep

from mizue.printer import Printer, TerminalColors, TablePrinter
from mizue.progress import Progress
from mizue.util import Utility
from mizue.file import FileUtils


class SignalHandler:
    def __init__(self, progress_instance: Progress):
        self._signal_received = False
        self._progress = progress_instance

    def __call__(self, sig, frame):
        self._signal_received = True
        self._progress.terminate()

    def is_signal_received(self):
        return self._signal_received


def print_message(name):
    Printer.prevent_newline(True)
    Printer.error(f'Hi, {name}. ')
    Printer.print_ansi(f'How are you?', TerminalColors.YELLOW)
    Printer.prevent_newline(False)
    Printer.prevent_newline(False)
    Printer.prevent_newline(False)
    Printer.prevent_newline(False)
    Printer.prevent_newline(False)
    Printer.print_ansi('This is a test', TerminalColors.RED, True, True)
    Printer.print_ansi('This is a test', TerminalColors.BG_CYAN, True, True)
    Printer.info(f'Terminal width: {Utility.get_terminal_width()}')
    Printer.info(f'Terminal height: {Utility.get_terminal_height()}')


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    progress = Progress(0, 100, 0, 10)
    signal.signal(signal.SIGINT, SignalHandler(progress))

    # print_message('Mizu')
    #
    # interval = 0.1
    # # progress.set_update_interval(interval)
    # progress.start()
    # progress.set_label('Progress: ')
    # for i in range(101):
    #     progress.set_info(f'File {i} of 100')
    #     progress.update_value(i)
    #     sleep(interval)
    # progress.stop()

    # print files
    files = FileUtils.list_folders(sys.argv[1], False, False)
    table = list(map(lambda f: [f, os.path.basename(f)], files))
    table_printer = TablePrinter(table)
    table_printer.color_list = ['#00a86b', '#906090']
    table_printer.border_color = '#348f50'
    table_printer.border_style = TablePrinter.BorderStyle.DOUBLE
    table_printer.cell_length_list = [40, 40]
    table_printer.title_data = [Printer.format_hex('Path', '#906090'), Printer.format_hex('Name', '#ff1493')]
    # table_printer.title_data = ['Path', 'Name']
    # table_printer.align_list = [TablePrinter.Alignment.LEFT, TablePrinter.Alignment.RIGHT]
    table_printer.print_table()

    Printer.print_rgb(' RGB COLORED TEXT ', (255, 220, 110), bold=True, underlined=False)
    Printer.print_hex(' HEX COLORED TEXT ', '#00a9ff', bold=True, underlined=False)
    Printer.print_ansi(' ANSI COLORED TEXT ', TerminalColors.BRIGHT_GREEN, bold=True, underlined=False)

    Printer.print_rgb(' RGB COLORED TEXT WITH BG COLOR ', (222, 222, 222), (30, 31, 35), bold=True, underlined=False)

    TablePrinter.print_text_with_border('This is', border_color='#00a9ff', border_style=TablePrinter.BorderStyle.SINGLE)


# See PyCharm help at https://www.jetbrains.com/help/pycharm/
