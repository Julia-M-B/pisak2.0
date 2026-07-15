from typing import Any, Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QGridLayout, QHBoxLayout, QLayout, QVBoxLayout

from aac_app.logging_config import get_module_logger
from aac_app.scanning.scannable import PisakScannableWidget
from aac_app.scanning.strategies import BackToParentStrategy

logger = get_module_logger(file_name="widgets", logger_name=__name__)


class PisakContainerWidget(PisakScannableWidget):
    """
    Container-widget class, i.e. a widget responsible for storing and displaying
    other widgets. It implements the PisakScannableItem interface, which allows it
    to scan its child items.
    """

    def __init__(self, parent, strategy=BackToParentStrategy()):
        super().__init__(parent)
        # Changed to list to preserve order, using check for uniqueness
        self._items = (
            []
        )  # PisakContainerWidget stores other objects, not necessarily scannable ones
        self._scanning_strategy = strategy
        self._layout: Optional[QLayout] = None

    @property
    def items(self) -> list[Any]:
        return self._items

    @property
    def layout(self) -> Optional[QLayout]:
        return self._layout

    def add_item(self, item) -> None:
        """
        Method that adds the `item` object to the item list of the given PisakContainerWidget.
        While adding the object to `self._items`, the `add_scannable_item` method is also called,
        which adds the `item` object to the scannable items, but only if it is a PisakScannableItem.
        """
        if item not in self._items:
            self._items.append(item)
            self.add_scannable_item(item)

    def highlight_self(self) -> None:
        """
        Override of the `highlight_self` method from the PisakScannableItem interface.
        For container widgets, highlighting itself is equivalent to
        highlighting all of its children at once.
        """
        for scannable_item in self._current_scannable_items:
            scannable_item.highlight_self()

    def reset_highlight_self(self) -> None:
        """
        Override of the `reset_highlight_self` method from the PisakScannableItem interface.
        For container widgets, stopping highlighting itself is equivalent to
        stopping the highlight of all of its children at once.
        """
        for scannable_item in self._current_scannable_items:
            scannable_item.reset_highlight_self()

    def set_layout(self) -> None:
        """
        Set the widget's layout (how its child items should be displayed).
        """
        for item in self._items:
            self._layout.addWidget(item)
        self.setLayout(self._layout)

    def init_ui(self) -> None:
        self.setFocusPolicy(Qt.StrongFocus)


class PisakGridWidget(PisakContainerWidget):
    """
    A PisakContainerWidget whose child items are displayed like in a table
    (it has both columns and rows).
    """

    def __init__(self, parent, strategy=BackToParentStrategy()):
        super().__init__(parent, strategy)
        self._layout = QGridLayout()


class PisakColumnWidget(PisakContainerWidget):
    """
    A PisakContainerWidget whose child items are displayed in a single column.
    """

    def __init__(self, parent, strategy=BackToParentStrategy()):
        super().__init__(parent, strategy)
        self._layout = QVBoxLayout()


class PisakRowWidget(PisakContainerWidget):
    """
    A PisakContainerWidget whose child items are displayed in a single row.
    """

    def __init__(self, parent, strategy=BackToParentStrategy()):
        super().__init__(parent, strategy)
        self._layout = QHBoxLayout()
