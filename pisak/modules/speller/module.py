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
from pisak.components.column_components import WordColumnComponent
from pisak.components.action_buttons_column_component import ActionButtonsColumnComponent, ActionButtonsHandler
from pisak.components.keyboard import ButtonManager, ButtonClickHandler
from pisak.modules.base_module import PisakBaseModule
from pisak.adapters import KeyPressAdapter
from pisak.events import AppEvent, AppEventType
from pisak.widgets.containers import PisakRowWidget
from pisak.predictions.prediction_handler import PredictionHandler

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
        self._word_column = WordColumnComponent(self.centralWidget(), words=words)
        self._keyboard_component = KeyboardDisplayComponent(self.centralWidget(), scanning_manager=self._scanning_manager)
        
        # Create Action Buttons Column - must be created after keyboard_component and word_column
        self._action_column = ActionButtonsColumnComponent(parent=self.centralWidget())
        self._action_button_manager = ButtonManager()
        self._buttons_clicked_handler = ButtonClickHandler(button_manager=self._action_button_manager)
        self._action_button_handler = ActionButtonsHandler(module=self, scanning_manager=self._scanning_manager, text_display=self._keyboard_component.display)
        self._action_button_handler.add_item_reference(self._keyboard_component, "KEYBOARDS")
        self._action_button_handler.add_item_reference(self._word_column, "PREDICTIONS")

        self._scanning_manager.subscribe(self._buttons_clicked_handler)

        self._action_button_manager.subscribe(self._action_button_handler)

        # Add components to layout: Action Column (left) | Word Column | Keyboard Component (right)
        self.centralWidget().add_item(self._action_column)
        self.centralWidget().add_item(self._word_column)
        self.centralWidget().add_item(self._keyboard_component)
        self.centralWidget().set_layout()
        
        # Apply Stretches: Action Column (1/5) | Word Column (1/5) | Keyboard (3/5)
        # To achieve 1/5 width for action column: use ratio 1:1:3 for a total of 5 parts
        self.centralWidget().layout.setStretch(0, 1)  # Action column: 1/5
        self.centralWidget().layout.setStretch(1, 1)  # Word column: 1/5
        self.centralWidget().layout.setStretch(2, 3)  # Keyboard: 3/5

        # Set up word prediction system
        # Connect text display changes to word column updates via threaded prediction service
        self._prediction_handler = PredictionHandler(
            word_column=self._word_column,
            n_words=len(words)
        )
        # Subscribe prediction handler to text display events
        self._keyboard_component.display.subscribe(self._prediction_handler)

        # Set up scanning to control the Main Row (switching between WordColumn and RightColumn)
        self._key_adapter = KeyPressAdapter(self, parent=self)
        self._key_adapter.subscribe(ScanningKeyHandler(self._scanning_manager, self.centralWidget()))

        self.init_ui()
    
    def closeEvent(self, event):
        """Clean up resources when module is closed"""
        # Stop the prediction service thread
        if hasattr(self, '_prediction_handler'):
            self._prediction_handler.stop()
        super().closeEvent(event)

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




