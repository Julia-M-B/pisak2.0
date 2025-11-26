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
        self._words = words or []
        # self._column = PisakColumnWidget(parent=self._parent)
        self._buttons = []
        
        self._create_word_buttons()
    
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

