from typing_extensions import Protocol

from aac_app.events import AppEvent, AppEventType


class EventHandler(Protocol):
    """
    EventHandler protocol. For an object to be recognized as an EventHandler
    it must implement the `.handle_event(event: AppEvent)` method.
    """

    def handle_event(self, event: AppEvent): ...


class TimerTimeoutHandler:
    """Handler for timer timeout events"""

    def __init__(self, scanning_manager):
        self._scanning_manager = scanning_manager

    def handle_event(self, event: AppEvent) -> None:
        """Handle timer timeout event"""
        if event.type == AppEventType.TIMER_TIMEOUT:
            self._scanning_manager.on_scan_tick()
