"""
Action buttons column component for the PisakSpeller module.
Provides buttons for various text manipulation and control actions.
"""

from datetime import datetime
from pathlib import Path

from pisak.events import AppEvent, AppEventType
from pisak.widgets.containers import PisakColumnWidget
from pisak.widgets.buttons import PisakButton, ButtonType
from pisak.widgets.text_display import PisakDisplay
from pisak.scanning.strategies import BackToParentStrategy
from yapper import Yapper, PiperSpeaker, PiperVoicePoland


class ActionButtonsColumnComponent(PisakColumnWidget):
    """
    A column of action buttons for text manipulation and control.
    Contains buttons for clearing, scanning control, saving/loading text, and text-to-speech.
    """
    
    def __init__(self, parent):
        super().__init__(parent, strategy=BackToParentStrategy())
        # Create buttons
        self._create_buttons()
        
        # Set up layout
        self.set_layout()
        
        # Add some spacing between buttons
        self.layout.setSpacing(10)
        # self.layout.addStretch()

    
    def _create_buttons(self):
        """Create all action buttons and connect their signals"""
        
        # Clear button
        self._clear_button = PisakButton(
            parent=self,
            text="NOWY",
            button_type=ButtonType.CLEAR
        )
        self.add_item(self._clear_button)
        
        # Keyboard button
        self._keyboard_button = PisakButton(
            parent=self,
            text="KLAWIATURA",
            button_type=ButtonType.POINTER,
            additional_data="KEYBOARDS"
        )
        self.add_item(self._keyboard_button)
        
        # Predictions button
        self._predictions_button = PisakButton(
            parent=self,
            text="PREDYKCJE",
            button_type=ButtonType.POINTER,
            additional_data="PREDICTIONS"
        )
        self.add_item(self._predictions_button)
        
        # Save text button
        self._save_button = PisakButton(
            parent=self,
            text="ZAPISZ",
            button_type=ButtonType.SAVE
        )
        self.add_item(self._save_button)
        
        # Upload text button
        self._upload_button = PisakButton(
            parent=self,
            text="WCZYTAJ",
            button_type=ButtonType.UPLOAD
        )
        self.add_item(self._upload_button)
        
        # Read text button (stops scanning for now)
        self._read_button = PisakButton(
            parent=self,
            text="CZYTAJ",
            button_type=ButtonType.READ
        )
        self.add_item(self._read_button)

        # Exit button
        self._exit_button = PisakButton(
            parent=self,
            text="WYJŚCIE",
            button_type=ButtonType.EXIT
        )
        self.add_item(self._exit_button)


class ActionButtonsHandler:
    def __init__(self, module, scanning_manager, text_display):
        self.lessac = PiperSpeaker(
            voice=PiperVoicePoland.GOSIA
        )
        self.yapper = Yapper(speaker=self.lessac)

        self._module = module
        self._scanning_manager = scanning_manager
        self._text_display = text_display
        # Get or create default save directory on desktop
        self._save_directory = self._get_save_directory()

        self._items_dict = {}

    @property
    def scanning_manager(self):
        return self._scanning_manager

    @property
    def text_display(self):
        return self._text_display

    def handle_event(self, event: AppEvent) -> None:
        if event.type == AppEventType.TEXT_SAVED:
            self._on_save_clicked()
        elif event.type == AppEventType.TEXT_UPLOADED:
            self._on_upload_clicked()
        elif event.type == AppEventType.ITEM_POINTED:
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

    @staticmethod
    def _get_save_directory() -> Path:
        """
        Get the default save directory for text files.
        Creates 'pisak_texts' folder on the desktop if it doesn't exist.

        :return: Path to the save directory
        """
        # Get user's home directory
        home = Path.home()

        # Create path to desktop folder (works on most Linux systems)
        desktop = home / "Desktop"

        # If Desktop doesn't exist, try localized names or fallback to home
        if not desktop.exists():
            # Try common localized names
            for desktop_name in ["Pulpit", "Bureau", "Escritorio", "Schreibtisch"]:
                alt_desktop = home / desktop_name
                if alt_desktop.exists():
                    desktop = alt_desktop
                    break
            else:
                # Fallback to home directory
                desktop = home

        # Create pisak_texts directory
        save_dir = desktop / "pisak_texts"
        save_dir.mkdir(exist_ok=True)

        return save_dir

    def _on_save_clicked(self):
        """
        Handle save button click - saves text history to a file.
        Creates a new file with timestamp in the filename.
        """
        if not self._text_display:
            return

        # Get current text and history
        current_text = self._text_display.text
        history = self._text_display.history.copy()

        # If current text is not empty, add it to history for saving
        if current_text:
            history.append(current_text)

        # If there's nothing to save, return
        if not history:
            print("No text to save")
            return

        # Create filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"pisak_tekst_{timestamp}.txt"
        filepath = self._save_directory / filename

        try:
            # Write history to file, with empty lines between entries
            with open(filepath, 'w', encoding='utf-8') as f:
                for i, text_entry in enumerate(history):
                    f.write(text_entry)
                    # Add empty line between entries (but not after the last one)
                    if i < len(history) - 1:
                        f.write("\n\n")

            print(f"Text saved to: {filepath}")
        except Exception as e:
            print(f"Error saving text: {e}")

    def _on_pointer_clicked(self, pointed_item):
        scannable_items = getattr(pointed_item, 'scannable_items', [])
        if scannable_items:
            self._scanning_manager.stop_scanning()
            self._scanning_manager.start_scanning(pointed_item)


    def _on_upload_clicked(self):
        """
        Handle upload button click - loads the last saved text file.
        Finds the most recent pisak_tekst_*.txt file and loads it into the display.
        """
        if not self._text_display:
            return

        try:
            # Find all pisak_tekst_*.txt files in the save directory
            text_files = sorted(
                self._save_directory.glob("pisak_tekst_*.txt"),
                key=lambda p: p.stat().st_mtime,
                reverse=True
            )

            if not text_files:
                print("No saved text files found")
                return

            # Get the most recent file
            latest_file = text_files[0]

            # Read the file
            with open(latest_file, 'r', encoding='utf-8') as f:
                content = f.read()

            # Clear current text and set the loaded content
            self._text_display._text = content
            self._text_display._cursor_index = len(content)
            self._text_display.update_display()
            self._text_display.emit_text_changed()

            print(f"Text loaded from: {latest_file}")
        except Exception as e:
            print(f"Error loading text: {e}")

    def _on_read_clicked(self):
        """
        Handle read button click - stops the scanning completely and resets to initial state.
        In the future, this will trigger text-to-speech functionality.
        """
        # Stop scanning completely - this ensures scanning stops even if called from mouse click
        # (not just from scanning activation)
        if self._scanning_manager.is_scanning:
            self._scanning_manager.stop_scanning()

        if self._text_display.text:
            self.yapper.yap(self._text_display.text)


    def _on_exit_clicked(self):
        self._module.close()

    def add_item_reference(self, item, key):
        if key not in self._items_dict.keys():
            self._items_dict[key] = item

    def get_item_by_key(self, key):
        return self._items_dict.get(key, None)



