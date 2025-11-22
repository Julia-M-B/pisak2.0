from enum import Enum, auto
import yaml
from pisak.emitters import EventEmitter
from pisak.events import AppEvent, AppEventType
from pisak.adapters import ButtonClickAdapter
from pisak.widgets.containers import PisakColumnWidget, PisakRowWidget
from pisak.widgets.buttons import PisakButtonBuilder, PisakButton, ButtonType
from pisak.widgets.stacked_widgets import PisakStackedWidget

class KeyboardType(Enum):
    UPPERCASE = auto()
    LOWERCASE = auto()
    NUMERICAL = auto()

KEYBOARD_TYPES_MAP = {
    "uppercase": KeyboardType.UPPERCASE,
    "lowercase": KeyboardType.LOWERCASE,
    "numerical": KeyboardType.NUMERICAL
}

class Keyboard(EventEmitter, PisakColumnWidget):
    def __init__(self, parent=None, keyboard_layout=None, keyboard_dim=(4, 7)):
        # Initialize parent classes explicitly to avoid MRO issues
        EventEmitter.__init__(self)
        PisakColumnWidget.__init__(self, parent)
        self._keyboard_layout = keyboard_layout
        self._keyboard_dim = keyboard_dim
        self._buttons = []

    @property
    def buttons(self):
        return self._buttons

    @staticmethod
    def numerical(parent):
        """
        Metoda tworzy i zwraca obiekt typu 'Keyboard' z numerami
        :param: parent — rodzic utworzonej klawiatury
        """
        keyboard_dim = (4, 3)
        horizontal_size = keyboard_dim[1]
        list_of_numbers = [x for x in range(9, -1, -1)]
        keyboard_layout = [
            sorted(list_of_numbers[i : i + horizontal_size])
            for i in range(0, len(list_of_numbers) + 1, horizontal_size)
        ]
        return Keyboard(
            parent=parent, keyboard_layout=keyboard_layout, keyboard_dim=keyboard_dim
        )

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
    def on_button_clicked(self, button: PisakButton):
        """Handle button click and emit appropriate event"""
        match button.button_type:
            case ButtonType.SPACE:
                self.emit_event(AppEvent(AppEventType.SPACE_ADDED))
            case ButtonType.BACKSPACE:
                self.emit_event(AppEvent(AppEventType.BACKSPACE_PRESSED))
            case ButtonType.ENTER:
                self.emit_event(AppEvent(AppEventType.NEW_LINE_ADDED))
            case ButtonType.LEFT_ARROW:
                self.emit_event(AppEvent(AppEventType.CURSOR_MOVED_LEFT))
            case ButtonType.RIGHT_ARROW:
                self.emit_event(AppEvent(AppEventType.CURSOR_MOVED_RIGHT))
            case ButtonType.SWITCHER:
                if button.additional_data is not None:
                    self.emit_event(AppEvent(AppEventType.ITEMS_SWITCHED, button.additional_data))
            case ButtonType.CHARACTER:
                self.emit_event(AppEvent(AppEventType.TEXT_INPUT, button.text))
            case _:
                self.emit_event(AppEvent(AppEventType.TEXT_INPUT, button.text))


class ButtonClickHandler:
    """Handler that converts button click events to keyboard actions"""
    
    def __init__(self, button_manager: ButtonManager):
        self._button_manager = button_manager
    
    def handle_event(self, event: AppEvent) -> None:
        """Handle button click event from adapter"""
        if event.type == AppEventType.BUTTON_CLICKED:
            button = event.data
            if isinstance(button, PisakButton):
                self._button_manager.on_button_clicked(button)




