import math

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QFontMetrics, QResizeEvent
from PySide6.QtWidgets import QLabel, QSizePolicy

from pisak.adapters import TimerAdapter
from pisak.events import AppEvent, AppEventType
import html


class PisakDisplay(QLabel):
    """
    Wyświetlacz do tekstu. Zarządza wyświetlaniem tekstu i modyfikowaniem go.
    Ma swój kursor, który wskazuje, w którym miejscu modyfikujemy tekst.
    Ignoruje input z fizycznej klawiatury - przyjmuje tylko eventy z wirtualnej klawiatury.
    """

    def __init__(self, parent):
        super().__init__(parent=parent)

        # cursor settings
        self._cursor_index: int = 0
        self._cursor_visible: bool = True
        self._cursor_timer = TimerAdapter(500)
        self._cursor_timer.start()
        self._cursor_handler = CursorToggleHandler(self)
        self._cursor_timer.subscribe(self._cursor_handler)
        self._cursor_marker = "\0"

        self._text = ""
        self._displayed_text = ""
        self._history = []

        self.init_ui()

        # metrics for displayed text (based on font set in init_ui and current size of display)
        self._font_metrics = self._get_current_font_metrics()
        self._max_lines = self._calculate_max_lines()
        self._max_line_width = self._calculate_max_line_width()

        # Initialize with empty text to ensure proper display
        self.update_display()

    def resizeEvent(self, event: QResizeEvent):
        """Handle resize to recalculate layout parameters"""
        super().resizeEvent(event)
        self.update_font_metrics()
        self.update_display()

    @property
    def cursor_index(self):
        return self._cursor_index

    @property
    def text(self):
        return self._text

    @property
    def displayed_text(self):
        return self._displayed_text

    def _get_current_font_metrics(self):
        return QFontMetrics(self.font())

    def _calculate_max_lines(self) -> int:
        # Calculate max lines based on height
        # Subtract padding (approx 30px total vertical to be safe against overflow loop)
        available_height = self.height() - 30
        line_height = self._font_metrics.lineSpacing()
        if line_height <= 0:
            line_height = 20  # fallback

        return max(2, available_height // line_height - 1)  # odejmujemy jedna linie na "numer strony"

    def _calculate_max_line_width(self) -> int:
        # Calculate max width
        # Subtract padding (approx 20px horizontal)
        line_width = self.width() - 20
        if line_width <= 0:
            line_width = 100  # fallback
        return line_width

    def update_font_metrics(self):
        self._font_metrics = self._get_current_font_metrics()
        self._max_lines = self._calculate_max_lines()
        self._max_line_width = self._calculate_max_line_width()

    def init_ui(self):
        self.setFont(QFont("Arial", 30))
        self.setAlignment(Qt.AlignLeft | Qt.AlignTop)  # Align text to top-left for better multiline support
        self.setLineWidth(10)
        # We handle wrapping manually now to support custom pagination
        self.setWordWrap(False)
        # Use Ignored policy to prevent the widget from forcing window expansion based on content
        # The size will be strictly determined by the layout (grid stretches)
        self.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        self.setStyleSheet("""
                            background-color: #f0f0f0;
                            color: black;
                            border-style: solid;
                            border-width: 2px;
                            border-color: black;
                            border-radius: 5px;
                            padding: 5px;
                            margin-bottom: 10px;
                            """)

    def toggle_cursor(self):
        """Toggle cursor visibility for blinking effect"""
        self._cursor_visible = not self._cursor_visible
        self.update_display()

    def move_cursor_left(self):
        if self._cursor_index > 0:
            self._cursor_index -= 1
        self.update_display()

    def move_cursor_right(self):
        if self._cursor_index < len(self._text):
            self._cursor_index += 1
        self.update_display()

    def update_text(self, text):
        """Insert arbitrary text at the cursor position."""
        current_text = self._text
        left_text = current_text[:self._cursor_index]
        right_text = current_text[self._cursor_index:]
        self._text = left_text + text + right_text
        self._cursor_index += len(text)
        self.update_display()

    def insert_newline(self):
        """Insert a newline at the cursor position."""
        self.update_text("\n")

    def add_space(self):
        self.update_text(" ")

    def remove_character(self):
        current_text = self._text
        if self._cursor_index > 0:
            left_text = current_text[:self._cursor_index - 1]
            right_text = current_text[self._cursor_index:]
            self._text = left_text + right_text
            self._cursor_index -= 1
        self.update_display()

    def _wrap_text(self, text, max_width):
        """
        Wrap text manually based on max_width and word boundaries.
        Returns a list of lines and the visual cursor line index.

        Celem jest niedopuszczenie do tego, zeby slowa byly rozdzielane w sytuacji,
        gdy nie mieszcza sie w linii (wtedy cale ostatnie slowo zostaje przeniesione do kolejnej linii)
        """
        if not text:
            return [""], 0

        # Insert a unique marker for cursor to track its position through wrapping
        # Using a character that is unlikely to be in text (e.g., \0)
        text_with_cursor = text[:self._cursor_index] + self._cursor_marker + text[self._cursor_index:]

        lines = []
        # Split by explicit newlines first
        paragraphs = text_with_cursor.split("\n")

        for p_idx, paragraph in enumerate(paragraphs):
            if not paragraph:
                lines.append("")
                continue

            words = paragraph.split(" ")
            current_line = []
            current_width = 0

            space_width = self._font_metrics.horizontalAdvance(" ")
            for word in words:
                # Reconstruct word with trailing space if it wasn't the last word
                # Note: simple split(' ') loses delimiters. We'll assume single space.
                # This is a limitation but fits "word is bounded by whitespaces".

                # Check width of word
                word_width = self._font_metrics.horizontalAdvance(word)

                if current_width + (space_width if current_line else 0) + word_width <= max_width:
                    if current_line:
                        current_line.append(" ")
                        current_width += space_width
                    current_line.append(word)
                    current_width += word_width
                else:
                    # Line break needed
                    if current_line:
                        lines.append("".join(current_line))

                    # Start new line
                    current_line = [word]
                    current_width = word_width

            if current_line:
                lines.append("".join(current_line))

        # Clean up cursor marker and find cursor position
        final_lines = []
        visual_cursor_line = 0

        # Handle case where text ends with newline which adds an empty line
        # split('\n') does this correctly for 'abc\n' -> ['abc', '']

        for idx, line in enumerate(lines):
            if self._cursor_marker in line:
                visual_cursor_line = idx
                # We don't remove the marker yet, we need it for rendering
            final_lines.append(line)

        return final_lines, visual_cursor_line

    def update_display(self):
        """
        Calculate layout, wrap text, handle pagination, and render HTML.
        """
        # Wrap text and find cursor
        lines, cursor_line_idx = self._wrap_text(self._text, self._max_line_width)

        n_lines = len(lines)
        n_windows = math.ceil(n_lines / self._max_lines)

        windows = []
        space_width = self._font_metrics.horizontalAdvance(" ")
        for i in range(1, n_windows + 1):
            displayed_lines = lines[(i - 1) * self._max_lines : min(i * self._max_lines, n_lines)]
            page_n = f"{i}/{n_windows}"
            page_n_width = self._font_metrics.horizontalAdvance(page_n)
            n_spaces = self._max_line_width - page_n_width // (2 * space_width)
            displayed_lines.append(" " * n_spaces + f"{i}/{n_windows}" + " " * n_spaces)
            windows.append(displayed_lines)

        cursor_window = math.ceil(cursor_line_idx / n_windows)
        visible_lines = windows[cursor_window]

        # Construct HTML
        html_lines = []

        for line in visible_lines[:-1]:
            # Replace marker with cursor
            line_content = html.escape(line)

            cursor_char = "|" if self._cursor_visible else ""

            if "\0" in line:
                line_content = line_content.replace("\0", cursor_char)
            elif "\0" in line_content:
                line_content = line_content.replace("\0", cursor_char)

            # Preserve spaces
            line_content = line_content.replace("  ", "&nbsp; ")
            html_lines.append(line_content)

        page_n_line = visible_lines[-1]
        html_lines.append(f"<div style='color: gray'>{page_n_line}</div>")

        full_html = "<br>".join(html_lines)
        self._displayed_text = full_html
        self.setText(full_html)


class TextEditionHandler:
    """Observer that handles text display events from virtual keyboard"""

    def __init__(self, text_display: PisakDisplay):
        self._text_display = text_display

    @property
    def text_display(self):
        return self._text_display

    def handle_event(self, event: AppEvent) -> None:
        """Handle events for text display - only processes virtual keyboard events"""
        if event.type == AppEventType.CHAR_ADDED:
            self._text_display.update_text(event.data)
        elif event.type == AppEventType.BACKSPACE_PRESSED:
            self._text_display.remove_character()
        elif event.type == AppEventType.SPACE_ADDED:
            self._text_display.add_space()
        elif event.type == AppEventType.NEW_LINE_ADDED:
            self._text_display.insert_newline()
        elif event.type == AppEventType.CURSOR_MOVED_RIGHT:
            self._text_display.move_cursor_right()
        elif event.type == AppEventType.CURSOR_MOVED_LEFT:
            self._text_display.move_cursor_left()
        elif event.type == AppEventType.WORD_ADDED:
            self._text_display.update_text(event.data)
            self._text_display.add_space()


class CursorToggleHandler:
    """
     Handler of cursor toggling
     """

    def __init__(self, text_display: PisakDisplay):
        self._text_display = text_display

    @property
    def text_display(self):
        return self._text_display

    def handle_event(self, event: AppEvent) -> None:
        """Handle timer timeout event to toggle cursor"""
        if event.type == AppEventType.TIMER_TIMEOUT:
            self._text_display.toggle_cursor()
