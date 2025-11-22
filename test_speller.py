"""
Test file for PisakSpellerModule.
This script creates and displays the Speller module to test:
- Display widget with visible cursor
- Virtual keyboard with buttons
- Scanning functionality
- Text input via virtual keyboard (not real keyboard)
- Event system integration
"""

import sys
import os

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

from pisak.modules.speller.module import PisakSpellerModule

def main():
    """Create and run the Speller module test"""
        
    app = QApplication(sys.argv)
    
    # Create the Speller module
    print("Creating PisakSpellerModule...")
    speller_module = PisakSpellerModule()
    
    # Resize window for better visibility
    speller_module.resize(1200, 800)
    
    # Show the module
    print("\n" + "="*60)
    print("PisakSpellerModule Test")
    print("="*60)
    print("\nInstructions:")
    print("  ✓ Use mouse to click virtual keyboard buttons")
    print("  ✓ Text should appear in the display above")
    print("  ✓ Real keyboard input should be IGNORED")
    print("  ✓ Cursor should blink in the text display")
    print("  ✓ Click 'ABC' button to switch to uppercase keyboard")
    print("  ✓ Click 'abc' button to switch back to lowercase")
    print("  ✓ Use arrow buttons (← →) to move cursor")
    print("  ✓ Use ⌫ button for backspace")
    print("  ✓ Use ⏎ button for newline")
    print("  ✓ Close window to exit")
    print("\n" + "="*60 + "\n")
    
    speller_module.show()
    
    # Run the application event loop
    exit_code = app.exec()
    print("\nApplication closed.")
    sys.exit(exit_code)
        


if __name__ == "__main__":
    main()

