import json

import httpx
import pytest

from extraction.gemini_client import (
    ExtractionRequestError,
    GeminiClient,
    TokenBucketLimiter,
)

_VALID_PAYLOAD = {
    "fields": [
        {
            "field": "claim_amount",
            "value_text": "Rs. 26,42,000/-",
            "evidence": {
                "quote": "directed refund of Rs. 26,42,000/-",
                "page": 4,
            },
        }
    ],
    "not_found": [],
}


def _gemini_envelope(text: str) -> dict[str, object]:
    return {"candidates": [{"content": {"parts": [{"text": text}]}}]}


def _client_with_transport(transport: httpx.MockTransport) -> GeminiClient:
    client = GeminiClient(api_key="test-key", model_name="gemini-1.5-flash", rpm=1000)
    client._client = httpx.Client(transport=transport)
    return client


class TestGeminiClientExtract:
    def test_valid_response_parses_into_llm_response(self) -> None:
        transport = httpx.MockTransport(
            lambda request: httpx.Response(
                200, json=_gemini_envelope(json.dumps(_VALID_PAYLOAD))
            )
        )
        client = _client_with_transport(transport)
        result = client.extract("some prompt")
        assert len(result.fields) == 1
        assert result.fields[0].field == "claim_amount"

    def test_missing_api_key_raises_without_network_call(self) -> None:
        called = False

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal called
            called = True
            return httpx.Response(200, json=_gemini_envelope("{}"))

        client = GeminiClient(api_key="", model_name="gemini-1.5-flash", rpm=1000)
        client._client = httpx.Client(transport=httpx.MockTransport(handler))

        with pytest.raises(ExtractionRequestError):
            client.extract("some prompt")
        assert called is False

    def test_malformed_json_retries_then_succeeds(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        calls = {"count": 0}

        def handler(request: httpx.Request) -> httpx.Response:
            calls["count"] += 1
            if calls["count"] == 1:
                return httpx.Response(200, json=_gemini_envelope("not json at all"))
            return httpx.Response(
                200, json=_gemini_envelope(json.dumps(_VALID_PAYLOAD))
            )

        client = _client_with_transport(httpx.MockTransport(handler))
        result = client.extract("some prompt")
        assert calls["count"] == 2
        assert len(result.fields) == 1

    def test_persistently_malformed_json_raises_after_retries(self) -> None:
        transport = httpx.MockTransport(
            lambda request: httpx.Response(200, json=_gemini_envelope("not json"))
        )
        client = _client_with_transport(transport)
        with pytest.raises(ExtractionRequestError):
            client.extract("some prompt")

    def test_response_violating_contract_is_treated_as_malformed(self) -> None:
        # value_text empty is explicitly a contract violation, not just bad JSON
        bad_payload = {
            "fields": [
                {
                    "field": "claim_amount",
                    "value_text": "",
                    "evidence": {"quote": "some quote here", "page": 1},
                }
            ],
            "not_found": [],
        }
        transport = httpx.MockTransport(
            lambda request: httpx.Response(
                200, json=_gemini_envelope(json.dumps(bad_payload))
            )
        )
        client = _client_with_transport(transport)
        with pytest.raises(ExtractionRequestError):
            client.extract("some prompt")

    def test_429_retried_with_backoff_then_succeeds(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr("extraction.gemini_client.time.sleep", lambda _: None)
        calls = {"count": 0}

        def handler(request: httpx.Request) -> httpx.Response:
            calls["count"] += 1
            if calls["count"] == 1:
                return httpx.Response(429)
            return httpx.Response(
                200, json=_gemini_envelope(json.dumps(_VALID_PAYLOAD))
            )

        client = _client_with_transport(httpx.MockTransport(handler))
        result = client.extract("some prompt")
        assert calls["count"] == 2
        assert len(result.fields) == 1


class TestTokenBucketLimiter:
    def test_allows_calls_up_to_rpm_without_sleeping(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        sleep_calls: list[float] = []
        monkeypatch.setattr(
            "extraction.gemini_client.time.sleep", lambda s: sleep_calls.append(s)
        )
        limiter = TokenBucketLimiter(rpm=3)
        limiter.acquire()
        limiter.acquire()
        limiter.acquire()
        assert sleep_calls == []

    def test_sleeps_once_rpm_exceeded_within_window(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        sleep_calls: list[float] = []
        monkeypatch.setattr(
            "extraction.gemini_client.time.sleep", lambda s: sleep_calls.append(s)
        )
        limiter = TokenBucketLimiter(rpm=2)
        limiter.acquire()
        limiter.acquire()
        limiter.acquire()
        assert len(sleep_calls) == 1
        assert sleep_calls[0] > 0
