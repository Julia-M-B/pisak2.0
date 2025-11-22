from PySide6.QtWidgets import QStackedWidget

from pisak.emitters import EventEmitter
from pisak.events import AppEvent, AppEventType
from pisak.scanning.scannable import PisakScannableItem

class PisakStackedWidget(EventEmitter, QStackedWidget, PisakScannableItem):
    """
    Przechowuje różne obiekty i zarządza ich wyświetlaniem:
    - np. może wyświetlać różne keyboardy lub może wyświetlać różne moduły
    """

    def __init__(self, parent):
        # Initialize parent classes explicitly to avoid MRO issues
        EventEmitter.__init__(self)
        QStackedWidget.__init__(self, parent)
        # PisakScannableItem is a protocol/mixin, no __init__ needed
        self._items_dict = {}
        self._items = []
        self._scannable_items = []

    def add_item(self, item):
        self._items.append(item)
        self.addWidget(item)
        if isinstance(item, PisakScannableItem):
            self._scannable_items.append(item)

    def add_item_reference(self, item, key):
        if key not in self._items_dict.keys():
            self._items_dict[key] = item

    # docelowo PisakStackedWidget będzie pewnie przechowywać obiekty różne,
    # nie tylko klawiatury
    # todo dodać jakieś ogólne typowanie, że klucz to ma być typ obiektu
    def get_item_by_key(self, key):
        return self._items_dict.get(key, None)

    @property
    def scannable_items(self):
        """Return scannable items from the currently visible widget"""
        current_widget = self.currentWidget()
        if current_widget and isinstance(current_widget, PisakScannableItem):
            return current_widget.scannable_items
        return []

    def __iter__(self):
        """Iterate through scannable items of the currently visible widget"""
        current_widget = self.currentWidget()
        if current_widget and isinstance(current_widget, PisakScannableItem):
            # Delegate iteration to the current widget
            self._iter_items = iter(current_widget)
            return self
        # Fallback to empty iterator if no current widget
        self._iter_items = iter([])
        return self

    def __next__(self):
        """Get next item from the current widget's iterator"""
        if hasattr(self, '_iter_items'):
            return next(self._iter_items)
        raise StopIteration

    # TODO dodać funkcję, która będzie zarządzała wyświetlaniem obiektów
    #  należących do PisakStackedWidget -> jak zmieni wyświetlany obiekt,
    #  to musi wysyłać sygnał do scanning managera, że obiekt został zmieniony
    #  wtedy scanning manager będzie kończył jedno skanowanie i rozpoczynał drugie
    def switch_shown_item(self, new_item):
        """
        Funkcja zmieniająca wyświetlany widget.
        Po zmianie wyświetlanego widgetu, emitowany jest sygnał "ITEMS_SWITCHED"
        zawierający informację o tym, jaki teraz jest wyświetlany widget (aby
        móc rozpocząć jego skanownanie)

        :param new_item:
        :return:
        """
        if new_item in self._items:
            self.setCurrentWidget(new_item)
            event = AppEvent(AppEventType.ITEMS_SWITCHED, new_item)
            self.emit_event(event)


class StackedWidgetObserver:
    """Observer that handles stacked widget events for scanning manager"""
    
    def __init__(self, scanning_manager):
        self._scanning_manager = scanning_manager

    def handle_event(self, event: AppEvent) -> None:
        """Handle items switched event - stop scanning old keyboard, start scanning new one"""
        if event.type == AppEventType.ITEMS_SWITCHED:
            new_keyboard = event.data
            from pisak.scanning.scannable import PisakScannableItem
            
            # Check if scanning is currently active and get the old keyboard reference
            was_scanning = self._scanning_manager.is_scanning
            old_keyboard = self._scanning_manager.current_item if was_scanning else None
            
            # Stop scanning the old keyboard completely
            if was_scanning:
                # Clear iterator state on old keyboard to prevent stale references
                if old_keyboard and hasattr(old_keyboard, '_iter_scannable_items'):
                    old_keyboard._iter_scannable_items = None
                if old_keyboard:
                    old_keyboard.iter_counter = 0
                
                self._scanning_manager.stop_scanning()
            
            # Verify we're not scanning anymore before starting new scan
            if self._scanning_manager.is_scanning:
                # If still scanning, force stop
                self._scanning_manager.stop_scanning()
            
            # If scanning was active and new keyboard is scannable, start scanning it
            if was_scanning and isinstance(new_keyboard, PisakScannableItem):
                scannable_items = getattr(new_keyboard, 'scannable_items', [])
            if len(scannable_items) > 0:
                # Verify old keyboard is different from new keyboard
                if old_keyboard != new_keyboard:
                    
                    # Clear any existing iterator state on new keyboard
                    if hasattr(new_keyboard, '_iter_scannable_items'):
                        new_keyboard._iter_scannable_items = None
                    new_keyboard.iter_counter = 0
                    
                    # Ensure we're definitely not scanning before starting
                    if self._scanning_manager.is_scanning:
                        self._scanning_manager.stop_scanning()
                    
                    # Start scanning the new keyboard
                    self._scanning_manager.start_scanning(new_keyboard)


