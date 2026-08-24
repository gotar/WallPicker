"""Tests for TagGenerationService detection logic and subprocess handling."""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from services.tag_generation import TagGenerationError, TagGenerationService


@pytest.fixture
def service() -> TagGenerationService:
    """Create a TagGenerationService with cleared availability cache."""
    svc = TagGenerationService()
    svc._clip_anytorch_available = None
    svc._clip_cpp_available = None
    return svc


class TestToolDetection:
    """Test tool detection and fallback behaviour (M8)."""

    def test_prefers_clip_anytorch(self, service, mocker):
        """clip-anytorch is preferred over clip-cpp when both exist."""
        mocker.patch.object(service, "_check_clip_anytorch", return_value=True)
        mocker.patch.object(service, "_check_clip_cpp", return_value=True)

        assert service._get_tool() == "clip-anytorch"

    def test_falls_back_to_clip_cpp(self, service, mocker):
        """When clip-anytorch is missing, clip-cpp is used."""
        mocker.patch.object(service, "_check_clip_anytorch", return_value=False)
        mocker.patch.object(service, "_check_clip_cpp", return_value=True)

        assert service._get_tool() == "clip-cpp"

    def test_no_tool_available(self, service, mocker):
        """With neither tool present, no tool is reported."""
        mocker.patch.object(service, "_check_clip_anytorch", return_value=False)
        mocker.patch.object(service, "_check_clip_cpp", return_value=False)

        assert service._get_tool() is None
        assert service.is_available() is False

    def test_is_available_true_with_any_tool(self, service, mocker):
        mocker.patch.object(service, "_check_clip_anytorch", return_value=False)
        mocker.patch.object(service, "_check_clip_cpp", return_value=True)

        assert service.is_available() is True

    def test_probe_result_is_cached(self, service, mocker):
        """Availability probes run only once per backend."""
        which_mock = mocker.patch(
            "services.tag_generation.shutil.which", return_value="/usr/bin/clip-cpp"
        )

        assert service._check_clip_cpp() is True
        assert service._check_clip_cpp() is True
        # Only one probe: the first successful which("clip-cpp") result is cached.
        assert which_mock.call_count == 1

    def test_generate_tags_raises_without_tool(self, service, mocker):
        mocker.patch.object(service, "_get_tool", return_value=None)

        with pytest.raises(TagGenerationError, match="No tag generation tool"):
            asyncio.run(service.generate_tags_async(_fake_path()))

    def test_unknown_tool_raises(self, service, mocker):
        mocker.patch.object(service, "_get_tool", return_value="nonexistent-tool")

        with pytest.raises(TagGenerationError, match="Unknown tool"):
            asyncio.run(service.generate_tags_async(_fake_path()))


class TestClipCppSubprocess:
    """Test the clip-cpp subprocess paths."""

    def test_success_parses_output(self, service, mocker):
        """Successful CLI run parses tags above the confidence threshold."""
        proc = _mock_process(returncode=0, stdout=b"nature: 0.85\nsunset: 0.72\n")

        mocker.patch.object(service, "_check_clip_anytorch", return_value=False)
        mocker.patch.object(service, "_check_clip_cpp", return_value=True)
        mocker.patch(
            "asyncio.create_subprocess_exec", new=AsyncMock(return_value=proc)
        )

        tags, confidence = asyncio.run(
            service.generate_tags_async(_fake_path())
        )

        assert tags == ["nature", "sunset"]
        assert confidence["nature"] == pytest.approx(0.85)

    def test_timeout_kills_process_and_raises(self, service, mocker):
        """A hung clip-cpp process is killed and surfaces as TagGenerationError (C3)."""
        proc = _mock_process(returncode=None, hang=True)

        mocker.patch.object(service, "_check_clip_anytorch", return_value=False)
        mocker.patch.object(service, "_check_clip_cpp", return_value=True)
        mocker.patch(
            "asyncio.create_subprocess_exec", new=AsyncMock(return_value=proc)
        )
        service.SUBPROCESS_TIMEOUT_SECONDS = 0.01

        with pytest.raises(TagGenerationError, match="timed out"):
            asyncio.run(service.generate_tags_async(_fake_path()))

        proc.kill.assert_called_once()
        # The killed process is reaped so no zombie remains.
        assert proc.communicate_calls == 2

    def test_nonzero_exit_raises(self, service, mocker):
        proc = _mock_process(returncode=1, stderr=b"model load failed")

        mocker.patch.object(service, "_check_clip_anytorch", return_value=False)
        mocker.patch.object(service, "_check_clip_cpp", return_value=True)
        mocker.patch(
            "asyncio.create_subprocess_exec", new=AsyncMock(return_value=proc)
        )

        with pytest.raises(TagGenerationError, match="model load failed"):
            asyncio.run(service.generate_tags_async(_fake_path()))

    def test_missing_binary_raises_and_invalidates_cache(self, service, mocker):
        mocker.patch.object(service, "_check_clip_anytorch", return_value=False)
        mocker.patch.object(service, "_check_clip_cpp", return_value=True)
        mocker.patch(
            "asyncio.create_subprocess_exec",
            new=AsyncMock(side_effect=FileNotFoundError()),
        )

        with pytest.raises(TagGenerationError, match="not found in PATH"):
            asyncio.run(service.generate_tags_async(_fake_path()))

        assert service._clip_cpp_available is False


class TestParsers:
    """Test output parsing helpers."""

    def test_parse_clip_cpp_output_threshold(self, service):
        output = "nature: 0.9\nnoise line\nmountain: 0.1\nsunset: 0.5"
        tags, confidence = service._parse_clip_cpp_output(output)

        assert tags == ["nature", "sunset"]
        assert "mountain" not in confidence

    def test_parse_clip_cpp_empty_output(self, service):
        assert service._parse_clip_cpp_output("") == ([], {})

    def test_parse_clip_anytorch_python_sorting_and_cutoff(self, service):
        results = {f"tag{i}": i / 100 for i in range(15)}
        results["strong"] = 0.99

        tags, confidence = service._parse_clip_anytorch_python(results)

        assert len(tags) <= 10
        assert tags[0] == "strong"
        assert all(score >= 0.05 for score in confidence.values())

    def test_parse_clip_anytorch_python_empty(self, service):
        assert service._parse_clip_anytorch_python({}) == ([], {})


class TestGenerateTagsSync:
    def test_sync_returns_empty_on_failure(self, service, mocker):
        mocker.patch.object(service, "_get_tool", return_value=None)

        assert service.generate_tags_sync(_fake_path()) == ([], {})


def _fake_path():
    from pathlib import Path

    return Path("/tmp/nonexistent.jpg")


def _mock_process(returncode, stdout=b"", stderr=b"", hang=False):
    proc = AsyncMock()
    proc.returncode = returncode
    if hang:
        proc.communicate_calls = 0

        async def slow_communicate():
            proc.communicate_calls += 1
            if proc.communicate_calls == 1:
                # First call hangs until wait_for cancels it.
                await asyncio.sleep(30)
            return b"", b""  # Subsequent call: process was killed, reaps instantly

        proc.communicate = slow_communicate
        proc.kill = MagicMock()
    else:
        proc.communicate = AsyncMock(return_value=(stdout, stderr))
    return proc
