"""Gemini REST client for extraction. See docs/EXTRACTION_CONTRACT.md's
"Model configuration" section: JSON response mode, temperature 0, token-
bucket rate limiting, backoff+jitter on 429, retry malformed JSON up to 2x.

No google-generativeai SDK dependency - a plain httpx call, consistent with
the rest of ingestion/*.
"""

import json
import logging
import random
import time

import httpx
from pydantic import ValidationError

from app.config import settings
from extraction.contract import LLMResponse

logger = logging.getLogger(__name__)

_API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"
_MAX_MALFORMED_JSON_RETRIES = 2
_MAX_429_RETRIES = 4


class ExtractionRequestError(Exception):
    """Raised when the model could not produce a usable response after all
    retries - a distinct, named reason, not a bare exception."""


class TokenBucketLimiter:
    """Simplest possible token bucket: at most `rpm` calls per rolling
    60-second window, single process (no distributed state needed - the
    pipeline runs as one process per AGENTS.md's "no worker" constraint)."""

    def __init__(self, rpm: int) -> None:
        self._rpm = rpm
        self._request_times: list[float] = []

    def acquire(self) -> None:
        now = time.monotonic()
        window_start = now - 60.0
        self._request_times = [t for t in self._request_times if t > window_start]

        if len(self._request_times) >= self._rpm:
            sleep_for = self._request_times[0] + 60.0 - now
            if sleep_for > 0:
                time.sleep(sleep_for)

        self._request_times.append(time.monotonic())


class GeminiClient:
    def __init__(
        self,
        api_key: str | None = None,
        model_name: str | None = None,
        rpm: int | None = None,
    ) -> None:
        self._api_key = api_key if api_key is not None else settings.GEMINI_API_KEY
        self._model_name = model_name or settings.GEMINI_MODEL_NAME
        self._limiter = TokenBucketLimiter(
            rpm if rpm is not None else settings.GEMINI_RPM
        )
        self._client = httpx.Client(timeout=60.0)

    def close(self) -> None:
        self._client.close()

    def extract(self, prompt: str) -> LLMResponse:
        if not self._api_key:
            raise ExtractionRequestError(
                "GEMINI_API_KEY is not set - cannot call the live API"
            )

        last_error: Exception | None = None
        for attempt in range(_MAX_MALFORMED_JSON_RETRIES + 1):
            raw_text = self._call_with_backoff(prompt)
            try:
                payload = json.loads(raw_text)
                return LLMResponse.model_validate(payload)
            except (json.JSONDecodeError, ValidationError) as exc:
                last_error = exc
                logger.warning(
                    "malformed model response on attempt %d/%d: %s",
                    attempt + 1,
                    _MAX_MALFORMED_JSON_RETRIES + 1,
                    exc,
                )

        raise ExtractionRequestError(
            f"model response was not valid JSON matching the contract after "
            f"{_MAX_MALFORMED_JSON_RETRIES + 1} attempts: {last_error}"
        )

    def _call_with_backoff(self, prompt: str) -> str:
        url = f"{_API_BASE}/{self._model_name}:generateContent"
        body = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0,
                "responseMimeType": "application/json",
            },
        }

        for attempt in range(_MAX_429_RETRIES):
            self._limiter.acquire()
            response = self._client.post(url, params={"key": self._api_key}, json=body)

            if response.status_code == 429:
                backoff = (2**attempt) + random.uniform(0, 1)
                logger.warning("429 from Gemini, backing off %.1fs", backoff)
                time.sleep(backoff)
                continue

            response.raise_for_status()
            data = response.json()
            text: str = data["candidates"][0]["content"]["parts"][0]["text"]
            return text

        raise ExtractionRequestError("exceeded 429 retry budget")
