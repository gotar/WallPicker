#!/usr/bin/env python3
import os
import sys
from pathlib import Path

# Add src directory to path FIRST
project_dir = Path(__file__).parent
src_dir = project_dir / "src"
sys.path.insert(0, str(src_dir))  # noqa: E402

# Change to project directory
os.chdir(project_dir)

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import GLib  # noqa: E402

# Set up asyncio event loop for GTK integration
from core.asyncio_integration import process_pending, setup_event_loop  # noqa: E402

loop = setup_event_loop()

# Schedule periodic processing of asyncio events
GLib.timeout_add(10, lambda: (process_pending(), True)[1])

# Import and run main
from ui.main_window import MainWindow  # noqa: E402

app = MainWindow()
exit_status = app.run()
sys.exit(exit_status)
