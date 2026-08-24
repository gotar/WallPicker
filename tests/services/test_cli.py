"""Tests for the headless CLI (services/cli.py)."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.cli import main


@pytest.fixture
def setter_cls():
    with patch("services.wallpaper_setter.WallpaperSetter") as mock_cls:
        yield mock_cls


class TestCli:
    def test_set_success_returns_0(self, setter_cls, capsys):
        instance = setter_cls.return_value
        instance.set_wallpaper_async = AsyncMock(return_value=True)

        rc = main(["set", "/tmp/wp.jpg"])

        assert rc == 0
        instance.set_wallpaper_async.assert_awaited_once_with("/tmp/wp.jpg")
        assert "Wallpaper set" in capsys.readouterr().out

    def test_set_failure_returns_1(self, setter_cls, capsys):
        instance = setter_cls.return_value
        instance.set_wallpaper_async = AsyncMock(return_value=False)

        rc = main(["set", "/tmp/wp.jpg"])

        assert rc == 1
        assert "Failed" in capsys.readouterr().err

    def test_current_prints_path(self, setter_cls, capsys):
        instance = setter_cls.return_value
        instance.get_current_wallpaper = MagicMock(
            return_value="/home/x/Wallpapers/a.jpg"
        )

        rc = main(["current"])

        assert rc == 0
        assert "/home/x/Wallpapers/a.jpg" in capsys.readouterr().out

    def test_current_none_returns_1(self, setter_cls, capsys):
        setter_cls.return_value.get_current_wallpaper = MagicMock(
            return_value=None
        )

        assert main(["current"]) == 1

    def test_no_args_shows_help_and_returns_1(self, capsys):
        assert main([]) == 1
        assert "set" in capsys.readouterr().out

    def test_unknown_command_returns_2(self, capsys):
        assert main(["frobnicate"]) == 2
        assert "Unknown command" in capsys.readouterr().err

    def test_set_requires_exactly_one_path(self, capsys):
        assert main(["set"]) == 2
        assert main(["set", "a", "b"]) == 2

    def test_uses_asyncio_run_when_no_loop(self, setter_cls):
        """Headless context: coroutine executed via asyncio.run."""
        instance = setter_cls.return_value
        instance.set_wallpaper_async = AsyncMock(return_value=True)
        fake_loop = MagicMock()
        fake_loop.is_running.return_value = False

        with patch("asyncio.get_event_loop", return_value=fake_loop), patch(
            "asyncio.run", return_value=True
        ) as mock_run:
            rc = main(["set", "/tmp/wp.jpg"])

        assert rc == 0
        mock_run.assert_called_once()


class TestVersionAndHelp:
    def test_version_flag(self, capsys, setter_cls):
        rc = main(["--version"])
        assert rc == 0
        assert "wallpicker" in capsys.readouterr().out

    def test_short_version_flag(self, capsys, setter_cls):
        rc = main(["-v"])
        assert rc == 0
        out = capsys.readouterr().out
        assert out.strip().startswith("wallpicker ")

    def test_help_flag_shows_gui_usage(self, capsys, setter_cls):
        rc = main(["--help"])
        assert rc == 0
        out = capsys.readouterr().out
        assert "GUI launches" in out
        assert "--version" in out

    def test_no_args_exits_1_with_help(self, capsys, setter_cls):
        rc = main([])
        assert rc == 1
        assert "Usage" in capsys.readouterr().out


class TestWantsCli:
    def test_no_args_launches_gui(self):
        from services.cli import wants_cli

        assert wants_cli([]) is False

    def test_debug_only_launches_gui(self):
        from services.cli import wants_cli

        assert wants_cli(["--debug"]) is False

    def test_set_routes_to_cli(self):
        from services.cli import wants_cli

        assert wants_cli(["set", "/tmp/x.jpg"]) is True
        assert wants_cli(["--debug", "set", "/tmp/x.jpg"]) is True

    def test_current_and_flags_route_to_cli(self):
        from services.cli import wants_cli

        assert wants_cli(["current"]) is True
        assert wants_cli(["-v"]) is True
        assert wants_cli(["--version"]) is True
        assert wants_cli(["-h"]) is True
        assert wants_cli(["--help"]) is True

    def test_unknown_first_arg_launches_gui(self):
        """Anything unrecognized stays GUI (GTK handles its own errors)."""
        from services.cli import wants_cli

        assert wants_cli(["--frobnicate"]) is False
