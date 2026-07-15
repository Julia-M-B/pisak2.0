import uuid
from typing import Any, Optional

try:
    from typing import Self
except ImportError:
    from typing_extensions import Self

from PySide6.QtGui import QFocusEvent
from PySide6.QtWidgets import QWidget

from aac_app.logging_config import get_module_logger
from aac_app.scanning.strategies import BaseStrategy

logger = get_module_logger(file_name="scanning", logger_name=__name__)


class PisakScannableItem:

    def __init__(self, *args, **kwargs):
        self._id: str = self._get_id()
        self._current_scannable_items: list[Any] = []
        self._scanning_strategy: Optional[BaseStrategy] = None
        self._iter_counter: int = (
            0  # counts how many times iteration over the scannable child items has been performed
        )

    def __str__(self) -> str:
        return f"{self.__class__.__name__} id={self._id}"

    def __repr__(self) -> str:
        return self.__str__()

    def __iter__(self) -> Self:
        """
        Iterate through scannable items
        """
        self._iter_scannable_items = iter(self.scannable_items)
        return self

    def __next__(self):
        try:
            item = next(self._iter_scannable_items)
            self._iter_counter += 1
            return item
        except StopIteration:
            return next(iter(self))

    @property
    def scannable_items(self) -> list[Any]:
        return self._current_scannable_items

    @property
    def scanning_strategy(self) -> Optional[BaseStrategy]:
        return self._scanning_strategy

    @property
    def iter_counter(self) -> int:
        return self._iter_counter

    @iter_counter.setter
    def iter_counter(self, val) -> None:
        self._iter_counter = val

    @staticmethod
    def _get_id() -> str:
        """
        Return a random id.
        """
        return str(uuid.uuid1())[:8]

    def add_scannable_item(self, item) -> None:
        """
        Not implemented - must be implemented by a class that inherits from PisakScannableItem.
        Verifies whether `item` is a PisakScannableItem and, if so, adds it to `self._scannable_items`.
        """
        raise NotImplementedError("Method `add_scannable_item` is not implemented.")

    def highlight_self(self) -> None:
        """
        Highlight itself (highlighting means the item has focus
        and receives input signals).
        """
        raise NotImplementedError("Method `highlight_self` is not implemented.")

    def reset_highlight_self(self) -> None:
        """
        Stop highlighting - focus moved to another item; this item no longer
        receives input signals.
        """
        raise NotImplementedError("Method `reset_highlight_self` is not implemented.")


class PisakScannableWidget(QWidget, PisakScannableItem):
    """
    A QWidget that implements the PisakScannableItem interface.
    """

    def __init__(self, parent):
        super().__init__(parent)

    def add_scannable_item(self, item) -> None:
        """
        Override of the PisakScannableItem interface method.
        Verifies whether the `item` object is a PisakScannableItem and, if so,
        adds it to the list of scannable child items.
        """
        if (
            isinstance(item, PisakScannableItem)
            and item not in self._current_scannable_items
        ):
            self._current_scannable_items.append(item)

    def focusInEvent(self, event: QFocusEvent) -> None:
        """
        PySide6 event - means the object gained focus.
        """
        if event.gotFocus():
            self.highlight_self()
        else:
            super().focusInEvent(event)

    def focusOutEvent(self, event: QFocusEvent) -> None:
        """
        PySide6 event - means the object lost focus.
        """
        if event.lostFocus():
            self.reset_highlight_self()
        else:
            super().focusOutEvent(event)
