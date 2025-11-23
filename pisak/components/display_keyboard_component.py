import os
from pisak.components.keyboard import Keyboard, KeyboardType, ButtonManager, ButtonClickHandler
from pisak.widgets.stacked_widgets import PisakStackedWidget, ItemSwitchedHandler
from pisak.widgets.text_display import PisakDisplay, TextEditionHandler


class KeyboardDisplayComponent:
    def __init__(self, parent, scanning_manager, keyboards_config_paths: list[str] = None):
        self._parent = parent
        self._scanning_manager = scanning_manager

        self._display = PisakDisplay(parent=self._parent)
        self._keyboards = PisakStackedWidget(parent=self._parent)

        # todo: create a function that would create and setup a keyboard for each config in keyboards_config_path

        # Create keyboards from config files
        config_dir = os.path.join(os.path.dirname(__file__), "..", "config_files")
        lowercase_config = os.path.join(config_dir, "lowercase_keyboard.yml")
        uppercase_config = os.path.join(config_dir, "uppercase_keyboard.yml")

        self._lower_letters = Keyboard(parent=self._keyboards)
        self._lower_letters.implement_layout_from_config(lowercase_config)
        self._keyboards.add_item_reference(self._lower_letters, KeyboardType.LOWERCASE)
        self._keyboards.add_item(self._lower_letters)

        self._upper_letters = Keyboard(parent=self._keyboards)
        self._upper_letters.implement_layout_from_config(uppercase_config)
        self._keyboards.add_item_reference(self._upper_letters, KeyboardType.UPPERCASE)
        self._keyboards.add_item(self._upper_letters)

        self._keyboards.switch_shown_item(self._upper_letters)

        # setting up all connections between event emitter and event handlers
        self._button_manager = ButtonManager()
        self._button_handler = ButtonClickHandler(button_manager=self._button_manager)
        self._scanning_manager.subscribe(self._button_handler)

        self._text_edition_handler = TextEditionHandler(text_display=self._display)
        self._button_manager.subscribe(self._text_edition_handler)

        self._keyboards_handler = ItemSwitchedHandler(scanning_manager=self._scanning_manager,
                                                      stacked_widget=self._keyboards)
        self._button_manager.subscribe(self._keyboards_handler)

    @property
    def keyboards(self):
        return self._keyboards

    @property
    def display(self):
        return self._display
