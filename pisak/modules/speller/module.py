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
from pisak.components.word_column_component import WordColumnComponent
from pisak.modules.base_module import PisakBaseModule
from pisak.adapters import KeyPressAdapter
from pisak.events import AppEvent, AppEventType
from pisak.widgets.containers import PisakRowWidget

class PisakSpellerModule(PisakBaseModule):
    """
    Podstawa modulu jest PisakSpellerModule, ktory dziedziczy po PisakBaseModule.
    
    This module provides a virtual keyboard interface for text input with word prediction.
    The keyboard emits events that are handled by the text display widget.
    Real keyboard input is ignored - only virtual keyboard events are processed.
    """

    def __init__(self, parent=None):
        """
        :param QWidget parent: obiekt-rodzic modułu Speller
        """
        super().__init__(parent=parent, title="Speller")
        self.set_central_widget(PisakRowWidget(parent=self))

        # Create Components
        words = ["TEST1", "TEST2", "TEST3", "TEST4", "TEST5", 
                 "TEST6", "TEST7", "TEST8", "TEST9", "TEST10"]
        words2 = ["TEST1", "TEST2", "TEST3", "TEST4", "TEST5",
                 "TEST6", "TEST7", "TEST8", "TEST9", "TEST10"]
        self._word_column = WordColumnComponent(self.centralWidget(), words=words)
        self._word_column2 = WordColumnComponent(self.centralWidget(), words=words2)
        self._keyboard_component = KeyboardDisplayComponent(self.centralWidget(), scanning_manager=self._scanning_manager)


        self.centralWidget().add_item(self._word_column.column)
        self.centralWidget().add_item(self._word_column2.column)
        self.centralWidget().add_item(self._keyboard_component)
        self.centralWidget().set_layout()
        
        # Apply Stretches
        self.centralWidget().layout.setStretch(0, 1)
        self.centralWidget().layout.setStretch(1, 2)
        self.centralWidget().layout.setStretch(2, 4)

        # Set up scanning to control the Main Row (switching between WordColumn and RightColumn)
        self._key_adapter = KeyPressAdapter(self, parent=self)
        self._key_adapter.subscribe(ScanningKeyHandler(self._scanning_manager, self.centralWidget()))

        self.init_ui()

class ScanningKeyHandler:
    """Handler for key "1" to control scanning"""
    
    def __init__(self, scanning_manager, main_scannable_item):
        self._scanning_manager = scanning_manager
        self._main_scannable_item = main_scannable_item
    
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
                # Start scanning from the main row (word column + keyboards)
                scannable_items = getattr(self._main_scannable_item, 'scannable_items', [])
                if len(scannable_items) > 0:
                    self._scanning_manager.start_scanning(self._main_scannable_item)
            else:
                # Activate the currently focused item
                self._scanning_manager.activate_current_item()




