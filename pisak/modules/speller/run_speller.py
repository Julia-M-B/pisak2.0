"""
Run Speller module
"""

import sys

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import Qt

from pisak.modules.speller.module import PisakSpellerModule

def main():
    """Create and run the Speller module test"""
        
    app = QApplication(sys.argv)

    speller_module = PisakSpellerModule()
    
    # Resize window for better visibility
    speller_module.setWindowState(Qt.WindowMaximized)
    
    speller_module.show()
    
    # Run the application event loop
    exit_code = app.exec()
    print("\nApplication closed.")
    sys.exit(exit_code)
        


if __name__ == "__main__":
    main()

