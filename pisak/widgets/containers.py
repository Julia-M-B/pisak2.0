import copy
from typing import Optional, Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QGridLayout, QHBoxLayout, QVBoxLayout, QLayout


from pisak.scanning.scannable import PisakScannableWidget
from pisak.scanning.strategies import BackToParentStrategy


class PisakContainerWidget(PisakScannableWidget):
    """
    Klasa widgetow-kontenerow, czyli widget, ktory jest odpowiedzialny za przechowywanie i wyswietlanie
    innych widgetow. Implementuje PisakScannableItem interfejs, ktory pozawala mu na skanowanie swoich
    obiektow-dzieci.
    """
    def __init__(self, parent, strategy = BackToParentStrategy()):
        super().__init__(parent)
        # Changed to list to preserve order, using check for uniqueness
        self._items = []  # PisakContainerWidget przechowuje inne obiekty, niekoniecznie skanowalne
        self._scanning_strategy = strategy
        self._layout: Optional[QLayout] = None

    @property
    def items(self) -> list[Any]:
        return copy.copy(self._items)

    @property
    def layout(self) -> Optional[QLayout]:
        return self._layout

    def add_item(self, item) -> None:
        """
        Metoda pozwalajaca na dodanie obiektu `item` do listy obiektow danego PisakContainerWidget.
        Przy okazji dodawania obiektu do `self._items` wywolywana jest takze metoda `add_scannable_item`,
        ktora dodaje obiekt `item` do obiektow skanowalnych, ale tylko jesli jest on PisakScannableItem
        """
        if item not in self._items:
            self._items.append(item)
            self.add_scannable_item(item)

    def highlight_self(self) -> None:
        """
        Nadpisanie metody `highlight_self` z interfejsu PisakScannableItems.
        W przypadku widgetow-kontenerow podswietlenie siebie jest rownoznaczne z
        podswietleniem wszystkich swoich dzieci na raz.
        """
        for scannable_item in self._scannable_items:
            scannable_item.highlight_self()

    def reset_highlight_self(self) -> None:
        """
        Nadpisanie metody `reset_highlight_self` z interfejsu PisakScannableItems.
        W przypadku widgetow-kontenerow zakonczenie podswietlania siebie jest rownoznaczne z
        zakonczeniem podswietlenia wszystkich swoich dzieci na raz.
        """
        for scannable_item in self._scannable_items:
            scannable_item.reset_highlight_self()

    def set_layout(self) -> None:
        """
        Ustawienie layoutu widgetu (tego, w jaki sposob maja sie wyswietlac jego obiekty-dzieci)
        """
        for item in self._items:
            self._layout.addWidget(item)
        self.setLayout(self._layout)

    def init_ui(self) -> None:
        self.setFocusPolicy(Qt.StrongFocus)


class PisakGridWidget(PisakContainerWidget):
    """
    PisakContainerWidget, ktorego obiekty-dzieci wyswietlane sa jak w tabeli
    (ma zarowno kolumny jak i wiersze)
    """
    def __init__(self, parent, strategy = BackToParentStrategy()):
        super().__init__(parent, strategy)
        self._layout = QGridLayout()

    def set_layout(self) -> None:
        """
        Ustawienie layoutu widgetu w gridzie - pozycjonuje elementy wierszami
        Display widgets (PisakDisplay) are always placed first (row 0), then other items
        """
        from pisak.widgets.text_display import PisakDisplay
        
        # Separate display from other items to ensure display is always on top
        display_items = []
        other_items = []
        for item in self._items:
            if isinstance(item, PisakDisplay):
                display_items.append(item)
            else:
                other_items.append(item)
        
        # Configure grid for 2/3 width display (centered)
        # Columns: 0=Spacer(1), 1=Display(4), 2=Spacer(1) -> Total 6, Display=4/6=2/3
        self._layout.setColumnStretch(0, 1)
        self._layout.setColumnStretch(1, 4)
        self._layout.setColumnStretch(2, 1)

        # Add display first (row 0)
        row = 0
        for item in display_items:
            # Display in center column
            self._layout.addWidget(item, row, 1)
            # Set row stretch to 1 to ensure it takes substantial height (e.g. 1/2 if there's one other item)
            self._layout.setRowStretch(row, 1)
            row += 1
            
        # Add other items (keyboards) spanning all columns
        for item in other_items:
            # Span all 3 columns
            self._layout.addWidget(item, row, 0, 1, 3)
            # Set row stretch to 1 to share height equally with display
            self._layout.setRowStretch(row, 1)
            row += 1
            
        self.setLayout(self._layout)


class PisakColumnWidget(PisakContainerWidget):
    """
    PisakContainerWidget, ktorego obiekty-dzieci wyswietlane sa w jednej kolumnie
    """
    def __init__(self, parent, strategy = BackToParentStrategy()):
        super().__init__(parent, strategy)
        self._layout = QVBoxLayout()


class PisakRowWidget(PisakContainerWidget):
    """
    PisakContainerWidget, ktorego obiekty-dzieci wyswietlane sa w jednym wierszu
    """
    def __init__(self, parent, strategy = BackToParentStrategy()):
        super().__init__(parent, strategy)
        self._layout = QHBoxLayout()

