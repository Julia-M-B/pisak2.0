from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont, QFontMetrics, QKeyEvent, QResizeEvent
from PySide6.QtWidgets import QLabel, QSizePolicy

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

        self._cursor_index: int = 0
        self._cursor_visible: bool = True
        self._cursor_timer = QTimer()
        self._cursor_timer.timeout.connect(self.toggle_cursor)
        self._cursor_timer.start(500)
        self._text = ""
        
        # Metrics for layout
        self._font_metrics = QFontMetrics(self.font())
        self._max_lines = 1

        self.init_ui()
        # Initialize with empty text to ensure proper display
        self.update_display()

    def keyPressEvent(self, event: QKeyEvent):
        """
        Override keyPressEvent to ignore real keyboard input.
        This widget only accepts input from virtual keyboard via events.
        """
        # Ignore all real keyboard input - only accept virtual keyboard events
        event.ignore()

    def resizeEvent(self, event: QResizeEvent):
        """Handle resize to recalculate layout parameters"""
        super().resizeEvent(event)
        self.update_display()

    @property
    def cursor_index(self):
        return self._cursor_index

    @property
    def text(self):
        return self._text

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
        self._font_metrics = QFontMetrics(self.font())

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
        """
        if not text:
            return [""], 0

        # Insert a unique marker for cursor to track its position through wrapping
        # Using a character that is unlikely to be in text (e.g., \0)
        CURSOR_MARKER = "\0"
        text_with_cursor = text[:self._cursor_index] + CURSOR_MARKER + text[self._cursor_index:]

        lines = []
        # Split by explicit newlines first
        paragraphs = text_with_cursor.split('\n')
        
        cursor_pos_found = None # (line_index, char_index_in_line)
        
        for p_idx, paragraph in enumerate(paragraphs):
            if not paragraph:
                lines.append("")
                continue
                
            words = paragraph.split(' ')
            current_line = []
            current_width = 0
            
            for word in words:
                # Reconstruct word with trailing space if it wasn't the last word
                # Note: simple split(' ') loses delimiters. We'll assume single space.
                # This is a limitation but fits "word is bounded by whitespaces".
                
                # Check width of word
                word_width = self._font_metrics.horizontalAdvance(word)
                space_width = self._font_metrics.horizontalAdvance(" ")
                
                if current_width + word_width + (space_width if current_line else 0) <= max_width:
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
            if CURSOR_MARKER in line:
                visual_cursor_line = idx
                # We don't remove the marker yet, we need it for rendering
            final_lines.append(line)
            
        return final_lines, visual_cursor_line

    def update_display(self):
        """
        Calculate layout, wrap text, handle pagination, and render HTML.
        """
        # Recalculate font metrics in case font changed
        self._font_metrics = QFontMetrics(self.font())

        # Calculate max lines based on height
        # Subtract padding (approx 30px total vertical to be safe against overflow loop)
        available_height = self.height() - 30
        line_height = self._font_metrics.lineSpacing()
        if line_height <= 0:
            line_height = 20 # fallback
            
        self._max_lines = max(1, available_height // line_height)
        
        # Calculate max width
        # Subtract padding (approx 20px horizontal)
        available_width = self.width() - 20
        if available_width <= 0:
            available_width = 100 # fallback

        # Wrap text and find cursor
        lines, cursor_line_idx = self._wrap_text(self._text, available_width)
        
        total_lines = len(lines)
        
        # Determine visible window
        # We want to show max_lines - 1 (reserved for '...') if truncation happens
        
        start_line = 0
        end_line = total_lines
        prefix = ""
        suffix = ""
        
        if total_lines <= self._max_lines:
            # All fits
            visible_lines = lines
        else:
            # Need truncation
            # Max visible content lines = max_lines - 1 (for one '...' line)
            window_size = self._max_lines - 1
            
            if cursor_line_idx < window_size:
                # Cursor is at top/beginning
                start_line = 0
                end_line = window_size
                suffix = "..."
            elif cursor_line_idx >= total_lines - window_size:
                # Cursor is at bottom/end
                start_line = total_lines - window_size
                end_line = total_lines
                prefix = "..."
            else:
                # Cursor in middle - keep it roughly centered or just ensure visibility
                # Requirement: "when the user would move cursor so much that it would return to the beginig... display shoud hide the last lines"
                # It implies a sliding window following the cursor.
                # Let's center the window around cursor if possible, or keep it simple.
                # "show only the last n lines" usually implies bottom anchor.
                # Let's just ensure cursor is visible.
                # If we scroll down, we show prefix. If we scroll up, we show suffix.
                
                # Strategy: Keep cursor line visible.
                # If we are deeper than first page, show prefix.
                # If we are higher than last page, show suffix.
                # Actually, if we are in middle, we might need both ...?
                # User spec: "show only the last n lines... while also showing ... at the top"
                # "when cursor... return to beginning... add ... at the bottom"
                # This implies we only show ONE ellipsis at a time usually? Or possibly both.
                # Let's support both if window is small.
                # But usually max_lines is small.
                
                # Let's simplify: Ensure cursor line is in [start_line, end_line].
                # Prefer showing end if cursor is at end.
                
                start_line = cursor_line_idx - (window_size // 2)
                if start_line < 0: start_line = 0
                end_line = start_line + window_size
                
                if end_line > total_lines:
                    end_line = total_lines
                    start_line = max(0, end_line - window_size)
                
                if start_line > 0:
                    prefix = "..."
                if end_line < total_lines:
                    suffix = "..."
            
            visible_lines = lines[start_line:end_line]

        # Construct HTML
        html_lines = []
        if prefix:
            html_lines.append(f"<div style='color: gray'>{prefix}</div>")
            
        for line in visible_lines:
            # Replace marker with cursor
            line_content = html.escape(line)
            
            cursor_char = "|" if self._cursor_visible else ""
            # We need to replace the NULL char marker
            # Note: html.escape might have escaped NULL? No, usually passes through or strips.
            # Let's check if marker is still there.
            
            if "\0" in line:
                line_content = line_content.replace("\0", cursor_char)
            elif "\0" in line_content: # Paranoia check if escape did something
                line_content = line_content.replace("\0", cursor_char)
            else:
                # If cursor line is visible but marker not found (should not happen if logic correct)
                pass
                
            # Preserve spaces
            line_content = line_content.replace("  ", "&nbsp; ")
            html_lines.append(line_content)

        if suffix:
            html_lines.append(f"<div style='color: gray'>{suffix}</div>")
            
        full_html = "<br>".join(html_lines)
        self.setText(full_html)


class TextDisplayObserver:
    """Observer that handles text display events from virtual keyboard"""
    
    def __init__(self, text_display: PisakDisplay):
        self._text_display = text_display

    @property
    def text_display(self):
        return self._text_display

    def handle_event(self, event: AppEvent) -> None:
        """Handle events for text display - only processes virtual keyboard events"""
        if event.type == AppEventType.TEXT_INPUT:
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
