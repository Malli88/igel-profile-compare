#!/usr/bin/env python3
"""Run script for IGEL Profile Compare & Migration Tool."""

import sys
import os

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from src.gui.main_window import main

if __name__ == "__main__":
    main()
