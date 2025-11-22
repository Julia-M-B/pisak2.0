from typing_extensions import Protocol

from pisak.events import AppEvent, AppEventType


class EventHandler(Protocol):
    """
    Protokol EventHandlera. Zeby obiekt byl rozpoznawany jako EventHandler
    musi implementowac metode `.handle_event(event: AppEvent)`.
    """
    def handle_event(self, event: AppEvent):
        ...


class TimerTimeoutHandler:
    """Handler for timer timeout events"""

    def __init__(self, scanning_manager):
        self._scanning_manager = scanning_manager

    def handle_event(self, event: AppEvent) -> None:
        """Handle timer timeout event"""
        if event.type == AppEventType.TIMER_TIMEOUT:
            self._scanning_manager._on_timer_timeout()
