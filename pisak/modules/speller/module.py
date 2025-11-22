"""
Modul Speller aplikacji PISAK.
Umozliwia korzystanie z wirtualnej klawiatury oraz wyswietlanie pisanego tekstu na wyswietlaczu.

W celu przyspieszenia komunikacji dostepne sa takze predykcje nastepnego slowa.

Funkcjonalnosci:
- pisanie za pomoca wirtualnej klawiatury z zaimplementowanym systemem switch-scanning
- wybieranie slowa z listy predykcji
- czytanie na glos napisanego tekstu
- czyszczenie wyswietlacza z napisanego tekstu
- zapisanie napisanego tekstu do pliku
- wczytanie wczesniej napisanego tekstu z pliku
- mozliwosc powrotu do menu glownego
"""

from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt

from pisak.components.display_keyboard_component import KeyboardDisplayComponent
from pisak.modules.base_module import PisakBaseModule
from pisak.widgets.stacked_widgets import StackedWidgetObserver
from pisak.adapters import KeyPressAdapter
from pisak.events import AppEvent, AppEventType
from pisak.handlers import EventHandler


class PisakSpellerModule(PisakBaseModule):
    """
    Podstawa modulu jest PisakSpellerModule, ktory dziedziczy po PisakBaseModule.
    
    This module provides a virtual keyboard interface for text input.
    The keyboard emits events that are handled by the text display widget.
    Real keyboard input is ignored - only virtual keyboard events are processed.
    """

    def __init__(self, parent=None):
        """
        :param QWidget parent: obiekt-rodzic modułu Speller
        """
        super().__init__(parent=parent, title="Speller")

        # Create keyboard display component which sets up:
        # - Text display widget (ignores real keyboard input)
        # - Virtual keyboard with buttons
        # - Event connections: keyboard -> text display observer
        self._keyboard_component = KeyboardDisplayComponent(self.centralWidget())

        # Subscribe to stacked widget events for scanning management
        # This handles keyboard switching events
        self._keyboard_component._keyboards.subscribe(
            StackedWidgetObserver(self._scanning_manager)
        )
        
        # Set up keyboard adapter to capture key "1" for scanning control
        self._key_adapter = KeyPressAdapter(self, parent=self)
        self._key_adapter.subscribe(ScanningKeyHandler(self._scanning_manager, self._keyboard_component._keyboards))

        self.init_ui()

    def init_ui(self):
        super().init_ui()
        self.centralWidget().set_layout()


class ScanningKeyHandler(EventHandler):
    """Handler for key "1" to control scanning"""
    
    def __init__(self, scanning_manager, keyboards_container):
        self._scanning_manager = scanning_manager
        self._keyboards_container = keyboards_container
    
    def handle_event(self, event: AppEvent) -> None:
        """Handle key press events - only process key "1" """
        if event.type != AppEventType.KEY_PRESSED:
            return
        
        key_data = event.data
        if not isinstance(key_data, dict):
            return
        
        key = key_data.get('key')
        text = key_data.get('text', '')
        # Check for key "1" - can be Qt.Key_1, ASCII code 0x31, or text '1'
        # In PySide6, key codes might vary, so check multiple possibilities
        is_key_1 = (text == '1' or 
                   key == 0x31 or  # ASCII code for '1'
                   key == getattr(Qt, 'Key_1', None) or
                   key == getattr(Qt.Key, 'Key_1', None))
        
        if is_key_1:
            if not self._scanning_manager.is_scanning:
                # Start scanning from the current keyboard
                current_keyboard = self._keyboards_container.currentWidget()
                if current_keyboard:
                    # Check if it's a scannable item (has scannable_items property)
                    scannable_items = getattr(current_keyboard, 'scannable_items', [])
                    if len(scannable_items) > 0:
                        self._scanning_manager.start_scanning(current_keyboard)
            else:
                # Activate the currently focused item
                self._scanning_manager.activate_current_item()




