from typing import Optional

try:
    from typing import Self
except ImportError:
    from typing_extensions import Self

from dataclasses import dataclass, field

from aac_app.adapters import TimerAdapter
from aac_app.emitters import EventEmitter
from aac_app.events import AppEvent, AppEventType
from aac_app.experiment import get_experiment_recorder
from aac_app.handlers import TimerTimeoutHandler
from aac_app.logging_config import get_module_logger
from aac_app.scanning.scannable import PisakScannableItem
from aac_app.settings import get_scanning_settings

logger = get_module_logger(file_name="scanning", logger_name=__name__)


@dataclass
class ScanningState:
    is_scanning: bool = False
    current_item: Optional[PisakScannableItem] = None
    loops_counter: int = 0
    # Annotated so that it is a real dataclass field: without the annotation it
    # would be a plain class attribute shared by every ScanningState instance.
    # Resolved per instance so that a command-line override is picked up.
    max_loop_number: int = field(
        default_factory=lambda: get_scanning_settings().loop_number
    )

    def __iadd__(self, value: int) -> Self:
        # Must return self: `state += 1` rebinds the name to whatever this
        # returns, so returning None would silently turn `state` into None.
        self.loops_counter += value
        return self

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
        # Read settings here rather than at import time, so that overrides applied
        # by the command line before the UI is built are respected.
        settings = get_scanning_settings()
        self._timer = TimerAdapter(int(settings.highlight_time * 1000))
        self._timer.subscribe(TimerTimeoutHandler(scanning_manager=self))
        self._start_delay_timer = TimerAdapter(int(settings.start_delay * 1000))
        self._start_delay_timer.subscribe(self._DelayedStartHandler(self))

        self._scanning_state = ScanningState()

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

        # Set new scanning state
        self._scanning_state.set_is_scanning(True).set_current_item(
            item
        ).set_loops_counter(0)

        iter(item)

        self.emit_event(AppEvent(AppEventType.SCANNING_STARTED, item))
        # Delay the first highlight to make choosing the first child item easier.
        self._start_delay_timer.start()

        logger.info("Started scanning item %s", self._scanning_state.current_item)

    def stop_scanning(self) -> None:
        """Stop current scanning"""
        if not self._scanning_state.is_scanning:
            return

        self._timer.stop()
        if self._start_delay_timer.is_active():
            self._start_delay_timer.stop()

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
            button_text = activated_item.text() or activated_item.additional_data
            get_experiment_recorder().record(
                module=__name__,
                action="BUTTON CLICKED",
                event_type=activated_item.button_type,
                text=button_text or "",
            )
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

    def on_scan_tick(self) -> None:
        """
        Handle a scanning timer tick - focus the next item.

        Part of the manager's API for its timer handlers (see `TimerTimeoutHandler`);
        not meant to be called from anywhere else.
        """
        # Double-check scanning state - this prevents stale timer callbacks from affecting new scans
        if (
            not self._scanning_state.is_scanning
            or not self._scanning_state.current_item
        ):
            return

        current_item = self._scanning_state.current_item

        # Check if we've completed all loops
        scannable_items = getattr(current_item, "scannable_items", [])
        if current_item.iter_counter >= self._scanning_state.max_loop_number * len(
            scannable_items
        ):
            self._reset_scanning()
            return

        self._focus_next_item()

    def on_start_delay_elapsed(self) -> None:
        """
        Start scanning ticks and first focus after the configured startup delay.

        Part of the manager's API for its timer handlers (see `_DelayedStartHandler`);
        not meant to be called from anywhere else.
        """
        # Delay timer should act like one-shot.
        if self._start_delay_timer.is_active():
            self._start_delay_timer.stop()

        # Guards against a stale callback: `stop_scanning` stops the timer and
        # clears the state, so a late tick must not focus anything.
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

        try:
            focused_item = next(current_item)
        except StopIteration:
            # The item has no scannable children - there is nothing to focus, so
            # stop instead of leaving a scan running over an empty container.
            logger.warning(
                "Item %s has no scannable children; stopping scanning", current_item
            )
            self.stop_scanning()
            return

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
                self._scanning_manager.on_start_delay_elapsed()
