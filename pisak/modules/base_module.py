import copy
from typing import Any

from PySide6.QtWidgets import QMainWindow, QSizePolicy
from PySide6.QtCore import Qt as QtCore

from pisak.widgets.containers import PisakGridWidget

class PisakBaseModule(QMainWindow):
    """
    Podstawowe okno w aplikacji Pisak.
    Wszystkie moduly apliakacji (speller, symboler, etc) dziedzicza po tym oknie.

    Jego centralnym widgetem jest PisakGridWidget - domyslnie obiekty widoczne w glownym oknie
    danego modulu sa rozmiesczone na zasadzie grida.
    """
    def __init__(self, parent=None, title=""):
        super().__init__(parent)
        self._title: str = title
        self._items: set[Any] = set()
        self.setCentralWidget(PisakGridWidget(parent=self))

    def __str__(self) -> str:
        return f"{self.__class__.__name__} name={self._title}"

    def __repr__(self) -> str:
        return self.__str__()

    @property
    def items(self) -> set[Any]:
        return copy.copy(self._items)

    def add_item(self, item) -> None:
        """
        dodaje obiekt `item` do zbioru obiektow-dzieci
        """
        self._items.add(item)

    def init_ui(self) -> None:
        """
        Ustawia podstawowe UI (z zalozenia takie samo dla wszystkich modulow) glownego okna
        """
        self.setWindowTitle(self._title)
        self.setGeometry(0, 0, 600, 600)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.centralWidget().setGeometry(0, 0, self.height(), self.width())
        self.centralWidget().setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.centralWidget().show()
        # Style ładować z configu styli
        self.setStyleSheet("""
                            background-color: #d9cfc5;
                            """)

    def show(self) -> None:
        """
        Pokazuje glowne okno.
        Ustawia focus na siebie (niezaleznie od tego, jaki obiekt wczesniej mial focus)
        """
        super().show()
        self.setFocus()
        # Ensure the window can receive keyboard events
        self.setFocusPolicy(QtCore.StrongFocus)

    def closeEvent(self, event) -> None:
        self.parent().closeEvent(event)