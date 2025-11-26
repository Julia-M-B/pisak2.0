from enum import Enum, auto
from typing import Any

from PySide6.QtGui import QFocusEvent, QFont
from PySide6.QtWidgets import QPushButton
from pisak.scanning.scannable import PisakScannableItem
from pisak.scanning.strategies import BackToParentStrategy

class ButtonType(Enum):
    CHARACTER = auto()
    WORD = auto()
    ENTER = auto()
    SPACE = auto()
    BACKSPACE = auto()
    RIGHT_ARROW = auto()
    LEFT_ARROW = auto()
    UP_ARROW = auto()
    DOWN_ARROW = auto()
    SWITCHER = auto()
    CLEAR = auto()

class PisakButton(QPushButton, PisakScannableItem):
    def __init__(self, parent, text="", icon=None, scanning_strategy=BackToParentStrategy(), button_type = None, button_ui = None, additional_data: Any = None):
        super().__init__(parent=parent, text=text)
        if icon:
            self.setIcon(icon)
        self._scanning_strategy = scanning_strategy
        self._text = text
        self._button_type = button_type
        self._additional_data = additional_data
        if button_ui:
            self._set_ui(button_ui)
        else:
            self.init_ui()

    def _set_ui(self, ui_dict):
        self.init_ui()  # placeholder for setting ui defined in config file

    def init_ui(self):
        self.setFont(QFont("Arial", 16))
        self.setStyleSheet("""
                            background-color: #ede4da;
                            color: black;
                            border-style: solid;
                            border-width: 2px;
                            border-color: black;
                            border-radius: 5px;
                            min-height: 50px;
                            font-weight: bold;
                            """)

    @property
    def text(self):
        return self._text

    @text.setter
    def text(self, text):
        self._text = text
        super().setText(text)

    @property
    def button_type(self):
        return self._button_type

    @property
    def additional_data(self):
        return self._additional_data

    def focusInEvent(self, event: QFocusEvent):
        if event.gotFocus():
            self.highlight_self()
        else:
            super().focusInEvent(event)

    def focusOutEvent(self, event: QFocusEvent):
        if event.lostFocus():
            self.reset_highlight_self()
        else:
            super().focusOutEvent(event)

    def highlight_self(self):
        self.setStyleSheet("""
                            background-color: #5ea9eb;
                            color: black;
                            border-style: solid;
                            border-width: 2px;
                            border-color: #9dccf5;
                            border-radius: 5px;
                            min-height: 50px;
                            font-weight: bold;
                            """)

    def reset_highlight_self(self):
        self.init_ui()

class PisakButtonBuilder:
    def __init__(self):
        self._text = ""
        self._icon = None
        self._scanning_strategy = BackToParentStrategy()
        self._button_type = None
        self._additional_data = None

    def set_text(self, text):
        self._text = text
        return self

    def set_icon(self, icon):
        self._icon = icon
        return self

    def set_scanning_strategy(self, strategy):
        self._scanning_strategy = strategy
        return self

    def set_button_type(self, button_type):
        self._button_type = button_type
        return self

    def set_additional_data(self, data):
        self._additional_data = data
        return self

    def set_base_data(self, button_dict):
        """
        Set button properties from a dictionary configuration.
        Expected keys: 'text', 'button_type', 'additional_data', 'icon'
        """
        if 'text' in button_dict:
            self.set_text(button_dict['text'])
        if 'button_type' in button_dict:
            # Convert string to ButtonType enum if needed
            button_type_str = button_dict['button_type']
            if isinstance(button_type_str, str):
                button_type_str = button_type_str.upper()
                if hasattr(ButtonType, button_type_str):
                    self.set_button_type(getattr(ButtonType, button_type_str))
            else:
                self.set_button_type(button_type_str)
        if 'additional_data' in button_dict:
            additional_data = button_dict['additional_data']
            # Handle KeyboardType enum conversion from string
            if isinstance(additional_data, str):
                from pisak.components.keyboard import KeyboardType
                if hasattr(KeyboardType, additional_data):
                    additional_data = getattr(KeyboardType, additional_data)
            self.set_additional_data(additional_data)
        if 'icon' in button_dict:
            self.set_icon(button_dict['icon'])
        return self

    def build(self, parent):
        return PisakButton(
            parent=parent,
            text=self._text,
            icon=self._icon,
            scanning_strategy=self._scanning_strategy,
            button_type=self._button_type,
            additional_data=self._additional_data
        )



