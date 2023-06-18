from abc import ABC


class EventListener(ABC):
    """Abstract class for event listeners"""
    def __init__(self):
        self._event_id_counter: int = 0
        self._events: dict[str, list[callable]] = {}
        self._event_id_map: dict[int, [str, callable]] = {}

    def add_event(self, event: str, callback: callable) -> int:
        """Add a callback to an event"""
        if event not in self._events:
            self._events[event] = []

        event_id = self._event_id_counter
        self._event_id_counter += 1
        self._event_id_map[event_id] = [event, callback]
        self._events[event].append(callback)
        return event_id

    def remove_event(self, event_id: int) -> None:
        """Remove a callback from an event"""
        if event_id in self._event_id_map:
            event, callback = self._event_id_map[event_id]
            self._events[event].remove(callback)
            del self._event_id_map[event_id]

    def _fire_event(self, event: str, *args, **kwargs) -> None:
        """Fire an event"""
        if event in self._events:
            for callback in self._events[event]:
                callback(*args, **kwargs)
