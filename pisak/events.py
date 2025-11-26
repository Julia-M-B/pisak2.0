from enum import Enum, auto
from typing import Any

class AppEventType(Enum):
    BUTTON_CLICKED = auto()  # event klikniecia na przycisk
    KEY_PRESSED = auto()  # event wcisniecia przycisku na fizycznej klawiaturze
    WIDGET_FOCUSED = auto()  # event posiadania focusu przez widget
    WIDGET_UNFOCUSED = auto()  # event nieposiadania focusu przez widget
    TIMER_TIMEOUT = auto()  # event zwiazany z przerzucaniem focusu w skanowaniu w petli
    SCANNING_STARTED = auto()  # event rozpoczecia skanowania nowego obiektu
    SCANNING_STOPPED = auto()  # skanowanie danego obiektu zostalo zakonczone
    ITEM_ACTIVATED = auto()  # event oznaczajacy, ze dany obiekt zostal aktywowany (pojawil sie input z zewnatrz, gdy obiekt mial focus)
    SCANNING_RESET = auto()  # event resetu skanowania
    # Text input events (from virtual keyboard)
    CHAR_ADDED = auto()  # event wprowadzenia tekstu z wirtualnej klawiatury
    WORD_ADDED = auto()  # event wprowadzenia tekstu z wirtualnej klawiatury
    SPACE_ADDED = auto()  # event dodania spacji
    BACKSPACE_PRESSED = auto()  # event wcisniecia backspace
    CLEAR_PRESSED = auto()  # event wyczyszczenia wyswietlacza
    NEW_LINE_ADDED = auto()  # event dodania nowej linii
    CURSOR_MOVED_LEFT = auto()  # event przesuniecia kursora w lewo
    CURSOR_MOVED_RIGHT = auto()  # event przesuniecia kursora w prawo
    CURSOR_MOVED_UP = auto()
    CURSOR_MOVED_DOWN = auto()
    TEXT_CHANGED = auto()  # event zmiany tekstu w wyswietlaczu (text + cursor position)
    # Keyboard switching events
    ITEMS_SWITCHED = auto()  # event zmiany wyswietlanych elementow (np. w stacked widget)
    # Prediction events
    PREDICTIONS_READY = auto()  # event gotowych predykcji slow


class BaseEvent:
    """Base class for all events - framework agnostic"""

    def __init__(self, event_type: Enum, data: Any = None):
        """
        :param event_type: typ eventu informuje o tym, co dokładnie się wydarzyło.
                           W zależności od tego, o jakim rodzaju
                           eventu mówimy, będziemy mieli do czynienia z różnymi
                           typami eventów. Np. ScanningEvent może mieć typ
                           SCANNING_STARTED oznaczający, że skanowanie się rozpoczęło,
                           ale także dysponuje typem SCANNING_STOPPED mówiącym,
                           że skanowanie zostało zakończone.

        :param data: dodatkowe informacje niezbędne do tego, aby obserwator mógł
                     poprawnie poradzić sobie z eventem. To może być cokolwiek,
                     np. element, który z jakiegoś powodu jest kluczowy
                     dla danego eventu.
        """
        self._type = event_type
        self._data = data

    @property
    def type(self) -> Enum:
        return self._type

    @property
    def data(self) -> Any:
        return self._data

    def __repr__(self):
        return f"{self.__class__.__name__}(type={self._type}, data={self._data})"

class AppEvent(BaseEvent):
    def __init__(self, event_type: AppEventType, data: Any = None):
        super().__init__(event_type=event_type, data=data)