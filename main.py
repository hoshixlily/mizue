import signal
from time import sleep

from mizue.printer import Printer, TerminalColors
from mizue.progress import Progress
from mizue.util import Utility


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
    Printer.print(f'How are you?', TerminalColors.YELLOW)
    Printer.prevent_newline(False)
    Printer.prevent_newline(False)
    Printer.prevent_newline(False)
    Printer.prevent_newline(False)
    Printer.prevent_newline(False)
    Printer.print('This is a test', TerminalColors.RED, True, True)
    Printer.print('This is a test', TerminalColors.BG_CYAN, True, True)
    Printer.info(f'Terminal width: {Utility.get_terminal_width()}')
    Printer.info(f'Terminal height: {Utility.get_terminal_height()}')


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    progress = Progress(0, 100, 0, 10)
    signal.signal(signal.SIGINT, SignalHandler(progress))

    print_message('Mizu')

    interval = 1
    # progress.set_update_interval(interval)
    progress.start()
    progress.set_label('Progress: ')
    for i in range(101):
        progress.set_info(f'File {i} of 100')
        progress.update_value(i)
        sleep(interval)
    progress.stop()

# See PyCharm help at https://www.jetbrains.com/help/pycharm/
