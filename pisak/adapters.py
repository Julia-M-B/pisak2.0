"""
UI Adapter Layer - bridges framework-specific UI events to framework-agnostic events.
This layer isolates PySide6 dependencies from business logic.

Idea tego pliku jest taka, zeby nie mieszac PySide-owych sygnalow z wewnetrznymi eventami;
wszystkie powiazania miedzy sygnalami a eventami sa zalatwiane przez adaptery, ktore dokonuja konwersji
sygnalu PySide'owego na wewnetrzny event.
"""
from typing import Optional
from PySide6.QtWidgets import QWidget, QPushButton
from PySide6.QtCore import QObject, QTimer
from PySide6.QtGui import QKeyEvent

from pisak.emitters import EventEmitter
from pisak.events import AppEvent, AppEventType


class QtEventAdapter(EventEmitter, QObject):
    """
    Bazowa klasa dla adapterow sygnalow z PySide6 na wewnetrzne eventy.
    Dziedziczy po EventEmitterze oraz QObject.
    """

    def __init__(self, parent: Optional[QObject] = None):
        QObject.__init__(self, parent)
        EventEmitter.__init__(self)


class ButtonClickAdapter(QtEventAdapter):
    """
    Adapter sygnalu klikniecia na przycisk (`.clicked`).
    Gdy przycisk zostaje klikniety, adapter emituje odpowiedni event (BUTTON_CLICKED)
    """

    def __init__(self, button: QPushButton, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._button = button
        # Connect Qt signal to our event system
        button.clicked.connect(self._on_button_clicked)

    def _on_button_clicked(self):
        """Convert Qt clicked signal to AppEvent"""
        event = AppEvent(AppEventType.BUTTON_CLICKED, self._button)
        self.emit_event(event)


class KeyPressAdapter(QtEventAdapter):
    """
    Adapter PySide'owego eventu `keyPressEvent`.
    Do implementacji `keyPressEvent` danego widgetu dodaje emitowanie
    eventu (troche dziala jak dekorator).
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
        app_event = AppEvent(AppEventType.KEY_PRESSED, {
            'key': event.key(),
            'text': event.text(),
            'modifiers': event.modifiers()
        })
        self.emit_event(app_event)


class FocusAdapter(QtEventAdapter):
    """
    Adapter dla PySide'owych eventow zwiazanych ze zmianami focusu.
    Do implementacji focusowych eventow danego widgetu dodaje emitowanie
    odpowiedniego wewnetrznego eventu (troche dziala jak dekorator).
    """

    def __init__(self, widget: QWidget, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._widget = widget
        self._original_focus_in = widget.focusInEvent
        self._original_focus_out = widget.focusOutEvent

        # Override focus events
        widget.focusInEvent = self._on_focus_in
        widget.focusOutEvent = self._on_focus_out

    def _on_focus_in(self, event):
        """Convert Qt focusInEvent to AppEvent"""
        if self._original_focus_in:
            self._original_focus_in(event)

        app_event = AppEvent(AppEventType.WIDGET_FOCUSED, self._widget)
        self.emit_event(app_event)

    def _on_focus_out(self, event):
        """Convert Qt focusOutEvent to AppEvent"""
        if self._original_focus_out:
            self._original_focus_out(event)

        app_event = AppEvent(AppEventType.WIDGET_UNFOCUSED, self._widget)
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

