from sys import stdout
from time import sleep
from mizue.util import Utility
from threading import Thread


class Spinner:
    def __init__(self):
        self._symbols = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        self._spinning = False
        self._thread = None

    def _spin(self) -> None:
        index = 0
        while self._spinning:
            spin_symbol = self._symbols[index % len(self._symbols)]
            stdout.write(u"\u001b[1D" + spin_symbol)
            stdout.flush()
            index += 1
            sleep(0.1)

    def start(self) -> None:
        Utility.hide_cursor()
        self._spinning = True
        self._thread = Thread(target=self._spin)
        self._thread.start()

    def stop(self) -> None:
        sleep(0.3)
        self._spinning = False
        self._thread.join()
        stdout.write(u"\u001b[1D")
        stdout.flush()
        Utility.show_cursor()