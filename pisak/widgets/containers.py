import copy
from typing import Optional

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
        self._items = []  # PisakContainerWidget przechowuje inne obiekty, niekoniecznie skanowalne (stad potrzeba na dwie listy obiektow-dzieci)
        self._scanning_strategy = strategy
        self._layout: Optional[QLayout] = None

    @property
    def items(self):
        return copy.copy(self._items)

    @property
    def layout(self):
        return self._layout

    def add_item(self, item) -> None:
        """
        Metoda pozwalajaca na dodanie obiektu `item` do listy obiektow danego PisakContainerWidget.
        Przy okazji dodawania obiektu do `self._items` wywolywana jest takze metoda `add_scannable_item`,
        ktora dodaje obiekt `item` do obiektow skanowalnych, ale tylko jesli jest on PisakScannableItem
        """
        self._items.append(item)
        self.add_scannable_item(item)

    def highlight_self(self):
        """
        Nadpisanie metody `highlight_self` z interfejsu PisakScannableItems.
        W przypadku widgetow-kontenerow podswietlenie siebie jest rownoznaczne z
        podswietleniem wszystkich swoich dzieci na raz.
        """
        for scannable_item in self._scannable_items:
            scannable_item.highlight_self()

    def reset_highlight_self(self):
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

    def init_ui(self):
        self.setFocusPolicy(Qt.StrongFocus)


class PisakGridWidget(PisakContainerWidget):
    """
    PisakContainerWidget, ktorego obiekty-dzieci wyswietlane sa jak w tabeli
    (ma zarowno kolumny jak i wiersze)
    """
    def __init__(self, parent, strategy = BackToParentStrategy()):
        super().__init__(parent, strategy)
        self._layout = QGridLayout()


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

