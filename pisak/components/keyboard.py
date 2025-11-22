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

# Dodałbym modyfikatory jak SHIFT czy ALT

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

    # TODO ja bym to przerobił, na wczytanie z jakiegoś YAMLa, bo to tak na szybko było
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

    def _implement_layout(self):
        # to do zmiany: layout (w postaci ścieżki do pliku) powinien być
        # przekazywany jako argument funkcji ?
        for row in self._keyboard_layout:
            row_widget = PisakRowWidget(parent=self)
            for letter in row:
                button = PisakButtonBuilder().set_text(str(letter)).build(row_widget)
                row_widget.add_item(button)
                self._buttons.append(button)
            row_widget.set_layout()
            self.add_item(row_widget)

        # dodanie paru przycisków specjalnych na próbę;
        # docelowo wszystko w tej funkcji powinno być automatycznie
        # zaczytane z pliku z configami
        row_widget = PisakRowWidget(parent=self)

        # spacja
        space_button = PisakButtonBuilder().set_text("⎵").build(row_widget)
        row_widget.add_item(space_button)
        self._buttons.append(space_button)

        # backspace
        backspace_button = PisakButtonBuilder().set_text("⌫").build(row_widget)
        row_widget.add_item(backspace_button)
        self._buttons.append(backspace_button)

        # enter
        enter_button = PisakButtonBuilder().set_text("⏎").build(row_widget)
        row_widget.add_item(enter_button)
        self._buttons.append(enter_button)

        # placeholder dla przycisku zmieniającego klawiaturę
        upper_button = PisakButtonBuilder().set_text("XXX").set_additional_data(KeyboardType.UPPERCASE).build(row_widget)
        row_widget.add_item(upper_button)
        self._buttons.append(upper_button)

        lower_button = PisakButtonBuilder().set_text("xxx").set_additional_data(KeyboardType.LOWERCASE).build(row_widget)
        row_widget.add_item(lower_button)
        self._buttons.append(lower_button)

        row_widget.set_layout()
        self.add_item(row_widget)

        self.set_layout()

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
                    self.emit_event(AppEvent(AppEventType.KEYBOARD_SWITCHED, button.additional_data))
            case ButtonType.CHARACTER:
                self.emit_event(AppEvent(AppEventType.TEXT_INPUT, button.text))
            case _:
                self.emit_event(AppEvent(AppEventType.TEXT_INPUT, button.text))

    def setup_event_handlers(self):
        """Setup event handlers for all buttons using UI adapters"""
        self._button_adapters = []
        for button in self._buttons:
            # Create adapter to convert Qt signal to event
            adapter = ButtonClickAdapter(button, parent=self)
            # Subscribe to button clicks
            adapter.subscribe(ButtonClickHandler(self))
            self._button_adapters.append(adapter)

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
        # Setup event handlers after layout is created
        self.setup_event_handlers()


class ButtonClickHandler:
    """Handler that converts button click events to keyboard actions"""
    
    def __init__(self, keyboard: 'Keyboard'):
        self._keyboard = keyboard
    
    def handle_event(self, event: AppEvent) -> None:
        """Handle button click event from adapter"""
        if event.type == AppEventType.BUTTON_CLICKED:
            button = event.data
            if isinstance(button, PisakButton):
                self._keyboard.on_button_clicked(button)


# To potencjalnie mogłoby być bardziej abstrakcyjne i wtedy użyć też w innych miejscach
class KeyboardSwitcherObserver:
    """Observer that handles keyboard switching events"""
    
    def __init__(self, keyboards_container: PisakStackedWidget):
        self._keyboards_container = keyboards_container

    @property
    def keyboards_container(self):
        return self._keyboards_container

    def handle_event(self, event: AppEvent) -> None:
        """Handle keyboard switch event"""
        if event.type == AppEventType.KEYBOARD_SWITCHED:
            new_keyboard = self._keyboards_container.get_item_by_key(event.data)
            if new_keyboard:
                self._keyboards_container.switch_shown_item(new_keyboard)


