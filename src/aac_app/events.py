from enum import Enum, auto
from typing import Any


class AppEventType(Enum):
    BUTTON_CLICKED = auto()  # button click event
    SWITCH_PRESSED = auto()  # switch signal event
    WIDGET_FOCUSED = auto()  # event: widget gained focus
    WIDGET_UNFOCUSED = auto()  # event: widget lost focus
    TIMER_TIMEOUT = auto()  # event related to moving focus during loop scanning
    SCANNING_STARTED = auto()  # event: scanning of a new item started
    SCANNING_STOPPED = auto()  # scanning of the given item finished
    ITEM_ACTIVATED = (
        auto()
    )  # event: the given item was activated (external input arrived while the item had focus)
    SCANNING_RESET = auto()  # scanning reset event
    # Text input events (from virtual keyboard)
    CHAR_ADDED = auto()  # event: text entered from the virtual keyboard
    WORD_ADDED = auto()  # event: text entered from the virtual keyboard
    SPACE_ADDED = auto()  # event: space added
    BACKSPACE_PRESSED = auto()  # event: backspace pressed
    CLEAR_PRESSED = auto()  # event: display cleared
    NEW_LINE_ADDED = auto()  # event: new line added
    CURSOR_MOVED_LEFT = auto()  # event: cursor moved left
    CURSOR_MOVED_RIGHT = auto()  # event: cursor moved right
    CURSOR_MOVED_UP = auto()
    CURSOR_MOVED_DOWN = auto()
    TEXT_CHANGED = auto()  # event: display text changed (text + cursor position)
    ITEM_POINTED = auto()
    READ_TEXT = auto()

    MODULE_EXITED = auto()

    # Keyboard switching events
    ITEMS_SWITCHED = auto()  # event: displayed items changed (e.g. in a stacked widget)
    # Prediction events
    PREDICTIONS_READY = auto()  # event: word predictions ready


class BaseEvent:
    """Base class for all events - framework agnostic"""

    def __init__(self, event_type: Enum, data: Any = None):
        """
        :param event_type: the event type tells what exactly happened.
                           Depending on which kind of event we are dealing
                           with, we will encounter different event types.
                           For example, a ScanningEvent may have the type
                           SCANNING_STARTED, meaning that scanning has started,
                           but it can also have the type SCANNING_STOPPED,
                           meaning that scanning has finished.

        :param data: additional information needed for the observer to handle
                     the event correctly. This can be anything, e.g. an item
                     that for some reason is crucial for the given event.
        """
        self._type = event_type
        self._data = data

    @property
    def type(self) -> Enum:
        return self._type

    @property
    def data(self) -> Any:
        return self._data

    def __repr__(self):
        return f"{self.__class__.__name__}(type={self._type}, data={self._data})"


class AppEvent(BaseEvent):
    def __init__(self, event_type: AppEventType, data: Any = None):
        super().__init__(event_type=event_type, data=data)
