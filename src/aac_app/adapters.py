"""
UI Adapter Layer - bridges framework-specific UI events to framework-agnostic events.
This layer isolates PySide6 dependencies from business logic.

The idea of this file is to avoid mixing PySide signals with internal events;
all bindings between signals and events are handled by adapters, which convert
a PySide signal into an internal event.
"""

from typing import Optional

from PySide6.QtCore import QObject, QTimer
from PySide6.QtGui import QKeyEvent
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


class KeyPressAdapter(QtEventAdapter):
    """
    Adapter for the PySide `keyPressEvent`.
    Adds event emission to a widget's `keyPressEvent` implementation
    (works a bit like a decorator).
    """

    def __init__(self, widget: QWidget, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._widget = widget
        self._original_key_press = widget.keyPressEvent
        # Override keyPressEvent to emit events
        widget.keyPressEvent = self._on_key_press

    def _on_key_press(self, event: QKeyEvent):
        """Convert Qt keyPressEvent to AppEvent"""
        # Call original handler first
        if self._original_key_press:
            self._original_key_press(event)

        # Emit framework-agnostic event
        app_event = AppEvent(
            AppEventType.SWITCH_PRESSED,
            {"key": event.key(), "text": event.text(), "modifiers": event.modifiers()},
        )
        self.emit_event(app_event)


class MousePressAdapter(QtEventAdapter):
    """
    Adapter for the PySide `mousePressEvent`.
    Adds event emission to a widget's `mousePressEvent` implementation
    (works a bit like a decorator).
    """

    def __init__(self, widget: QWidget, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._widget = widget
        self._original_mouse_press = widget.mousePressEvent
        # Override mousePressEvent to emit events
        widget.mousePressEvent = self._on_mouse_press

    def _on_mouse_press(self, event: QKeyEvent):
        """Convert Qt mousePressEvent to AppEvent"""
        # Call original handler first
        if self._original_mouse_press:
            self._original_mouse_press(event)

        # Emit framework-agnostic event
        app_event = AppEvent(
            AppEventType.SWITCH_PRESSED,
            {
                # 'key': event.key(),
                # 'text': event.text(),
                # 'modifiers': event.modifiers()
            },
        )
        self.emit_event(app_event)


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
