"""
UI Adapter Layer - bridges framework-specific UI events to framework-agnostic events.
This layer isolates PySide6 dependencies from business logic.

The idea of this file is to avoid mixing PySide signals with internal events;
all bindings between signals and events are handled by adapters, which convert
a PySide signal into an internal event.
"""

from typing import Optional

from PySide6.QtCore import QEvent, QObject, QTimer
from PySide6.QtWidgets import QWidget

from aac_app.emitters import EventEmitter
from aac_app.events import AppEvent, AppEventType


class QtEventAdapter(EventEmitter, QObject):
    """
    Base class for adapters converting PySide6 signals into internal events.
    Inherits from both EventEmitter and QObject.
    """

    def __init__(self, parent: Optional[QObject] = None):
        QObject.__init__(self, parent)
        EventEmitter.__init__(self)


class _WidgetEventAdapter(QtEventAdapter):
    """
    Base for adapters that watch a single widget through Qt's event filter.

    An event filter is used rather than replacing the widget's handler method:
    monkey-patching cannot be undone, breaks when two adapters watch the same
    widget, and hides the behaviour from anyone reading the widget class.

    Subclasses declare which Qt event type they translate and how.
    """

    #: Qt event type the subclass reacts to
    watched_event_type: QEvent.Type

    def __init__(self, widget: QWidget, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._widget = widget
        widget.installEventFilter(self)

    def detach(self) -> None:
        """Stop watching the widget."""
        self._widget.removeEventFilter(self)

    def _build_event(self, event: QEvent) -> AppEvent:
        raise NotImplementedError("Method `_build_event` is not implemented.")

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        """Translate a watched Qt event into an AppEvent, without consuming it."""
        if watched is self._widget and event.type() == self.watched_event_type:
            self.emit_event(self._build_event(event))

        # Never consume the event - the widget must still receive it.
        return super().eventFilter(watched, event)


class KeyPressAdapter(_WidgetEventAdapter):
    """
    Adapter for Qt key press events.
    Turns every key press on the watched widget into a SWITCH_PRESSED AppEvent.
    """

    watched_event_type = QEvent.Type.KeyPress

    def _build_event(self, event: QEvent) -> AppEvent:
        return AppEvent(
            AppEventType.SWITCH_PRESSED,
            {"key": event.key(), "text": event.text(), "modifiers": event.modifiers()},
        )


class MousePressAdapter(_WidgetEventAdapter):
    """
    Adapter for Qt mouse press events.
    Turns every mouse press on the watched widget into a SWITCH_PRESSED AppEvent.

    Currently unused: the switch is bound to the space key instead of the mouse.
    Kept as part of the adapter layer for alternative switch hardware.
    """

    watched_event_type = QEvent.Type.MouseButtonPress

    def _build_event(self, event: QEvent) -> AppEvent:
        return AppEvent(AppEventType.SWITCH_PRESSED, {})


class TimerAdapter(QtEventAdapter):
    """Adapter for timer events - converts QTimer to event-based system"""

    def __init__(self, interval_ms: int, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._on_timeout)
        self._interval_ms = interval_ms

    def start(self):
        """Start the timer"""
        self._timer.start(self._interval_ms)

    def stop(self):
        """Stop the timer"""
        self._timer.stop()

    def is_active(self) -> bool:
        """Check if timer is active"""
        return self._timer.isActive()

    def _on_timeout(self):
        """Emit timeout event - this triggers the next scanning step"""
        event = AppEvent(AppEventType.TIMER_TIMEOUT, None)
        self.emit_event(event)
