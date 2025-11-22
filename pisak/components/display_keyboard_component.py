import os
from pisak.components.keyboard import KeyboardSwitcherObserver, Keyboard, \
    KeyboardType
from pisak.widgets.containers import PisakContainerWidget
from pisak.widgets.stacked_widgets import PisakStackedWidget
from pisak.widgets.text_display import PisakDisplay, TextDisplayObserver


class KeyboardDisplayComponent:
    def __init__(self, parent: PisakContainerWidget = None, display = None, display_observer = None, keyboards = None, keyboards_observer = None):
        self._parent = parent

        self._display = display if display else PisakDisplay(parent=self._parent)
        self._display_observer = display_observer if display_observer else TextDisplayObserver(self._display)

        self._keyboards = keyboards if keyboards else PisakStackedWidget(parent=self._parent)
        self._keyboards_observer = keyboards_observer if keyboards_observer else KeyboardSwitcherObserver(self._keyboards)

        # Create keyboards from config files
        config_dir = os.path.join(os.path.dirname(__file__), "..", "config_files")
        lowercase_config = os.path.join(config_dir, "lowercase_keyboard.yml")
        uppercase_config = os.path.join(config_dir, "uppercase_keyboard.yml")

        self._lower_letters = Keyboard(parent=self._keyboards)
        self._lower_letters.implement_layout_from_config(lowercase_config)
        self.setup_keyboard(self._lower_letters)
        self._keyboards.add_item_reference(self._lower_letters, KeyboardType.LOWERCASE)

        self._upper_letters = Keyboard(parent=self._keyboards)
        self._upper_letters.implement_layout_from_config(uppercase_config)
        self.setup_keyboard(self._upper_letters)
        self._keyboards.add_item_reference(self._upper_letters, KeyboardType.UPPERCASE)

        self._keyboards.switch_shown_item(self._lower_letters)

        # Add display first (will appear on top), then keyboards (will appear below)
        self._parent.add_item(self._display)
        self._parent.add_item(self._keyboards)

    def setup_keyboard(self, keyboard: Keyboard):
        keyboard.setup_event_handlers()
        keyboard.subscribe(self._keyboards_observer)
        keyboard.subscribe(self._display_observer)
        self._keyboards.add_item(keyboard)
