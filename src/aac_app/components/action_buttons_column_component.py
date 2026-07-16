"""
Action buttons column component for the PisakSpeller module.
Provides buttons for various text manipulation and control actions.
"""

from PySide6 import QtGui
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel
from yapper import PiperSpeaker, PiperVoicePoland, Yapper

from aac_app.events import AppEvent, AppEventType
from aac_app.logging_config import get_module_logger
from aac_app.resource_paths import package_resource_path
from aac_app.scanning.strategies import BackToParentStrategy
from aac_app.widgets.buttons import ButtonType, PisakButton
from aac_app.widgets.containers import PisakColumnWidget

logger = get_module_logger(file_name="components", logger_name=__name__)


class ActionButtonsColumnComponent(PisakColumnWidget):
    """
    A column of action buttons for text manipulation and control.
    Contains buttons for clearing, scanning control, saving/loading text, and text-to-speech.
    """

    def __init__(self, parent):
        super().__init__(parent, strategy=BackToParentStrategy())
        # Add header image (non-scannable)
        self._add_header_image()
        # Create buttons
        self._create_buttons()

        # Set up layout
        self.set_layout()

        # Add some spacing between buttons
        self.layout.setSpacing(10)

    def _add_header_image(self):
        """Add the header image at the top of the column (non-scannable)"""
        icon_path = package_resource_path("resources/icons/funkcjenapis.svg")
        header_label = QLabel(self)
        header_label.setPixmap(QtGui.QPixmap(icon_path))
        header_label.setAlignment(Qt.AlignCenter)
        header_label.setScaledContents(True)
        header_label.setStyleSheet("""
            max-height: 57px;
            max-width: 142px;
            """)
        # Add directly to layout (not via add_item) so it's not scannable
        # We'll insert it at position 0 after set_layout is called
        self._header_label = header_label
        self.add_item(self._header_label)

    def _create_buttons(self):
        """Create all action buttons and connect their signals"""

        # Clear button
        self._clear_button = PisakButton(
            parent=self,
            text="NOWY\t",
            icon=QtGui.QIcon(
                package_resource_path("resources/icons/nowy_dokument.svg")
            ),
            button_type=ButtonType.CLEAR,
        )
        self.add_item(self._clear_button)

        # Keyboard button
        self._keyboard_button = PisakButton(
            parent=self,
            text="KLAWIATURA\t",
            icon=QtGui.QIcon(package_resource_path("resources/icons/klawiatura.svg")),
            button_type=ButtonType.POINTER,
            additional_data="KEYBOARDS",
        )
        self.add_item(self._keyboard_button)

        # Predictions button
        self._predictions_button = PisakButton(
            parent=self,
            text="PREDYKCJE\t",
            icon=QtGui.QIcon(package_resource_path("resources/icons/predykcja.svg")),
            button_type=ButtonType.POINTER,
            additional_data="PREDICTIONS",
        )
        self.add_item(self._predictions_button)

        # Read text button (reads the current text aloud)
        self._read_button = PisakButton(
            parent=self,
            text="CZYTAJ\t",
            icon=QtGui.QIcon(package_resource_path("resources/icons/przeczytaj.svg")),
            button_type=ButtonType.READ,
        )
        self.add_item(self._read_button)

        # Exit button
        self._exit_button = PisakButton(
            parent=self,
            text="WYJŚCIE\t",
            icon=QtGui.QIcon(package_resource_path("resources/icons/exit.svg")),
            button_type=ButtonType.EXIT,
        )
        self.add_item(self._exit_button)


class ActionButtonsHandler:
    def __init__(self, module, scanning_manager, text_display):
        self.lessac = PiperSpeaker(voice=PiperVoicePoland.GOSIA)
        self.yapper = Yapper(speaker=self.lessac)

        self._module = module
        self._scanning_manager = scanning_manager
        self._text_display = text_display

        self._items_dict = {}

    @property
    def scanning_manager(self):
        return self._scanning_manager

    @property
    def text_display(self):
        return self._text_display

    def handle_event(self, event: AppEvent) -> None:
        if event.type == AppEventType.ITEM_POINTED:
            pointed_item = event.data
            if not pointed_item:
                return

            resolved_item = self.get_item_by_key(pointed_item)
            if resolved_item:
                pointed_item = resolved_item
            self._on_pointer_clicked(pointed_item)

        elif event.type == AppEventType.READ_TEXT:
            self._on_read_clicked()
        elif event.type == AppEventType.MODULE_EXITED:
            self._on_exit_clicked()

    def _on_pointer_clicked(self, pointed_item):
        scannable_items = getattr(pointed_item, "scannable_items", [])
        if scannable_items:
            self._scanning_manager.stop_scanning()
            self._scanning_manager.start_scanning(pointed_item)

    def _on_read_clicked(self):
        """
        Handle read button click - stops scanning completely and reads the current
        text aloud using the text-to-speech engine.
        """
        # Stop scanning completely - this ensures scanning stops even if called from mouse click
        # (not just from scanning activation)
        if self._scanning_manager.is_scanning:
            self._scanning_manager.stop_scanning()

        if self._text_display.text:
            self.yapper.yap(self._text_display.text)

    def _on_exit_clicked(self):
        self._module.close()
        logger.info("Exit button clicked.")

    def add_item_reference(self, item, key):
        if key not in self._items_dict.keys():
            self._items_dict[key] = item

    def get_item_by_key(self, key):
        return self._items_dict.get(key, None)
