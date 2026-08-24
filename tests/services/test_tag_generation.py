"""Tests for TagGenerationService detection logic and subprocess handling."""

import asyncio
import sys
import types
from contextlib import nullcontext
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
from PIL import Image

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


class TestClipAnytorchPipeline:
    """Exercise the real clip-anytorch Python pipeline with mocked modules."""

    @pytest.fixture
    def image_path(self, tmp_path: Path) -> Path:
        path = tmp_path / "wallpaper.png"
        Image.new("RGB", (32, 32), (0, 128, 255)).save(path, "PNG")
        return path

    @staticmethod
    def _install_fake_clip(
        mocker, *, module_name="clip", device_capture: list | None = None
    ):
        """Install minimal fake CLIP + torch modules into sys.modules.

        The fake tensor math maps tag index (k-1) to the highest confidence,
        so parsed output is deterministic.
        """

        class FakeTensor:
            def norm(self, dim=None, keepdim=None):
                return FakeTensor()

            def __itruediv__(self, other):
                return self

            @property
            def T(self):
                return self

            def unsqueeze(self, dim):
                return self

            def to(self, device):
                return self

            def __rmul__(self, scalar):
                # (100.0 * image) @ text — scalar multiply is a no-op for the fake.
                return self

            def __matmul__(self, other):
                return FakeSimilarity()

        class FakeSimilarity:
            def softmax(self, dim=None):
                return self

            def __getitem__(self, idx):
                assert idx == 0
                return self

            def topk(self, k):
                # Highest confidence first; deterministic mapping to tags.
                values = [0.9 - 0.01 * i for i in range(k)]
                indices = [(k - 1 - i) for i in range(k)]  # last tag scores highest
                return values, indices

        fake_model = MagicMock()
        fake_model.encode_image.return_value = FakeTensor()
        fake_model.encode_text.return_value = FakeTensor()

        def fake_load(model_name, device="cpu"):
            if device_capture is not None:
                device_capture.append((model_name, device))
            return fake_model, lambda img: FakeTensor()

        fake_clip = types.ModuleType(module_name)
        fake_clip.load = fake_load
        fake_clip.tokenize = MagicMock(return_value=FakeTensor())

        fake_torch = types.ModuleType("torch")
        fake_torch.no_grad = lambda: nullcontext()
        fake_torch.cuda = types.SimpleNamespace(is_available=lambda: False)

        mocker.patch.dict(sys.modules, {module_name: fake_clip, "torch": fake_torch})
        return fake_clip, fake_model

    def test_successful_tag_parse(self, service, mocker, image_path):
        fake_clip, _ = self._install_fake_clip(mocker)
        mocker.patch.object(service, "_get_tool", return_value="clip-anytorch")

        tags, confidence = asyncio.run(service.generate_tags_async(image_path))

        assert len(tags) == 10  # top-10 cut-off
        assert all(tag in confidence for tag in tags)
        scores = [confidence[tag] for tag in tags]
        assert scores == sorted(scores, reverse=True)  # sorted by confidence desc
        assert all(score >= 0.05 for score in confidence.values())
        # The full common-tag vocabulary was tokenized.
        assert len(fake_clip.tokenize.call_args[0][0]) > 40

    def test_device_selection_uses_cpu_without_cuda(
        self, service, mocker, image_path
    ):
        devices = []
        self._install_fake_clip(mocker, device_capture=devices)
        mocker.patch.object(service, "_get_tool", return_value="clip-anytorch")

        asyncio.run(service.generate_tags_async(image_path))

        assert devices == [("ViT-B/32", "cpu")]

    def test_falls_back_to_clip_anytorch_module(self, service, mocker, image_path):
        """When plain `clip` is absent, the same-API clip_anytorch package is used."""
        assert "clip" not in sys.modules
        self._install_fake_clip(mocker, module_name="clip_anytorch")
        mocker.patch.object(service, "_get_tool", return_value="clip-anytorch")

        tags, confidence = asyncio.run(service.generate_tags_async(image_path))

        # Deterministic fake math: last common tag has the highest score.
        assert len(tags) == 10
        assert all(tag in confidence for tag in tags)

    def test_pillow_handle_closed_after_preprocessing(
        self, service, mocker, image_path
    ):
        """L5: the PIL image handle must be closed inside run_model."""
        close_events = []
        real_open = Image.open

        class RecordingHandle:
            def __init__(self, inner):
                self._inner = inner

            def __enter__(self):
                return self._inner.__enter__()

            def __exit__(self, *args):
                close_events.append("closed")
                return self._inner.__exit__(*args)

        def spy_open(*args, **kwargs):
            return RecordingHandle(real_open(*args, **kwargs))

        fake_pil_image = types.ModuleType("PIL.Image")
        fake_pil_image.open = spy_open
        fake_pil = types.ModuleType("PIL")
        fake_pil.Image = fake_pil_image

        self._install_fake_clip(mocker)
        mocker.patch.dict(
            sys.modules,
            {"PIL": fake_pil, "PIL.Image": fake_pil_image},
            clear=False,
        )
        mocker.patch.object(service, "_get_tool", return_value="clip-anytorch")

        asyncio.run(service.generate_tags_async(image_path))

        assert close_events == ["closed"]

    def test_pipeline_failure_raises_tag_generation_error(
        self, service, mocker, image_path
    ):
        fake_clip, _ = self._install_fake_clip(mocker)
        fake_clip.load = MagicMock(side_effect=RuntimeError("model download failed"))
        mocker.patch.object(service, "_get_tool", return_value="clip-anytorch")

        with pytest.raises(TagGenerationError, match="model download failed"):
            asyncio.run(service.generate_tags_async(image_path))


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


class TestAvailabilityProbes:
    """Direct probe behaviour in an environment without CLIP backends."""

    def test_probe_chain_reports_false_without_backends(self, tmp_path):
        """No clip/clip_anytorch/torch installed => probe returns False."""
        svc = TagGenerationService()
        svc._clip_anytorch_available = None
        sys.modules.pop("clip", None)
        sys.modules.pop("clip_anytorch", None)
        sys.modules.pop("torch", None)

        assert svc._check_clip_anytorch() is False
        assert svc._clip_anytorch_available is False

    def test_cached_positive_result_skips_import(self, service, mocker):
        service._clip_anytorch_available = True

        assert service._check_clip_anytorch() is True


class TestGenerateTagsSyncSuccess:
    def test_sync_success_returns_result(self, service, mocker):
        from unittest.mock import AsyncMock

        expected = (["nature"], {"nature": 0.9})
        mocker.patch.object(service, "_get_tool", return_value="clip-cpp")
        mocker.patch.object(
            service, "_generate_clip_cpp", AsyncMock(return_value=expected)
        )

        result = service.generate_tags_sync(_fake_path())

        assert result == expected


class TestParserRobustnessAndProbes:
    def test_parse_clip_cpp_malformed_confidence_keeps_prior_tags(self, service):
        """A malformed confidence value aborts the remaining lines but keeps
        the tags already parsed before the error."""
        output = "nature: 0.9\nbroken: not-a-number\nsunset: 0.5"

        tags, confidence = service._parse_clip_cpp_output(output)

        assert tags == ["nature"]
        assert confidence == {"nature": pytest.approx(0.9)}

    def test_probe_succeeds_with_plain_clip_and_torch(self, service, mocker):
        """clip + torch importable (without clip_anytorch) => available."""
        fake_clip = types.ModuleType("clip")
        fake_torch = types.ModuleType("torch")
        mocker.patch.dict(sys.modules, {"clip": fake_clip, "torch": fake_torch})
        sys.modules.pop("clip_anytorch", None)

        assert service._check_clip_anytorch() is True


class TestProbeClipAnytorchPackage:
    def test_probe_succeeds_with_clip_anytorch_package_alone(self, service, mocker):
        """clip_anytorch alone (no plain clip/torch) => available."""
        fake_anytorch = types.ModuleType("clip_anytorch")
        mocker.patch.dict(sys.modules, {"clip_anytorch": fake_anytorch})
        sys.modules.pop("clip", None)
        sys.modules.pop("torch", None)

        assert service._check_clip_anytorch() is True
