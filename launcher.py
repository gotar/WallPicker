#!/usr/bin/env python3
"""Launcher script for WallPicker."""

import os
import signal
import sys
import site
from pathlib import Path

# Add user site-packages to support pip --user installs
user_site = site.getusersitepackages()
if user_site not in sys.path:
    sys.path.insert(0, user_site)

# Add src to path for development
project_dir = Path(__file__).parent
src_dir = project_dir / "src"
sys.path.insert(0, str(src_dir))


def main():
    os.chdir(project_dir)

    import gi

    gi.require_version("Gtk", "4.0")
    gi.require_version("Adw", "1")

    from core.asyncio_integration import setup_event_loop
    from ui.main_window import MainWindow

    setup_event_loop()

    app = MainWindow()

    signal.signal(signal.SIGINT, signal.SIG_DFL)

    exit_status = app.run()
    sys.exit(exit_status)


if __name__ == "__main__":
    main()
