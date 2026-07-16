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

    Handlers are kept in a list rather than a set, so events are always delivered
    in subscription order. With a set, the order depended on object hashes (i.e. on
    memory addresses) and therefore differed between runs - unacceptable here, both
    because some handlers react to what an earlier handler did, and because an
    experiment must behave reproducibly.
    """

    def __init__(self):
        self._event_handlers: list[Any] = []

    @property
    def event_handlers(self) -> list[Any]:
        return copy.copy(self._event_handlers)

    def subscribe(self, handler) -> None:
        """Register a handler; subscribing the same handler twice has no effect."""
        if handler not in self._event_handlers:
            self._event_handlers.append(handler)

    def unsubscribe(self, handler) -> None:
        if handler in self._event_handlers:
            self._event_handlers.remove(handler)

    def emit_event(self, event: BaseEvent) -> None:
        """
        Emit an event to all subscribed handlers, in subscription order.

        A failing handler is logged but does not stop the event from reaching the
        remaining handlers - one broken observer must not break the whole chain.
        """
        # Iterate over a copy: a handler may subscribe or unsubscribe while reacting.
        for handler in list(self._event_handlers):
            try:
                handler.handle_event(event)
            except Exception:
                # Logged at error level with a traceback: swallowing these at debug
                # level hides real bugs, since every handler failure ends up here.
                logger.exception(
                    "Error in handler %s while handling %s", handler, event
                )
