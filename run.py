"""Run the application."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))
from gui.main_window import main
main()
