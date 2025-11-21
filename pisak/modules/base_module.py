import copy

from PySide6.QtWidgets import QMainWindow, QSizePolicy
from PySide6.QtCore import Qt as QtCore

from pisak.widgets.containers import PisakGridWidget
from pisak.scanning.scannable import PisakScannableItem

class PisakBaseModule(QMainWindow, PisakScannableItem):
    def __init__(self, parent=None, title=""):
        super().__init__(parent)
        self._title = title
        self._items = []
        self._central_widget = PisakGridWidget(parent=self)
        self.setCentralWidget(self._central_widget)
        self.disable_scanning()


    def __str__(self):
        return f"{self.__class__.__name__} name={self._title}"

    def __repr__(self):
        return self.__str__()

    @property
    def items(self):
        return copy.copy(self._items)

    def add_item(self, item):
        if item not in self._items:
            self._items.append(item)

    def init_ui(self):
        self.setWindowTitle(self._title)
        self.setGeometry(0, 0, 600, 600)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._central_widget.setGeometry(0, 0, self.height(), self.width())
        self._central_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._central_widget.show()
        # Style ładować z configu styli
        self.setStyleSheet("""
                            background-color: #d9cfc5;
                            """)

    def show(self):
        super().show()
        self.setFocus()
        # Ensure the window can receive keyboard events
        self.setFocusPolicy(QtCore.StrongFocus)

    def closeEvent(self, event):
        self.parent().closeEvent(event)