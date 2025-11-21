"""
Plik zawierajacy definicje, jak powinny wygladac obiekty emitujace eventy.
Jest to czesc implementacji designu observera.
"""
import copy
from typing import Any

from pisak.events import BaseEvent

class EventEmitter:
    """
    Podstawowa implementacja EventEmittera - obiektu, ktory emituje wewnetrzne eventy
    do swoich subskrybentow (implementacja designu observera).
    """
    def __init__(self):
        self._event_handlers: set[Any] = set()

    @property
    def event_handlers(self) -> set[Any]:
        return copy.copy(self._event_handlers)

    def subscribe(self, handler) -> None:
        self._event_handlers.add(handler)

    def unsubscribe(self, handler) -> None:
        if handler in self._event_handlers:
            self._event_handlers.remove(handler)

    def emit_event(self, event: BaseEvent) -> None:
        """
        Emit an event to all subscribed handlers
        """
        for handler in self._event_handlers:
            try:
                handler.handle_event(event)
            except Exception as e:
                # Log error but don't break the event chain
                print(f"Error in handler {handler}: {e}")