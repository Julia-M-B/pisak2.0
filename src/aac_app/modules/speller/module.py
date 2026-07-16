"""
The Speller module of the application.
Enables using a virtual keyboard and displaying the typed text on a display.

To speed up communication, next-word predictions are also available.

Features:
- typing with a virtual keyboard using the switch-scanning system
- selecting a word from the prediction list
- reading the typed text aloud
- clearing the typed text from the display
- saving the typed text to a file
- loading previously typed text from a file
- the ability to return to the main menu
"""

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence, QShortcut

from aac_app.adapters import KeyPressAdapter
from aac_app.components.action_buttons_column_component import (
    ActionButtonsColumnComponent,
    ActionButtonsHandler,
)
from aac_app.components.column_components import WordColumnComponent
from aac_app.components.display_keyboard_component import KeyboardDisplayComponent
from aac_app.components.keyboard import ButtonClickHandler, ButtonManager
from aac_app.events import AppEvent, AppEventType
from aac_app.experiment import close_experiment_recorder, get_experiment_recorder
from aac_app.logging_config import get_module_logger
from aac_app.modules.base_module import PisakBaseModule
from aac_app.predictions.prediction_handler import PredictionHandler
from aac_app.widgets.buttons import ButtonType
from aac_app.widgets.containers import PisakRowWidget

logger = get_module_logger(file_name="aac_app", logger_name=__name__)


class PisakSpellerModule(PisakBaseModule):
    """
    The core of the module is PisakSpellerModule, which inherits from PisakBaseModule.

    This module provides a virtual keyboard interface for text input with word prediction.
    The keyboard emits events that are handled by the text display widget.
    Real keyboard input is ignored - only virtual keyboard events are processed.
    """

    def __init__(self, parent=None):
        """
        :param QWidget parent: parent object of the Speller module
        """
        super().__init__(parent=parent, title="Speller")
        self.set_central_widget(PisakRowWidget(parent=self))

        # Create Components
        words = ["CZEŚĆ", "CZY", "JAK", "JESTEM", "NIE"]
        self._word_column = WordColumnComponent(self.centralWidget(), words=words)
        self._keyboard_component = KeyboardDisplayComponent(
            self.centralWidget(), scanning_manager=self._scanning_manager
        )

        # Create Action Buttons Column - must be created after keyboard_component and word_column
        self._action_column = ActionButtonsColumnComponent(parent=self.centralWidget())
        self._action_button_manager = ButtonManager()
        self._buttons_clicked_handler = ButtonClickHandler(
            button_manager=self._action_button_manager
        )
        self._action_button_handler = ActionButtonsHandler(
            module=self,
            scanning_manager=self._scanning_manager,
            text_display=self._keyboard_component.display,
        )

        self._action_button_handler.add_item_reference(
            self._keyboard_component, "KEYBOARDS"
        )
        self._action_button_handler.add_item_reference(self._word_column, "PREDICTIONS")
        self._action_button_handler.add_item_reference(self._action_column, "ACTIONS")

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
            word_column=self._word_column, n_words=len(words)
        )
        # Subscribe prediction handler to text display events
        self._keyboard_component.display.subscribe(self._prediction_handler)

        # Set up scanning to control the Main Row (switching between WordColumn and RightColumn)
        self._switch_handler = ScanningSwitchHandler(
            self._scanning_manager, self.centralWidget()
        )
        self._key_adapter = KeyPressAdapter(self, parent=self)
        self._key_adapter.subscribe(self._switch_handler)
        # Fallback shortcut so SPACE works even when focus is on child widgets (e.g. buttons).
        self._space_shortcut = QShortcut(QKeySequence(Qt.Key_Space), self)
        self._space_shortcut.activated.connect(self._on_space_shortcut)

        self.init_ui()

    def closeEvent(self, event):
        """Clean up resources when module is closed"""

        current_text = self._action_button_handler.text_display.text
        get_experiment_recorder().record(
            module=__name__,
            action="EXITING APP",
            event_type=ButtonType.EXIT,
            text=current_text,
        )

        # Stop the prediction service thread
        if hasattr(self, "_prediction_handler"):
            self._prediction_handler.stop()
        close_experiment_recorder()
        super().closeEvent(event)

    def _on_space_shortcut(self):
        self._switch_handler.handle_event(
            AppEvent(AppEventType.SWITCH_PRESSED, {"key": Qt.Key_Space})
        )


class ScanningSwitchHandler:
    """Handler for SPACE key to control scanning."""

    def __init__(self, scanning_manager, main_scannable_item):
        self._scanning_manager = scanning_manager
        self._main_scannable_item = main_scannable_item
        self._switch_pressed_counter = 0

    def handle_event(self, event: AppEvent) -> None:
        """Handle key press events - only process SPACE."""
        if event.type != AppEventType.SWITCH_PRESSED:
            return

        key_data = event.data
        if not isinstance(key_data, dict):
            return

        if key_data.get("key") != Qt.Key_Space:
            return

        self._switch_pressed_counter += 1
        get_experiment_recorder().record(
            module=__name__,
            action="SWITCH PRESSED",
            additional=self._switch_pressed_counter,
        )
        if not self._scanning_manager.is_scanning:
            # Start scanning from the main row (word column + keyboards)
            scannable_items = getattr(self._main_scannable_item, "scannable_items", [])
            if len(scannable_items) > 0:
                self._scanning_manager.start_scanning(self._main_scannable_item)
        else:
            # Activate the currently focused item
            self._scanning_manager.activate_current_item()
