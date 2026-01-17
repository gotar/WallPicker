#!/usr/bin/env python3
import os
import signal
import sys
from pathlib import Path


def main() -> None:
    project_dir = Path(__file__).parent
    src_dir = project_dir / "src"
    sys.path.insert(0, str(src_dir))

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
