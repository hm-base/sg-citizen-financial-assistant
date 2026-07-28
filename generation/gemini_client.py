import logging
import time
from pathlib import Path
from typing import Protocol

from google import genai

logger = logging.getLogger(__name__)

#: A freshly uploaded video sits in PROCESSING for seconds to minutes; the
#: Files API discards it entirely after 48h, so these only bound one build run.
FILE_ACTIVE_TIMEOUT_SECONDS = 60.0
FILE_POLL_INTERVAL_SECONDS = 2.0


class GenAISdkClient(Protocol):
    def generate_content(self, model: str, contents): ...

    def upload_file(self, path): ...


class GeminiClient:
    def __init__(self, api_key: str, model_name: str, sdk_client=None):
        self.model_name = model_name
        if sdk_client is not None:
            self._sdk_client = sdk_client
        else:
            client = genai.Client(api_key=api_key)
            self._sdk_client = _RealGenAIAdapter(client)

    def generate(self, prompt: str) -> str:
        response = self._sdk_client.generate_content(self.model_name, prompt)
        return response.text

    def transcribe(self, video_path: Path, prompt: str) -> str:
        """Upload the video and transcribe it.

        The video must be attached to the request — prompting without it would
        make the model fabricate a transcript that later gets ingested as if it
        were grounded evidence.
        """
        video_path = Path(video_path)
        if not video_path.exists():
            raise FileNotFoundError(f"Video file not found: {video_path}")
        uploaded_file = self._sdk_client.upload_file(video_path)
        response = self._sdk_client.generate_content(self.model_name, [uploaded_file, prompt])
        return response.text


def _state_name(uploaded_file) -> str:
    """Normalise a File.state to an upper-case string.

    The SDK returns a `types.FileState` enum, but older/newer versions and the
    REST surface have returned bare strings, so accept both.
    """
    state = getattr(uploaded_file, "state", None)
    if state is None:
        return ""
    return str(getattr(state, "name", None) or state).upper()


class _RealGenAIAdapter:
    def __init__(
        self,
        client,
        *,
        sleep=time.sleep,
        monotonic=time.monotonic,
        active_timeout: float = FILE_ACTIVE_TIMEOUT_SECONDS,
        poll_interval: float = FILE_POLL_INTERVAL_SECONDS,
    ):
        self.client = client
        self._sleep = sleep
        self._monotonic = monotonic
        self._active_timeout = active_timeout
        self._poll_interval = poll_interval

    def generate_content(self, model: str, contents):
        return self.client.models.generate_content(model=model, contents=contents)

    def upload_file(self, path):
        uploaded_file = self.client.files.upload(file=str(path))
        return self._wait_until_active(uploaded_file)

    def _wait_until_active(self, uploaded_file):
        """Block until the uploaded file is usable as `generate_content` input.

        `files.upload` returns immediately with the file in PROCESSING state;
        passing that handle straight to `generate_content` is rejected, so a
        video transcription would fail on every first run. Poll until the state
        clears, and return the *refreshed* handle rather than the stale one.
        """
        deadline = self._monotonic() + self._active_timeout
        current = uploaded_file
        while True:
            state = _state_name(current)
            if state == "ACTIVE":
                return current
            if state == "FAILED":
                raise RuntimeError(
                    f"Gemini file processing FAILED for {getattr(current, 'name', '?')} "
                    f"(state={state}); the video cannot be transcribed."
                )
            if self._monotonic() >= deadline:
                raise TimeoutError(
                    f"Gemini file {getattr(current, 'name', '?')} did not reach ACTIVE within "
                    f"{self._active_timeout:.0f}s (last state={state or 'unknown'})."
                )
            logger.info(
                "Waiting for Gemini to finish processing %s (state=%s)",
                getattr(current, "name", "?"),
                state or "unknown",
            )
            self._sleep(self._poll_interval)
            current = self.client.files.get(name=current.name)
