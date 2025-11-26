import math

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QFontMetrics, QResizeEvent
from PySide6.QtWidgets import QLabel, QSizePolicy

from pisak.adapters import TimerAdapter
from pisak.events import AppEvent, AppEventType
from pisak.emitters import EventEmitter
import html


class PisakDisplay(QLabel, EventEmitter):
    """
    Wyświetlacz do tekstu. Zarządza wyświetlaniem tekstu i modyfikowaniem go.
    Ma swój kursor, który wskazuje, w którym miejscu modyfikujemy tekst.
    Ignoruje input z fizycznej klawiatury - przyjmuje tylko eventy z wirtualnej klawiatury.
    """

    def __init__(self, parent):
        QLabel.__init__(self, parent)
        EventEmitter.__init__(self)

        # cursor settings
        self._cursor_index: int = 0
        self._cursor_visible: bool = True
        self._cursor_timer = TimerAdapter(500)
        self._cursor_timer.start()
        self._cursor_handler = CursorToggleHandler(self)
        self._cursor_timer.subscribe(self._cursor_handler)
        self._cursor_marker = "\0"

        self._text = ""
        self._displayed_text = [""]
        self._history = []

        self.init_ui()

        # metrics for displayed text (based on font set in init_ui and current size of display)
        self._font_metrics = self._get_current_font_metrics()
        self._max_lines = self._calculate_max_lines()
        self._max_line_length = self._calculate_max_line_length()

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

    def _calculate_max_line_length(self) -> int:
        # Calculate max width accounting for padding, border, and margins
        # Stylesheet has: padding: 5px (left+right = 10px) + border: 2px (left+right = 4px) = 14px
        # Add extra margin based on average character width to ensure text doesn't get cut off
        avg_char_width = self._font_metrics.averageCharWidth()
        # Total horizontal space to subtract: CSS padding/border + extra safety margin
        horizontal_padding = 14 + int(avg_char_width * 1.5)  # Extra 1.5 chars worth of space
        
        line_width = self.width() - horizontal_padding
        if line_width <= 0:
            line_width = 100  # fallback
        return line_width

    def update_font_metrics(self):
        self._font_metrics = self._get_current_font_metrics()
        self._max_lines = self._calculate_max_lines()
        self._max_line_length = self._calculate_max_line_length()

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
    
    def _emit_text_changed(self):
        """Emit TEXT_CHANGED event with current text and cursor position"""
        event = AppEvent(
            AppEventType.TEXT_CHANGED,
            data={'text': self._text, 'cursor_position': self._cursor_index}
        )
        self.emit_event(event)

    def move_cursor_left(self):
        if self._cursor_index > 0:
            self._cursor_index -= 1
        self.update_display()
        self._emit_text_changed()

    def move_cursor_right(self):
        if self._cursor_index < len(self._text):
            self._cursor_index += 1
        self.update_display()
        self._emit_text_changed()

    def move_cursor_up(self):
        # Wrap text and find cursor
        lines, cursor_line_idx = self._wrap_text(self._text, self._max_line_length)
        if cursor_line_idx > 0 and len(lines) > 1:
            previous_line = lines[cursor_line_idx - 1]
            cursor_line = lines[cursor_line_idx]
            line_length = 0
            for c in cursor_line:
                if c == self._cursor_marker:
                    break
                line_length += 1
            if len(previous_line) <= line_length:
                self._cursor_index -= (line_length + 1)  # plus 1 for `\n` at the end of the previous line
            else:
                self._cursor_index -= len(previous_line)

    def move_cursor_down(self):
        # Wrap text and find cursor
        lines, cursor_line_idx = self._wrap_text(self._text, self._max_line_length)
        if cursor_line_idx < (len(lines) - 1) and len(lines) > 1:
            next_line = lines[cursor_line_idx + 1]
            cursor_line = lines[cursor_line_idx]
            line_length = 0
            for c in cursor_line:
                if c == self._cursor_marker:
                    break
                line_length += 1
            if len(next_line) <= line_length:
                self._cursor_index += (len(cursor_line) - line_length + len(next_line))  # if next line is shorter, move at the end of the next line
            else:
                self._cursor_index += len(cursor_line)

    def update_text(self, text):
        """Insert arbitrary text at the cursor position."""
        current_text = self._text
        left_text = current_text[:self._cursor_index]
        right_text = current_text[self._cursor_index:]
        self._text = left_text + text + right_text
        self._cursor_index += len(text)
        self.update_display()
        self._emit_text_changed()

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
        self._emit_text_changed()

    def clear_text(self):
        """Clear the text display and save current text to history"""
        # Save current text to history if it's not empty
        if self._text:
            self._history.append(self._text)
        
        # Clear text and reset cursor
        self._text = ""
        self._cursor_index = 0
        self.update_display()
        self._emit_text_changed()

    def _is_word_char(self, char: str) -> bool:
        """Check if a character is part of a word (letter or digit)"""
        return char.isalnum()
    
    def _is_cursor_inside_word(self) -> bool:
        """
        Check if cursor is inside a word.
        Cursor is inside a word if at least one adjacent character (left or right) is a letter or digit.
        """
        if not self._text:
            return False
        
        # Check character to the left of cursor
        if self._cursor_index > 0:
            left_char = self._text[self._cursor_index - 1]
            if self._is_word_char(left_char):
                return True
        
        # Check character to the right of cursor
        if self._cursor_index < len(self._text):
            right_char = self._text[self._cursor_index]
            if self._is_word_char(right_char):
                return True
        
        return False
    
    def _get_word_boundaries(self) -> tuple[int, int]:
        """
        Get the start and end indices of the word that contains the cursor.
        Returns (start_index, end_index) where:
        - start_index is the position after the last space (or 0 if no space before)
        - end_index is the position of the next space/newline (or end of text)
        
        If cursor is not inside a word, returns (cursor_index, cursor_index).
        """
        if not self._is_cursor_inside_word():
            return (self._cursor_index, self._cursor_index)
        
        text = self._text
        
        # Find start of word (search backwards for space or newline)
        start = self._cursor_index
        while start > 0:
            char = text[start - 1]
            if char in (' ', '\n'):
                break
            start -= 1
        
        # Find end of word (search forwards for space or newline)
        end = self._cursor_index
        while end < len(text):
            char = text[end]
            if char in (' ', '\n'):
                break
            end += 1
        
        return (start, end)
    
    def replace_current_word(self, new_word: str):
        """
        Replace the word at cursor position with a new word.
        If cursor is inside a word, replaces that entire word.
        If the word being replaced has a trailing space, removes it to avoid double spaces.
        
        :param new_word: The new word to insert (should already include trailing space if needed)
        """
        start, end = self._get_word_boundaries()
        
        # Check if there's a space after the word being replaced
        has_trailing_space = end < len(self._text) and self._text[end] == ' '
        
        # If there's a trailing space, include it in the replacement to avoid double spaces
        if has_trailing_space:
            end += 1
        
        # Replace the word
        left_text = self._text[:start]
        right_text = self._text[end:]
        self._text = left_text + new_word + right_text
        
        # Position cursor after the new word
        self._cursor_index = start + len(new_word)
        
        self.update_display()
        self._emit_text_changed()

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
            for word_idx, word in enumerate(words):
                # Calculate actual display width without the cursor marker
                word_without_marker = word.replace(self._cursor_marker, "")
                
                # Handle empty words (from trailing/multiple spaces)
                if not word_without_marker:
                    # If this empty word contains the cursor marker, add it to current line
                    if self._cursor_marker in word:
                        # Add space before cursor if there's already content on the line
                        if len(current_line) > 0:
                            current_line.append(" ")
                            current_width += space_width
                        current_line.append(self._cursor_marker)
                    # Skip processing empty words further
                    continue
                
                word_width = self._font_metrics.horizontalAdvance(word_without_marker)

                # Check if word fits on current line
                needs_space_before = len(current_line) > 0
                if current_width + (space_width if needs_space_before else 0) + word_width <= max_width:
                    # Word fits
                    if needs_space_before:
                        current_line.append(" ")
                        current_width += space_width
                    current_line.append(word)
                    current_width += word_width
                else:
                    # Word doesn't fit - wrap to new line
                    if current_line:
                        lines.append("".join(current_line))

                    # Start new line
                    current_line = [word]
                    current_width = word_width

            if current_line:
                lines.append("".join(current_line))

        # Find which line contains the cursor
        cursor_line_idx = 0
        for idx, line in enumerate(lines):
            if self._cursor_marker in line:
                cursor_line_idx = idx
                break

        return lines, cursor_line_idx

    def update_display(self):
        """
        Calculate layout, wrap text, handle pagination, and render HTML.
        """
        # Wrap text and find cursor
        lines, cursor_line_idx = self._wrap_text(self._text, self._max_line_length)

        n_lines = len(lines)
        n_max_lines = self._max_lines

        # Calculate number of pages
        n_windows = math.ceil(n_lines / n_max_lines)
        if n_windows == 0:
            n_windows = 1

        windows = []
        for i in range(1, n_windows + 1):
            # Slice for current page
            start_idx = (i - 1) * n_max_lines
            end_idx = min(start_idx + n_max_lines, n_lines)
            displayed_lines = list(lines[start_idx:end_idx])

            # Pad with empty lines to push page number to bottom
            while len(displayed_lines) < n_max_lines:
                displayed_lines.append("")

            # Add page number
            page_n = f"{i}/{n_windows}"
            displayed_lines.append(page_n)
            
            windows.append(displayed_lines)

        # Calculate cursor window
        cursor_window = cursor_line_idx // n_max_lines
        
        # Safety bounds
        if cursor_window >= len(windows):
            cursor_window = len(windows) - 1
        if cursor_window < 0:
            cursor_window = 0

        visible_lines = windows[cursor_window]
        self._displayed_text = visible_lines[:-1]

        # Construct HTML
        html_lines = []

        for line in self._displayed_text:
            # Replace marker with cursor BEFORE HTML escaping
            cursor_char = "|" if self._cursor_visible else ""
            
            # Replace cursor marker first, before any escaping
            if self._cursor_marker in line:
                line = line.replace(self._cursor_marker, cursor_char)
            
            # Now escape HTML
            line_content = html.escape(line)

            # Preserve spaces
            line_content = line_content.replace("  ", "&nbsp; ")
            
            # Ensure empty lines take up vertical space
            if not line_content:
                line_content = "&nbsp;"
            
            html_lines.append(line_content)

        page_n_line = visible_lines[-1]
        
        # Calculate font size for page number (50% of current font size)
        current_font_size = self.font().pointSize()
        page_n_font_size = max(1, int(current_font_size / 2))

        # Use remaining vertical space to push the page number to the bottom
        # We calculated n_max_lines with a "-1" buffer (approx 1 line height).
        # The page number takes about 0.5 line height.
        # So we have ~0.5 line height of extra space to distribute.
        
        line_height = self._font_metrics.lineSpacing()
        margin_top = int(line_height * 0.2) # A small push down, relying on the empty line buffer
        
        page_html = f"<div align='center' style='color: gray; font-size: {page_n_font_size}pt; margin: 0px; margin-top: {margin_top}px;'>{page_n_line}</div>"

        content_html = "<br>".join(html_lines)
        full_html = content_html + page_html
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
        elif event.type == AppEventType.CLEAR_PRESSED:
            self._text_display.clear_text()
        elif event.type == AppEventType.SPACE_ADDED:
            self._text_display.add_space()
        elif event.type == AppEventType.NEW_LINE_ADDED:
            self._text_display.insert_newline()
        elif event.type == AppEventType.CURSOR_MOVED_RIGHT:
            self._text_display.move_cursor_right()
        elif event.type == AppEventType.CURSOR_MOVED_LEFT:
            self._text_display.move_cursor_left()
        elif event.type == AppEventType.CURSOR_MOVED_UP:
            self._text_display.move_cursor_up()
        elif event.type == AppEventType.CURSOR_MOVED_DOWN:
            self._text_display.move_cursor_down()
        elif event.type == AppEventType.WORD_ADDED:
            # Remove any leading spaces from the word before adding it
            word = event.data.lstrip() if isinstance(event.data, str) else event.data
            # Add a space after the word for better UX
            word_with_space = word + " "
            
            # Check if cursor is inside a word - if yes, replace the whole word
            if self._text_display._is_cursor_inside_word():
                self._text_display.replace_current_word(word_with_space)
            else:
                # Just insert the word at cursor position
                self._text_display.update_text(word_with_space)


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
