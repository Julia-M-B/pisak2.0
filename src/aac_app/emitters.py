"""
This file defines what event-emitting objects should look like.
It is part of the observer pattern implementation.
"""

import copy
from typing import Any

from aac_app.events import BaseEvent
from aac_app.logging_config import get_module_logger

logger = get_module_logger(file_name="emitters", logger_name=__name__)


class EventEmitter:
    """
    Basic EventEmitter implementation - an object that emits internal events
    to its subscribers (observer pattern implementation).
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
                logger.debug("Error in handler %s: %s", handler, e)
