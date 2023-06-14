from signal import signal, Signals


class SignalHandler:
    def __init__(self, signal: Signals, callback: callable):
        self._callback = callback
        self._signal = signal
        self._signal_received = False

    def __call__(self, *args, **kwargs):
        self._signal_received = True
        self._signal_handler()

    def is_signal_received(self):
        return self._signal_received

    def _signal_callback(self):
        self._signal_received = True
        self._callback()

    def _signal_handler(self):
        signal(self._signal, self._signal_callback)
