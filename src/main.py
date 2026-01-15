"""Application entry point."""
import sys
import os

# Ensure src directory is in path for imports
if getattr(sys, 'frozen', False):
    # Running as compiled executable
    base_path = sys._MEIPASS
else:
    # Running as script
    base_path = os.path.dirname(os.path.abspath(__file__))

sys.path.insert(0, base_path)

from gui.main_window import main

if __name__ == "__main__":
    main()
