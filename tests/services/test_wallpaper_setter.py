"""
Tests for WallpaperSetter service
"""

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from services.wallpaper_setter import WallpaperSetter


class TestWallpaperSetterInit:
    """Test WallpaperSetter initialization"""

    def test_init_creates_directories(self, tmp_path):
        """Test that initialization creates cache and symlink directories"""
        # Mock home directory to tmp_path
        with patch("pathlib.Path.home", return_value=tmp_path):
            WallpaperSetter()

            cache_dir = tmp_path / ".cache" / "wallpaper"
            symlink_dir = tmp_path / ".config" / "omarchy" / "current"

            assert cache_dir.exists()
            assert symlink_dir.exists()

    def test_init_sets_correct_paths(self):
        """Test that initialization sets correct paths"""
        home = Path.home()

        setter = WallpaperSetter()

        expected_cache = home / ".cache" / "wallpaper"
        expected_symlink = home / ".config" / "omarchy" / "current" / "background"

        assert setter.cache_dir == expected_cache
        assert setter.symlink_path == expected_symlink


class TestSetWallpaper:
    """Test set_wallpaper method"""

    @pytest.fixture
    def test_image_path(self, tmp_path):
        """Create a test image path"""
        test_file = tmp_path / "wallpaper.jpg"
        test_file.write_bytes(b"test image data")
        return str(test_file)

    def _make_omarchy_available(self, setter, return_value=True):
        """Patch the setter to run through the omarchy integration path."""
        patcher = patch.object(
            setter, "_apply_via_omarchy", new=AsyncMock(return_value=return_value)
        )
        patcher.start()
        return patcher

    def test_set_wallpaper_success_via_omarchy(self, test_image_path):
        """Successful omarchy integration must not draw via awww on top"""
        with patch("pathlib.Path.home"):
            setter = WallpaperSetter()

            self._make_omarchy_available(setter, True)
            setter._ensure_daemon_running = AsyncMock()
            setter._apply_wallpaper = AsyncMock()
            setter._save_original_path = MagicMock()
            setter._cleanup_old_wallpapers = MagicMock()

            result = setter.set_wallpaper(test_image_path)

            assert result is True
            setter._apply_via_omarchy.assert_awaited_once()
            # awww must not double-draw over the shell-rendered background
            setter._ensure_daemon_running.assert_not_called()
            setter._apply_wallpaper.assert_not_called()
            setter._save_original_path.assert_called_once()
            setter._cleanup_old_wallpapers.assert_called_once()

    def test_set_wallpaper_non_existent_path(self):
        """Test setting wallpaper with non-existent path"""
        with patch("pathlib.Path.home"):
            setter = WallpaperSetter()

            result = setter.set_wallpaper("/non/existent/path.jpg")

            # Should return False for non-existent file
            assert result is False

    def test_set_wallpaper_exception(self, test_image_path):
        """Exceptions on the fallback path are caught and return False"""
        with patch("pathlib.Path.home"):
            setter = WallpaperSetter()

            self._make_omarchy_available(setter, False)
            with patch.object(
                setter,
                "_ensure_daemon_running",
                new=AsyncMock(side_effect=RuntimeError("no daemon")),
            ):
                result = setter.set_wallpaper(test_image_path)

                # Should return False on exception
                assert result is False

    def test_set_wallpaper_calls_in_order(self, test_image_path):
        """Fallback path order: daemon -> symlinks -> original -> apply"""
        with patch("pathlib.Path.home"):
            setter = WallpaperSetter()

            call_order = []

            async def fake_daemon():
                call_order.append("daemon")

            async def fake_omarchy(_):
                call_order.append("omarchy")
                return False

            def fake_symlink(link, _target):
                call_order.append(
                    "state_link" if link == setter.state_link_path else "legacy_link"
                )

            async def fake_apply(_):
                call_order.append("apply")

            setter._ensure_daemon_running = fake_daemon
            setter._apply_via_omarchy = fake_omarchy
            setter._atomic_symlink = fake_symlink
            setter._save_original_path = lambda *_: call_order.append("save")
            setter._apply_wallpaper = fake_apply
            setter._cleanup_old_wallpapers = MagicMock()

            assert setter.set_wallpaper(test_image_path) is True
            assert call_order == [
                "omarchy",
                "daemon",
                "state_link",
                "legacy_link",
                "save",
                "apply",
            ]


class TestEnsureDaemonRunning:
    """Test _ensure_daemon_running method"""

    def test_ensure_daemon_already_running(self):
        """Test when daemon is already running"""
        with patch("pathlib.Path.home"):
            setter = WallpaperSetter()

        mock_pgrep = AsyncMock()
        mock_pgrep.returncode = 0
        mock_pgrep.communicate = AsyncMock(return_value=(b"", b""))

        with patch(
            "asyncio.create_subprocess_exec", new=AsyncMock(return_value=mock_pgrep)
        ) as mock_exec:
            import asyncio

            asyncio.run(setter._ensure_daemon_running())

            mock_exec.assert_called_once_with(
                "pgrep",
                "-x",
                "awww-daemon",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

    def test_ensure_daemon_not_running(self):
        """Test when daemon is not running"""
        with patch("pathlib.Path.home"):
            setter = WallpaperSetter()

        mock_pgrep = AsyncMock()
        mock_pgrep.returncode = 1
        mock_pgrep.communicate = AsyncMock(return_value=(b"", b""))

        mock_daemon = AsyncMock()
        mock_daemon.communicate = AsyncMock(return_value=(b"", b""))

        with patch(
            "asyncio.create_subprocess_exec",
            new=AsyncMock(side_effect=[mock_pgrep, mock_daemon]),
        ) as mock_exec:
            with patch("asyncio.sleep", new=AsyncMock()) as mock_sleep:
                import asyncio

                asyncio.run(setter._ensure_daemon_running())

                assert mock_exec.call_count == 2
                assert mock_exec.call_args_list == [
                    call(
                        "pgrep",
                        "-x",
                        "awww-daemon",
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE,
                    ),
                    call(
                        "awww-daemon",
                        stdout=asyncio.subprocess.DEVNULL,
                        stderr=asyncio.subprocess.DEVNULL,
                    ),
                ]
                mock_sleep.assert_awaited_once_with(1)

    def test_ensure_daemon_pgrep_args(self):
        """Test that pgrep is called with correct arguments"""
        with patch("pathlib.Path.home"):
            setter = WallpaperSetter()

        mock_pgrep = AsyncMock()
        mock_pgrep.returncode = 1
        mock_pgrep.communicate = AsyncMock(return_value=(b"", b""))

        mock_daemon = AsyncMock()
        mock_daemon.communicate = AsyncMock(return_value=(b"", b""))

        with patch(
            "asyncio.create_subprocess_exec",
            new=AsyncMock(side_effect=[mock_pgrep, mock_daemon]),
        ) as mock_exec:
            with patch("asyncio.sleep", new=AsyncMock()):
                import asyncio

                asyncio.run(setter._ensure_daemon_running())

                first_call = mock_exec.call_args_list[0]
                assert first_call.args[0] == "pgrep"
                assert "-x" in first_call.args
                assert "awww-daemon" in first_call.args


class TestAtomicSymlink:
    """Test _atomic_symlink helper (tmp link + os.replace swap)"""

    def test_atomic_symlink_new(self, tmp_path):
        """Creating a symlink where none exists"""
        test_image = tmp_path / "wallpaper.jpg"
        test_image.write_bytes(b"test")
        link = tmp_path / "current" / "background"

        WallpaperSetter._atomic_symlink(link, test_image)

        assert link.is_symlink()
        assert link.resolve() == test_image

    def test_atomic_symlink_replaces_existing(self, tmp_path):
        """Existing symlink (or regular file) is replaced atomically"""
        old_target = tmp_path / "old.jpg"
        old_target.write_bytes(b"old")
        new_target = tmp_path / "new.jpg"
        new_target.write_bytes(b"new")
        link = tmp_path / "background"
        link.symlink_to(old_target)

        WallpaperSetter._atomic_symlink(link, new_target)

        assert link.resolve() == new_target

    def test_atomic_symlink_replaces_regular_file(self, tmp_path):
        """A regular file at the link position does not raise FileExistsError"""
        target = tmp_path / "wp.jpg"
        target.write_bytes(b"x")
        link = tmp_path / "background"
        link.write_text("not a symlink")

        WallpaperSetter._atomic_symlink(link, target)

        assert link.is_symlink()
        assert link.resolve() == target

    def test_atomic_symlink_leaves_no_tmp_files(self, tmp_path):
        """No .tmp leftovers on success"""
        target = tmp_path / "wp.jpg"
        target.write_bytes(b"x")
        link_dir = tmp_path / "d"
        link = link_dir / "background"

        WallpaperSetter._atomic_symlink(link, target)

        assert list(link_dir.glob("*.tmp*")) == []


class TestApplyViaOmarchy:
    """Test the omarchy-theme-bg-set integration path"""

    def _make_process(self, returncode=0, stderr=b""):
        proc = AsyncMock()
        proc.returncode = returncode
        proc.communicate = AsyncMock(return_value=(b"", stderr))
        return proc

    async def test_uses_omarchy_theme_bg_set(self, tmp_path):
        image = tmp_path / "wp.jpg"
        image.write_bytes(b"x")
        with patch("pathlib.Path.home"):
            setter = WallpaperSetter()
        setter.symlink_path = tmp_path / "legacy" / "background"
        setter.state_link_path = tmp_path / "state" / "background"

        with patch("shutil.which", return_value="/usr/bin/omarchy-theme-bg-set"):
            with patch(
                "asyncio.create_subprocess_exec",
                new=AsyncMock(return_value=self._make_process(0)),
            ) as mock_exec:
                result = await setter._apply_via_omarchy(image)

        assert result is True
        args = mock_exec.call_args.args
        assert args[0] == "omarchy-theme-bg-set"
        assert args[1] == str(image)
        # legacy link kept in sync for old consumers
        assert setter.symlink_path.is_symlink()
        assert setter.symlink_path.resolve() == image

    async def test_returns_false_when_command_missing(self, tmp_path):
        image = tmp_path / "wp.jpg"
        image.write_bytes(b"x")
        with patch("pathlib.Path.home"):
            setter = WallpaperSetter()

        with patch("shutil.which", return_value=None):
            result = await setter._apply_via_omarchy(image)

        assert result is False

    async def test_returns_false_on_non_zero_exit(self, tmp_path):
        image = tmp_path / "wp.jpg"
        image.write_bytes(b"x")
        with patch("pathlib.Path.home"):
            setter = WallpaperSetter()
        setter.symlink_path = tmp_path / "legacy" / "background"

        with patch("shutil.which", return_value="/usr/bin/omarchy-theme-bg-set"):
            with patch(
                "asyncio.create_subprocess_exec",
                new=AsyncMock(
                    return_value=self._make_process(1, stderr=b"boom")
                ),
            ):
                result = await setter._apply_via_omarchy(image)

        assert result is False
        # legacy link must not be touched on failure
        assert not setter.symlink_path.exists()


class TestApplyWallpaper:
    """Test _apply_wallpaper method"""

    def test_apply_wallpaper_command(self):
        """Test that correct awww command is run"""
        with patch("pathlib.Path.home"):
            setter = WallpaperSetter()

        test_path = Path("/test/wallpaper.jpg")

        mock_process = AsyncMock()
        mock_process.returncode = 0
        mock_process.communicate = AsyncMock(return_value=(b"", b""))

        with patch(
            "asyncio.create_subprocess_exec", new=AsyncMock(return_value=mock_process)
        ) as mock_exec:
            import asyncio

            asyncio.run(setter._apply_wallpaper(test_path))

            # Check awww command arguments
            call_args = mock_exec.call_args
            cmd = call_args.args

            assert cmd[0] == "awww"
            assert "img" in cmd
            assert "--transition-type" in cmd
            assert "random" in cmd
            assert "--transition-fps" in cmd
            assert "60" in cmd
            assert "--transition-duration" in cmd
            assert "3" in cmd
            assert "--transition-bezier" in cmd
            assert str(test_path) in cmd
            assert "--transition-bezier" in cmd
            assert ".43,1.19,1,.4" in cmd

    def test_apply_wallpaper_raises_on_non_zero_exit(self):
        """Test that non-zero exit status raises RuntimeError"""
        with patch("pathlib.Path.home"):
            setter = WallpaperSetter()

        test_path = Path("/test/wallpaper.jpg")

        mock_process = AsyncMock()
        mock_process.returncode = 1
        mock_process.communicate = AsyncMock(return_value=(b"", b"awww failed"))

        with patch(
            "asyncio.create_subprocess_exec", new=AsyncMock(return_value=mock_process)
        ):
            import asyncio

            with pytest.raises(RuntimeError, match="awww failed"):
                asyncio.run(setter._apply_wallpaper(test_path))


class TestCleanupOldWallpapers:
    """Test _cleanup_old_wallpapers method"""

    def test_cleanup_removes_old_files(self, tmp_path):
        """Test that old wallpapers are removed"""
        with patch("pathlib.Path.home", return_value=tmp_path):
            setter = WallpaperSetter()

            # Create more than 10 wallpaper files in cache_dir
            for i in range(15):
                wallpaper_file = setter.cache_dir / f"wallpaper_{i}.jpg"
                wallpaper_file.write_bytes(b"test")

            import time

            # Make some files newer
            time.sleep(0.01)
            for i in range(5):
                wallpaper_file = setter.cache_dir / f"wallpaper_{i}.jpg"
                wallpaper_file.write_bytes(b"newer")

            setter._cleanup_old_wallpapers()

            # Should keep only 10 files (the newest ones)
            remaining = list(setter.cache_dir.glob("wallpaper_*.jpg"))
            assert len(remaining) == 10

    def test_cleanup_ignores_non_wallpaper_files(self, tmp_path):
        """Test that non-wallpaper files are not deleted"""
        with patch("pathlib.Path.home", return_value=tmp_path):
            setter = WallpaperSetter()

            # Create wallpaper and non-wallpaper files
            for i in range(5):
                (tmp_path / f"wallpaper_{i}.jpg").write_bytes(b"wp")
                (tmp_path / f"other_{i}.txt").write_bytes(b"txt")

            setter._cleanup_old_wallpapers()

            # Only wallpaper files should be affected
            list(tmp_path.glob("wallpaper_*.jpg"))
            other_files = list(tmp_path.glob("other_*.txt"))

            # Some wallpaper files might be deleted if >10, but other files should remain
            assert len(other_files) == 5

    def test_cleanup_no_files(self, tmp_path):
        """Test cleanup when no wallpapers exist"""
        with patch("pathlib.Path.home", return_value=tmp_path):
            setter = WallpaperSetter()

            # No wallpaper files exist
            setter._cleanup_old_wallpapers()

            # Should not raise error, and no wallpaper files should exist afterwards
            assert list(setter.cache_dir.glob("wallpaper_*")) == []

    def test_cleanup_exactly_ten_files(self, tmp_path):
        """Test cleanup with exactly 10 files"""
        with patch("pathlib.Path.home", return_value=tmp_path):
            setter = WallpaperSetter()

            # Create exactly 10 wallpaper files
            for i in range(10):
                wallpaper_file = tmp_path / f"wallpaper_{i}.jpg"
                wallpaper_file.write_bytes(b"test")

            initial_count = len(list(tmp_path.glob("wallpaper_*.jpg")))
            assert initial_count == 10

            setter._cleanup_old_wallpapers()

            # Should keep all 10 files
            remaining = list(tmp_path.glob("wallpaper_*.jpg"))
            assert len(remaining) == 10


class TestGetCurrentWallpaper:
    """Test get_current_wallpaper method"""

    def test_get_current_wallpaper_exists(self, tmp_path):
        """Test getting current wallpaper when symlink exists"""
        with patch("pathlib.Path.home", return_value=tmp_path):
            setter = WallpaperSetter()

            # Create symlink and target
            target_file = tmp_path / "current.jpg"
            target_file.write_bytes(b"current wallpaper")
            setter.symlink_path.symlink_to(target_file)

            result = setter.get_current_wallpaper()

            assert result == str(target_file)

    def test_get_current_wallpaper_no_symlink(self, tmp_path):
        """Test getting current wallpaper when symlink doesn't exist"""
        with patch("pathlib.Path.home", return_value=tmp_path):
            setter = WallpaperSetter()

            result = setter.get_current_wallpaper()

            # Should return None
            assert result is None

    def test_get_current_wallpaper_target_missing(self, tmp_path):
        """Test getting current wallpaper when symlink target is missing"""
        with patch("pathlib.Path.home", return_value=tmp_path):
            setter = WallpaperSetter()

            # Create symlink to non-existent file
            setter.symlink_path.symlink_to(tmp_path / "missing.jpg")

            result = setter.get_current_wallpaper()

            # Should return None
            assert result is None


class TestSetWallpaperAsyncFailurePaths:
    """Test set_wallpaper_async failure handling"""

    @pytest.fixture
    def test_image_path(self, tmp_path):
        """Create a test image path"""
        test_file = tmp_path / "wallpaper.jpg"
        test_file.write_bytes(b"test image data")
        return str(test_file)

    def test_returns_false_when_daemon_check_fails(self, test_image_path):
        """OSError while probing the daemon results in False, not an exception"""
        with patch("pathlib.Path.home"):
            setter = WallpaperSetter()

        with patch.object(setter, "_apply_via_omarchy", new=AsyncMock(return_value=False)):
            with patch.object(
                setter,
                "_ensure_daemon_running",
                side_effect=OSError("pgrep missing"),
            ):
                import asyncio

                assert asyncio.run(setter.set_wallpaper_async(test_image_path)) is False

    def test_returns_false_when_apply_wallpaper_raises(self, test_image_path):
        """A failing awww transition is reported as False"""
        with patch("pathlib.Path.home"):
            setter = WallpaperSetter()

        with patch.object(setter, "_apply_via_omarchy", new=AsyncMock(return_value=False)):
            with patch.object(setter, "_ensure_daemon_running", new=AsyncMock()):
                with patch.object(
                    setter,
                    "_apply_wallpaper",
                    new=AsyncMock(side_effect=RuntimeError("awww failed")),
                ):
                    import asyncio

                    result = asyncio.run(
                        setter.set_wallpaper_async(test_image_path)
                    )

                    assert result is False

    def test_sync_set_wallpaper_swallows_unexpected_errors(self, test_image_path):
        """set_wallpaper returns False instead of raising on unexpected errors"""
        with patch("pathlib.Path.home"):
            setter = WallpaperSetter()

            with patch(
                "services.wallpaper_setter.get_event_loop",
                side_effect=ValueError("loop broken"),
            ):
                result = setter.set_wallpaper(test_image_path)

                # ValueError propagates out of asyncio.run fallback -> caught
                assert result is False

    def test_returns_false_when_symlink_update_fails(self, test_image_path):
        """Symlink creation failure (e.g. read-only dir) results in False"""
        with patch("pathlib.Path.home"):
            setter = WallpaperSetter()

        with patch.object(setter, "_apply_via_omarchy", new=AsyncMock(return_value=False)):
            with patch.object(setter, "_ensure_daemon_running", new=AsyncMock()):
                with patch.object(
                    setter,
                    "_atomic_symlink",
                    side_effect=OSError("read-only file system"),
                ):
                    import asyncio

                    result = asyncio.run(
                        setter.set_wallpaper_async(test_image_path)
                    )

                    assert result is False

    async def test_async_returns_false_for_missing_file(self):
        """Non-existent source returns False without spawning anything"""
        with patch("pathlib.Path.home"):
            setter = WallpaperSetter()

            assert await setter.set_wallpaper_async("/nonexistent/wp.jpg") is False
