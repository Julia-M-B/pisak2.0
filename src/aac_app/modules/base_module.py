import copy
from typing import Any

from PySide6.QtCore import Qt as QtCore
from PySide6.QtWidgets import QMainWindow, QSizePolicy

from aac_app.scanning.manager import ScanningManager
from aac_app.widgets.containers import PisakContainerWidget


class PisakBaseModule(QMainWindow):
    """
    Base window of the application.
    All application modules (speller, etc.) inherit from this window.

    Its central widget is a PisakContainerWidget.
    """

    def __init__(self, parent=None, title=""):
        super().__init__(parent)
        self._title: str = title
        self._items: set[Any] = set()
        self._scanning_manager = ScanningManager()

    def __str__(self) -> str:
        return f"{self.__class__.__name__} name={self._title}"

    def __repr__(self) -> str:
        return self.__str__()

    @property
    def items(self) -> set[Any]:
        return copy.copy(self._items)

    def add_item(self, item) -> None:
        """
        Add the `item` object to the set of child objects.
        """
        self._items.add(item)

    def set_central_widget(self, widget: PisakContainerWidget):
        widget.setParent(self)
        self.setCentralWidget(widget)

    def init_ui(self) -> None:
        """
        Set up the basic UI of the main window (assumed to be the same for all modules).
        """
        self.setWindowTitle(self._title)
        self.setGeometry(0, 0, 600, 600)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.centralWidget().setGeometry(0, 0, self.height(), self.width())
        self.centralWidget().setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.centralWidget().show()
        # TODO: load styles from a style config
        self.setStyleSheet("""
                            background-color: #d9cfc5;
                            """)

    def show(self) -> None:
        """
        Show the main window.
        Sets focus on itself (regardless of which object previously had focus).
        """
        super().show()
        self.setFocus()
        # Ensure the window can receive keyboard events
        self.setFocusPolicy(QtCore.StrongFocus)

    def closeEvent(self, event) -> None:
        if self.parent():
            self.parent().closeEvent(event)
        else:
            super().closeEvent(event)
