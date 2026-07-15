from typing import Optional

try:
    from typing import Self
except ImportError:
    from typing_extensions import Self

from dataclasses import dataclass

from aac_app.adapters import TimerAdapter
from aac_app.emitters import EventEmitter
from aac_app.events import AppEvent, AppEventType
from aac_app.handlers import TimerTimeoutHandler
from aac_app.logging_config import get_module_logger
from aac_app.scanning.scannable import PisakScannableItem
from aac_app.settings import SCAN_HIGHLIGHT_TIME, SCAN_LOOP_NUMBER, SCAN_START_DELAY

logger = get_module_logger(file_name="scanning", logger_name=__name__, experiment=True)


@dataclass
class ScanningState:
    is_scanning: bool = False
    current_item: Optional[PisakScannableItem] = None
    loops_counter: int = 0
    max_loop_number = SCAN_LOOP_NUMBER

    def __iadd__(self, value: int) -> None:
        self.loops_counter += value

    def set_is_scanning(self, state: bool) -> Self:
        self.is_scanning = state
        return self

    def set_current_item(self, item: Optional[PisakScannableItem]) -> Self:
        self.current_item = item
        return self

    def set_loops_counter(self, value: int) -> Self:
        self.loops_counter = value
        return self


class ScanningManager(EventEmitter):
    """
    Scanning manager - manages scanning across the whole application.
    Manages scanning-related events.
    Implements the observer pattern.

    Main idea: ScanningManager manages which item is currently being scanned.
    It starts, resets, and stops scanning. It ensures scanning follows
    defined rules (e.g. a given number of times; in a given order).
    Whenever any change occurs in scanning, ScanningManager notifies
    its observers by sending them an event of the appropriate type.
    Each observer implements its own reaction to the received event.
    """

    def __init__(self):
        super().__init__()
        self._timer = TimerAdapter(int(SCAN_HIGHLIGHT_TIME * 1000))
        self._timer.subscribe(TimerTimeoutHandler(scanning_manager=self))
        self._start_delay_timer = TimerAdapter(int(SCAN_START_DELAY * 1000))
        self._start_delay_timer.subscribe(self._DelayedStartHandler(self))

        self._scanning_state = ScanningState()
        self._pending_start_token = 0

    def start_scanning(self, item: PisakScannableItem) -> None:
        """Start scanning a scannable item"""
        # Stop any existing scanning first
        if self._scanning_state.is_scanning:
            self.stop_scanning()

        # Ensure timer is stopped before starting new scan
        if self._timer.is_active():
            self._timer.stop()
        if self._start_delay_timer.is_active():
            self._start_delay_timer.stop()

        # Set new scanning state (this increments scan_id)
        self._scanning_state.set_is_scanning(True).set_current_item(
            item
        ).set_loops_counter(0)

        iter(item)

        # Delay first highlight to make choosing first child item easier.
        self._pending_start_token += 1

        # Emit event
        self.emit_event(AppEvent(AppEventType.SCANNING_STARTED, item))
        self._start_delay_timer.start()

        logger.info("Started scanning item %s", self._scanning_state.current_item)

    def stop_scanning(self) -> None:
        """Stop current scanning"""
        if not self._scanning_state.is_scanning:
            return

        self._timer.stop()
        if self._start_delay_timer.is_active():
            self._start_delay_timer.stop()
        self._pending_start_token += 1

        # Reset iterator counter on old item before clearing it
        current_item = self._scanning_state.current_item
        logger.info("Stopped scanning item %s", self._scanning_state.current_item)
        if current_item:
            current_item.iter_counter = 0
            current_item.reset_highlight_self()

        # Clear current item and set scanning to False
        self._scanning_state.set_is_scanning(False).set_current_item(None)

        self.emit_event(AppEvent(AppEventType.SCANNING_STOPPED))

    def activate_current_item(self):
        """
        Activate the item that currently has focus.
        Activation here means that external input arrived during scanning
        (e.g. pressing a key on the physical keyboard or pressing the switch).
        As a result, the item that had focus at that moment is activated (following the switch-scanning principle).
        """
        if (
            not self._scanning_state.is_scanning
            or not self._scanning_state.current_item
        ):
            return

        current_item = self._scanning_state.current_item

        logger.info(f"Item activated (switch was pressed): {current_item}")

        # Get the focused widget within the current item
        focused_widget = current_item.focusWidget()

        if focused_widget and focused_widget in current_item.scannable_items:
            # Emit activation event
            self.emit_event(AppEvent(AppEventType.ITEM_ACTIVATED, focused_widget))

            # Handle activation based on item type
            self._handle_item_activation(focused_widget, current_item)
        else:
            # No focused widget, activate the item itself
            # this can happen e.g. when we start the app and nothing is being scanned yet
            # or when we want to reactivate scanning after it has stopped
            self.emit_event(AppEvent(AppEventType.ITEM_ACTIVATED, current_item))
            self._handle_item_activation(current_item, current_item)

    def _handle_item_activation(
        self, activated_item: PisakScannableItem, parent_item: PisakScannableItem
    ):
        """
        Determine how to behave when an item has been activated.
        Depending on the type of the activated item, different actions must be taken.
        """
        # Check if activated item is a button - if so, trigger button action via event system
        # This ensures button clicks work both from mouse and scanning activation
        from aac_app.widgets.buttons import ButtonType, PisakButton

        is_read_button = False
        if isinstance(activated_item, PisakButton):
            button_text = (
                activated_item.text
                if activated_item.text
                else activated_item.additional_data
            )
            logger.debug(f"BUTTON CLICKED,{activated_item.button_type},{button_text},")
            self.emit_event(AppEvent(AppEventType.BUTTON_CLICKED, activated_item))

            # Check if this is a READ button - if so, we should stop scanning completely
            # and not restart it (user wants to reset to initial state)
            if activated_item.button_type == ButtonType.READ:
                is_read_button = True

            # Check if scanning state was modified by handlers (e.g. keyboard switch)
            # If handlers started a new scan (current_item changed and is valid),
            # and it's different from the parent context we are handling here,
            # then we should NOT interfere/stop it.
            if self.is_scanning and self.current_item != parent_item:
                return

        # Stop current scanning
        self.stop_scanning()

        # If this is a READ button, stop scanning completely and reset to initial state
        # Don't restart scanning - user must press Enter to start scanning again
        if is_read_button:
            self.emit_event(AppEvent(AppEventType.SCANNING_RESET, None))
            return

        # If the activated item has scannable items (e.g., a row with buttons),
        # start scanning those items
        if len(activated_item.scannable_items) > 0:
            self.start_scanning(activated_item)
            return

        # If the activated item has no scannable items (e.g., a button),
        # use the parent's strategy to go back up the hierarchy
        # This ensures buttons go back to keyboard level, not just row level
        strategy = (
            parent_item.scanning_strategy
            if parent_item
            else activated_item.scanning_strategy
        )
        if strategy:
            # Use parent's strategy to go back, or activated item's strategy as fallback
            target_for_strategy = parent_item if parent_item else activated_item
            next_target = strategy.reset_scan(target_for_strategy)

            if isinstance(next_target, PisakScannableItem):
                # Continue scanning with new target
                self.start_scanning(next_target)
            else:
                # No more scanning targets
                self.emit_event(AppEvent(AppEventType.SCANNING_RESET, next_target))
        else:
            # No strategy, stop scanning
            self.emit_event(AppEvent(AppEventType.SCANNING_RESET, None))

    def _on_timer_timeout(self):
        """
        Handle timer timeout - focus next item
        """
        # Double-check scanning state - this prevents stale timer callbacks from affecting new scans
        if (
            not self._scanning_state.is_scanning
            or not self._scanning_state.current_item
        ):
            return

        # # Verify this callback is for the current scan session (not a stale callback)
        # if self._scanning_state.scan_id != self._active_scan_id:
        #     # This is a stale callback from a previous scan session, ignore it
        #     return

        current_item = self._scanning_state.current_item

        # Verify current_item is still valid (not None)
        if not current_item:
            return

        # Check if we've completed all loops
        scannable_items = getattr(current_item, "scannable_items", [])
        if current_item.iter_counter >= self._scanning_state.max_loop_number * len(
            scannable_items
        ):
            self._reset_scanning()
            return

        self._focus_next_item()

    def _on_start_delay_timeout(self, pending_token: int):
        """
        Start scanning ticks and first focus after configured startup delay.
        """
        # Delay timer should act like one-shot.
        if self._start_delay_timer.is_active():
            self._start_delay_timer.stop()

        if pending_token != self._pending_start_token:
            return
        if (
            not self._scanning_state.is_scanning
            or not self._scanning_state.current_item
        ):
            return

        self._timer.start()
        self._focus_next_item()

    def _focus_next_item(self):
        """Focus the next item in the scanning sequence"""
        if (
            not self._scanning_state.is_scanning
            or not self._scanning_state.current_item
        ):
            return

        current_item = self._scanning_state.current_item

        focused_item = next(current_item)
        focused_item.setFocus()

    def _reset_scanning(self):
        """Reset scanning to parent or stop"""
        if (
            not self._scanning_state.is_scanning
            or not self._scanning_state.current_item
        ):
            return

        current_item = self._scanning_state.current_item
        strategy = current_item.scanning_strategy

        if strategy:
            next_target = strategy.reset_scan(current_item)

            if isinstance(next_target, PisakScannableItem):
                self.start_scanning(next_target)
            else:
                self.stop_scanning()
                self.emit_event(AppEvent(AppEventType.SCANNING_RESET, next_target))
        else:
            self.stop_scanning()

    @property
    def is_scanning(self) -> bool:
        """Check if scanning is currently active"""
        return self._scanning_state.is_scanning

    @property
    def current_item(self) -> Optional[PisakScannableItem]:
        """Get currently scanned item"""
        return self._scanning_state.current_item

    class _DelayedStartHandler:
        """Bridges delayed timer timeout to manager callback."""

        def __init__(self, scanning_manager: "ScanningManager"):
            self._scanning_manager = scanning_manager

        def handle_event(self, event: AppEvent) -> None:
            if event.type == AppEventType.TIMER_TIMEOUT:
                token = self._scanning_manager._pending_start_token
                self._scanning_manager._on_start_delay_timeout(token)
