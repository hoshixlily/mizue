from threading import Thread, Event


class StoppableThread(Thread):
    def __init__(self, target, args=()):
        super(StoppableThread, self).__init__(target=target, args=args)
        self._stop_event = None

    def stop(self) -> None:
        self._stop_event.set()

    def _init_stop_event(self) -> None:
        self._stop_event = Event()

    def _is_stopped(self) -> bool:
        return self._stop_event.is_set()
