from typing import Optional, Self
from dataclasses import dataclass

from pisak.emitters import EventEmitter
from pisak.events import AppEvent, AppEventType
from pisak.scanning.scannable import PisakScannableItem
from pisak.settings import SCAN_HIGHLIGHT_TIME, SCAN_LOOP_NUMBER
from pisak.adapters import TimerAdapter
from pisak.handlers import TimerTimeoutHandler

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
    Manager skanowania - zarzadza skanowaniem w calej aplikacji.
    Zarzadza eventami zwiazanymi ze skanowaniem.
    Implementuje design observera;

    Glowna idea: ScanningManager zarzadza, ktory obiekt jest aktualnie skanowany.
    Rozpoczyna, resetuje oraz konczy skanowanie. Pilnuje, aby skanowanie odbywalo sie
    wg okreslonych zasad (np. tyle i tyle razy; w takiej i takiej kolejnosci).
    Gdy w skanowaniu zajdzie jakakolwiek zmiana, ScanningManager informuje o tym
    swoich obserwatorow, wysylajac do nich event odpowiedniego typu.
    Kazdy z obserwatorow implementuje odpowiednia reakcje na otrzymany event.
    """

    def __init__(self):
        super().__init__()
        self._timer = TimerAdapter(int(SCAN_HIGHLIGHT_TIME * 1000))
        self._timer.subscribe(TimerTimeoutHandler(scanning_manager=self))

        self._scanning_state = ScanningState()

    def start_scanning(self, item: PisakScannableItem) -> None:
        """Start scanning a scannable item"""
        # Stop any existing scanning first
        if self._scanning_state.is_scanning:
            self.stop_scanning()
        
        # Ensure timer is stopped before starting new scan
        if self._timer.is_active():
            self._timer.stop()
        
        # Set new scanning state (this increments scan_id)
        self._scanning_state.set_is_scanning(True).set_current_item(item).set_loops_counter(0)

        iter(item)

        # Start timer
        self._timer.start()

        # Emit event
        self.emit_event(AppEvent(AppEventType.SCANNING_STARTED, item))
        self._focus_next_item()

    def stop_scanning(self) -> None:
        """Stop current scanning"""
        if not self._scanning_state.is_scanning:
            return

        self._timer.stop()
        
        # Reset iterator counter on old item before clearing it
        current_item = self._scanning_state.current_item
        if current_item:
            current_item.iter_counter = 0
            current_item.reset_highlight_self()
        
        # Clear current item and set scanning to False
        self._scanning_state.set_is_scanning(False).set_current_item(None)

        self.emit_event(AppEvent(AppEventType.SCANNING_STOPPED))

    def activate_current_item(self):
        """
        Funkcja aktywujaca obiekt, ktory aktualnie ma focus.
        Aktywacja oznacza w tym przypadku, ze w trakcie skanowania pojawil sie input z zewnatrz
        (np. wcisniecie przycisku na fizycznej klawiaturze lub nacisniecie switcha).
        W zwiazku z tym aktywowany zostaje obiekt, ktory w danym momencie mial focus (wg zasady systemu switch-scanning).
        """
        if not self._scanning_state.is_scanning or not self._scanning_state.current_item:
            return

        current_item = self._scanning_state.current_item

        # Get the focused widget within the current item
        focused_widget = current_item.focusWidget()

        if focused_widget and focused_widget in current_item.scannable_items:
            # Emit activation event
            self.emit_event(AppEvent(AppEventType.ITEM_ACTIVATED, focused_widget))

            # Handle activation based on item type
            self._handle_item_activation(focused_widget, current_item)
        else:
            # No focused widget, activate the item itself
            # taka sytuacja moze byc np. gdy odpalamy aplikacje i jeszcze nic nie jest skanowane
            # lub gdy chcemy reaktywowac skanowanie po tym, jak skanowanie ustalo
            self.emit_event(AppEvent(AppEventType.ITEM_ACTIVATED, current_item))
            self._handle_item_activation(current_item, current_item)

    def _handle_item_activation(self, activated_item: PisakScannableItem, parent_item: PisakScannableItem):
        """
        Funkcja okreslajaca, jak nalzey zachowac sie, gdy obiekt zostal aktywowany.
        W zaleznosci od typu aktywowanego obiektu, nalezy podjac rozne dzialania.
        """
        # Check if activated item is a button - if so, trigger button action via event system
        # This ensures button clicks work both from mouse and scanning activation
        from pisak.widgets.buttons import PisakButton
        if isinstance(activated_item, PisakButton):
            self.emit_event(AppEvent(AppEventType.BUTTON_CLICKED, activated_item))
            
            # Check if scanning state was modified by handlers (e.g. keyboard switch)
            # If handlers started a new scan (current_item changed and is valid),
            # and it's different from the parent context we are handling here,
            # then we should NOT interfere/stop it.
            if self.is_scanning and self.current_item != parent_item:
                return

        # Stop current scanning
        self.stop_scanning()

        # If the activated item has scannable items (e.g., a row with buttons),
        # start scanning those items
        if len(activated_item.scannable_items) > 0:
            self.start_scanning(activated_item)
            return

        # If the activated item has no scannable items (e.g., a button),
        # use the parent's strategy to go back up the hierarchy
        # This ensures buttons go back to keyboard level, not just row level
        strategy = parent_item.scanning_strategy if parent_item else activated_item.scanning_strategy
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
        if not self._scanning_state.is_scanning or not self._scanning_state.current_item:
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
        scannable_items = getattr(current_item, 'scannable_items', [])
        if current_item.iter_counter >= self._scanning_state.max_loop_number * len(scannable_items):
            self._reset_scanning()
            return

        self._focus_next_item()

    def _focus_next_item(self):
        """Focus the next item in the scanning sequence"""
        if not self._scanning_state.is_scanning or not self._scanning_state.current_item:
            return

        current_item = self._scanning_state.current_item

        focused_item = next(current_item)
        focused_item.setFocus()

    def _reset_scanning(self):
        """Reset scanning to parent or stop"""
        if not self._scanning_state.is_scanning or not self._scanning_state.current_item:
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

