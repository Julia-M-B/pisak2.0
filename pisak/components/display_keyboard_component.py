import os
from typing import Any

from pisak.components.keyboard import Keyboard, KeyboardType, ButtonManager, ButtonClickHandler
from pisak.widgets.containers import PisakColumnWidget
from pisak.scanning.strategies import BackNLevelsStrategy
from pisak.widgets.stacked_widgets import PisakStackedWidget, ItemSwitchedHandler
from pisak.widgets.text_display import PisakDisplay, TextEditionHandler


class KeyboardDisplayComponent(PisakColumnWidget):
    def __init__(self, parent, scanning_manager, keyboards_config_paths: list[str] = None):
        super().__init__(parent)
        self._parent = parent
        self._scanning_manager = scanning_manager

        self._display = PisakDisplay(parent=self._parent)
        self._keyboards = PisakStackedWidget(parent=self._parent)
        self.add_item(self._display)
        self.add_item(self._keyboards)

        # todo: create a function that would create and setup a keyboard for each config in keyboards_config_path

        # Create keyboards from config files
        config_dir = os.path.join(os.path.dirname(__file__), "..", "config_files")
        uppercase_config = os.path.join(config_dir, "uppercase_keyboard.yml")
        diacritics_config = os.path.join(config_dir, "diacritics_keyboard.yml")
        numerical_config = os.path.join(config_dir, "numerical_keyboard.yml")

        self._uppercase = Keyboard(parent=self._keyboards,
                                   strategy=BackNLevelsStrategy(n=3))
        self._uppercase.implement_layout_from_config(uppercase_config)
        self._keyboards.add_item_reference(self._uppercase,
                                           KeyboardType.UPPERCASE)
        self._keyboards.add_item(self._uppercase)

        self._diacritics = Keyboard(parent=self._keyboards, strategy=BackNLevelsStrategy(n=3))
        self._diacritics.implement_layout_from_config(diacritics_config)
        self._keyboards.add_item_reference(self._diacritics, KeyboardType.DIACRITICS)
        self._keyboards.add_item(self._diacritics)

        self._numerical = Keyboard(parent=self._keyboards, strategy=BackNLevelsStrategy(n=3))
        self._numerical.implement_layout_from_config(numerical_config)
        self._keyboards.add_item_reference(self._numerical, KeyboardType.NUMERICAL)
        self._keyboards.add_item(self._numerical)

        self._keyboards.switch_shown_item(self._uppercase)

        # setting up all connections between event emitter and event handlers
        self._button_manager = ButtonManager()
        self._button_handler = ButtonClickHandler(button_manager=self._button_manager)
        self._scanning_manager.subscribe(self._button_handler)

        self._text_edition_handler = TextEditionHandler(text_display=self._display)
        self._button_manager.subscribe(self._text_edition_handler)

        self._keyboards_handler = ItemSwitchedHandler(scanning_manager=self._scanning_manager,
                                                      stacked_widget=self._keyboards)
        self._button_manager.subscribe(self._keyboards_handler)

        self.set_layout()
        # Right Column: 1 vs 1 (Display vs Keyboard)
        self.layout.setStretch(0, 1)
        self.layout.setStretch(1, 1)

    @property
    def keyboards(self):
        return self._keyboards

    @property
    def display(self):
        return self._display

    @property
    def scannable_items(self) -> list[Any]:
        return self._keyboards.scannable_items

