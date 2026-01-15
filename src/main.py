"""Main entry point for IGEL Profile Compare & Migration Tool."""

import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.gui.main_window import main

if __name__ == "__main__":
    main()
