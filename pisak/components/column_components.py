import os

from PySide6 import QtGui
from PySide6.QtWidgets import QLabel
from PySide6.QtCore import Qt
from pisak.widgets.containers import PisakColumnWidget
from pisak.widgets.buttons import PisakButton, ButtonType
from pisak.scanning.strategies import BackToParentStrategy


class WordColumnComponent(PisakColumnWidget):
    """
    Component that creates a column of word buttons.
    Each button contains a predefined word that can be inserted into the display.
    """
    
    def __init__(self, parent, words: list[str] = None):
        """
        Initialize word column with a list of words.
        
        :param parent: Parent widget
        :param words: List of words to display as buttons
        """
        super().__init__(parent)
        self._icons_base_path = os.path.join(os.path.dirname(__file__), "..",
                                             "config_files/icons")
        self._add_header_image()
        self._words = words or []
        # self._column = PisakColumnWidget(parent=self._parent)
        self._buttons = []
        
        self._create_word_buttons()

    def _add_header_image(self):
        """Add the header image at the top of the column (non-scannable)"""
        icon_path = os.path.join(self._icons_base_path, "predykcjanapis.svg")
        header_label = QLabel(self)
        header_label.setPixmap(QtGui.QPixmap(icon_path))
        header_label.setAlignment(Qt.AlignCenter)
        header_label.setScaledContents(True)
        header_label.setStyleSheet(
            """
            max-height: 35px;
            max-width: 153px;
            """
        )
        # Add directly to layout (not via add_item) so it's not scannable
        # We'll insert it at position 0 after set_layout is called
        self._header_label = header_label
        self.add_item(self._header_label)
    
    def _create_word_buttons(self):
        """Create a button for each word in the list"""
        for word in self._words:
            button = PisakButton(
                parent=self,
                text=word,
                button_type=ButtonType.WORD,
                scanning_strategy=BackToParentStrategy()
            )
            self.add_item(button)
            self._buttons.append(button)
        
        self.set_layout()
    
    # @property
    # def column(self):
    #     """Get the column widget containing all word buttons"""
    #     return self._column
    
    @property
    def buttons(self):
        """Get list of all word buttons"""
        return self._buttons
    
    def update_words(self, new_words: list[str]):
        """
        Update the words displayed on the buttons.
        This method is thread-safe and can be called from any thread.
        
        :param new_words: List of new words to display
        """
        # Ensure we have the right number of words
        if len(new_words) != len(self._buttons):
            # Pad with empty strings or truncate as needed
            if len(new_words) < len(self._buttons):
                new_words = new_words + [""] * (len(self._buttons) - len(new_words))
            else:
                new_words = new_words[:len(self._buttons)]
        
        # Update button texts
        for button, word in zip(self._buttons, new_words):
            button.text = word

