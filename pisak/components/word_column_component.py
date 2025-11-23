from pisak.widgets.containers import PisakColumnWidget
from pisak.widgets.buttons import PisakButton, ButtonType
from pisak.scanning.strategies import BackToParentStrategy


class WordColumnComponent:
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
        self._parent = parent
        self._words = words or []
        self._column = PisakColumnWidget(parent=self._parent)
        self._buttons = []
        
        self._create_word_buttons()
    
    def _create_word_buttons(self):
        """Create a button for each word in the list"""
        for word in self._words:
            button = PisakButton(
                parent=self._column,
                text=word,
                button_type=ButtonType.TEXT,
                scanning_strategy=BackToParentStrategy()
            )
            self._column.add_item(button)
            self._buttons.append(button)
        
        self._column.set_layout()
    
    @property
    def column(self):
        """Get the column widget containing all word buttons"""
        return self._column
    
    @property
    def buttons(self):
        """Get list of all word buttons"""
        return self._buttons

