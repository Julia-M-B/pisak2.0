"""
Run Speller module
"""

import logging
import sys

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import Qt

from aac_app.modules.speller.module import PisakSpellerModule

logger = logging.getLogger(__name__)

def main():
    """Create and run the Speller module test"""
        
    app = QApplication(sys.argv)
    logger.info("Application started.")

    speller_module = PisakSpellerModule()
    
    # Resize window for better visibility
    speller_module.setWindowState(Qt.WindowMaximized)
    
    speller_module.show()
    
    # Run the application event loop
    exit_code = app.exec()
    logger.info("Application closed.")
    sys.exit(exit_code)
        


if __name__ == "__main__":
    main()

