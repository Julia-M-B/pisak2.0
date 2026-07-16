from enum import Enum, auto

import yaml

from aac_app.emitters import EventEmitter
from aac_app.events import AppEvent, AppEventType
from aac_app.logging_config import get_module_logger
from aac_app.widgets.buttons import ButtonType, PisakButton, PisakButtonBuilder
from aac_app.widgets.containers import PisakColumnWidget, PisakRowWidget

logger = get_module_logger(file_name="components", logger_name=__name__)


class KeyboardType(Enum):
    UPPERCASE = auto()
    DIACRITICS = auto()
    NUMERICAL = auto()


KEYBOARD_TYPES_MAP = {
    "uppercase": KeyboardType.UPPERCASE,
    "diacritics": KeyboardType.DIACRITICS,
    "numerical": KeyboardType.NUMERICAL,
}


class Keyboard(PisakColumnWidget):
    def __init__(self, parent=None, strategy=None):
        super().__init__(parent, strategy)
        self._buttons = []

    @property
    def buttons(self):
        return self._buttons

    def implement_layout_from_config(self, config_path: str):
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)

        rows = config["rows"]

        for row in rows:
            row_widget = PisakRowWidget(parent=self)
            buttons = row["row"]
            for button_config in buttons:
                button_dict = button_config["button"]
                button_builder = PisakButtonBuilder().set_base_data(button_dict)
                button = button_builder.build(parent=row_widget)
                row_widget.add_item(button)
                self._buttons.append(button)
            row_widget.set_layout()
            self.add_item(row_widget)

        self.set_layout()


class ButtonManager(EventEmitter):
    """
    Button manager - when a button is clicked, it emits the appropriate kind of event
    depending on the button type.
    """

    def on_button_clicked(self, button: PisakButton):
        match button.button_type:
            case ButtonType.SPACE:
                self.emit_event(AppEvent(AppEventType.SPACE_ADDED))
            case ButtonType.BACKSPACE:
                self.emit_event(AppEvent(AppEventType.BACKSPACE_PRESSED))
            case ButtonType.CLEAR:
                self.emit_event(AppEvent(AppEventType.CLEAR_PRESSED))
            case ButtonType.ENTER:
                self.emit_event(AppEvent(AppEventType.NEW_LINE_ADDED))
            case ButtonType.LEFT_ARROW:
                self.emit_event(AppEvent(AppEventType.CURSOR_MOVED_LEFT))
            case ButtonType.RIGHT_ARROW:
                self.emit_event(AppEvent(AppEventType.CURSOR_MOVED_RIGHT))
            case ButtonType.UP_ARROW:
                self.emit_event(AppEvent(AppEventType.CURSOR_MOVED_UP))
            case ButtonType.DOWN_ARROW:
                self.emit_event(AppEvent(AppEventType.CURSOR_MOVED_DOWN))
            case ButtonType.SWITCHER:
                if button.additional_data is not None:
                    self.emit_event(
                        AppEvent(AppEventType.ITEMS_SWITCHED, button.additional_data)
                    )
            case ButtonType.POINTER:
                if button.additional_data is not None:
                    self.emit_event(
                        AppEvent(AppEventType.ITEM_POINTED, button.additional_data)
                    )
            case ButtonType.SAVE:
                self.emit_event(AppEvent(AppEventType.TEXT_SAVED))
            case ButtonType.UPLOAD:
                self.emit_event(AppEvent(AppEventType.TEXT_UPLOADED))
            case ButtonType.READ:
                self.emit_event(AppEvent(AppEventType.READ_TEXT))
            case ButtonType.EXIT:
                self.emit_event(AppEvent(AppEventType.MODULE_EXITED))
            case ButtonType.CHARACTER:
                self.emit_event(AppEvent(AppEventType.CHAR_ADDED, button.text()))
            case ButtonType.WORD:
                self.emit_event(AppEvent(AppEventType.WORD_ADDED, button.text()))
            case _:
                self.emit_event(AppEvent(AppEventType.CHAR_ADDED, button.text()))


class ButtonClickHandler:
    """
    Observes the scanning manager (which emits an event that a button was clicked)
    when the activated item is a PisakButton.
    Passes to the button manager the information that a button was clicked (and which button it was).
    """

    def __init__(self, button_manager: ButtonManager):
        self._button_manager = button_manager

    def handle_event(self, event: AppEvent) -> None:
        """Handle button click event from adapter"""
        if event.type == AppEventType.BUTTON_CLICKED:
            button = event.data
            if isinstance(button, PisakButton):
                self._button_manager.on_button_clicked(button)
