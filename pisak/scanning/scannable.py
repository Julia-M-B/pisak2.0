import uuid
from typing import Any, Optional
try:
    from typing import Self
except ImportError:
    from  typing_extensions import Self

from PySide6.QtGui import QFocusEvent
from PySide6.QtWidgets import QWidget

from pisak.scanning.strategies import BaseStrategy


class PisakScannableItem:

    def __init__(self, *args, **kwargs):
        self._id: str = self._get_id()
        self._current_scannable_items: list[Any] = []
        self._scanning_strategy: Optional[BaseStrategy] = None
        self._iter_counter: int = 0  # liczy, ile razy zostala wykonana iteracja na skanowalnych obiektach-dzieciach

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
        Zwraca losowe id
        """
        return str(uuid.uuid1())[:8]

    def add_scannable_item(self, item) -> None:
        """
        Metoda nie zaimplementowana - musi zostac zaimplementowana w klasie, ktora dziedziczy po PisakScannableItem.
        Weryfikuje, czy `item` jest obiektem klasy PisakScannableItem i, jesli tak, dodaje go do `self._scannable_items`
        """
        raise NotImplementedError("Method `add_scannable_item` is not implemented.")

    def highlight_self(self) -> None:
        """
        Podswietl siebie (podswietlenie oznacza, ze na danym obiekcie jest focus
        i przyjmuje on sygnal z inputu.
        """
        raise NotImplementedError("Method `highlight_self` is not implemented.")

    def reset_highlight_self(self) -> None:
        """
        Przestan sie podswietlac - focus przeszedl na inny obiekt; ten obiekt nie przujmuje
        juz sygnalu z inputu.
        """
        raise NotImplementedError("Method `reset_highlight_self` is not implemented.")


class PisakScannableWidget(QWidget, PisakScannableItem):
    """
    QWidget, ktory implementuje interfejs PisakScannableItem
    """

    def __init__(self, parent):
        super().__init__(parent)

    def add_scannable_item(self, item) -> None:
        """
        Nadpisanie metody interfejsu PisakScannableItem.
        Weryfikujemy, czy obiekt `item` jest PisakScannableItem i, jesli tak, to
        dodajemy go do listy skanowalnych obiektow-dzieci
        """
        if isinstance(item, PisakScannableItem) and item not in self._current_scannable_items:
                self._current_scannable_items.append(item)

    def focusInEvent(self, event: QFocusEvent) -> None:
        """
        event z PySdie6 - oznacza, ze obiekt zyskal focus
        """
        if event.gotFocus():
            self.highlight_self()
        else:
            super().focusInEvent(event)

    def focusOutEvent(self, event: QFocusEvent) -> None:
        """
        event z PySdie6 - oznacza, ze obiekt stracil focus
        """
        if event.lostFocus():
            self.reset_highlight_self()
        else:
            super().focusOutEvent(event)

