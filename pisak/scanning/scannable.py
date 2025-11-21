import copy
import uuid
from typing import Self

from PySide6.QtGui import QFocusEvent
from PySide6.QtWidgets import QWidget


class PisakScannableItem:

    def __init__(self, *args, **kwargs):
        self._id: str = self._get_id()
        self._scannable_items = []
        self._scanning_strategy = None  # todo: dodac typ strategii
        self._iter_counter: int = 0  # liczy, ile razy zostala wykonana iteracja na skanowalnych obiektach-dzieciach

    def __str__(self) -> str:
        return f"{self.__class__.__name__} id={self._id}"

    def __repr__(self) -> str:
        return self.__str__()

    def __iter__(self) -> Self:
        """
        Iterate through scannable items
        """
        self._iter_scannable_items = iter(self._scannable_items)
        return self

    def __next__(self):
        try:
            item = next(self._iter_scannable_items)
            print("Next item", item)
            self._iter_counter += 1
            return item
        except StopIteration:
            print("Recurrent next call")
            return next(iter(self))

    @property
    def scannable_items(self):
        return copy.copy(self._scannable_items)

    @property
    def scanning_strategy(self):
        return self._scanning_strategy

    @property
    def iter_counter(self):
        return self._iter_counter

    @iter_counter.setter
    def iter_counter(self, val):
        self._iter_counter = val

    @staticmethod
    def _get_id():
        """
        Zwraca losowe id
        """
        return str(uuid.uuid1())[:8]

    def add_scannable_item(self, item):
        """
        Metoda nie zaimplementowana - musi zostac zaimplementowana w klasie, ktora dziedziczy po PisakScannableItem.
        Weryfikuje, czy `item` jest obiektem klasy PisakScannableItem i, jesli tak, dodaje go do `self._scannable_items`
        """
        raise NotImplementedError("Method `add_scannable_item` is not implemented.")

    def highlight_self(self):
        """
        Podswietl siebie (podswietlenie oznacza, ze na danym obiekcie jest focus
        i przyjmuje on sygnal z inputu.
        """
        raise NotImplementedError("Method `highlight_self` is not implemented.")

    def reset_highlight_self(self):
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
        if isinstance(item, PisakScannableItem):
            self._scannable_items.append(item)

    def focusInEvent(self, event: QFocusEvent) -> None:
        if event.gotFocus():
            self.highlight_self()
        else:
            super().focusInEvent(event)

    def focusOutEvent(self, event: QFocusEvent) -> None:
        if event.lostFocus():
            self.reset_highlight_self()
        else:
            super().focusOutEvent(event)

