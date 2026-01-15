#!/usr/bin/env python3
"""Run the web GUI."""
import os
import sys
import webbrowser
import threading

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from web.app import app

def open_browser():
    webbrowser.open('http://localhost:5000')

if __name__ == '__main__':
    print("Starting IGEL Profile Compare Web GUI...")
    print("Open http://localhost:5000 in your browser")
    threading.Timer(1.5, open_browser).start()
    app.run(host='0.0.0.0', port=5000, debug=False)
