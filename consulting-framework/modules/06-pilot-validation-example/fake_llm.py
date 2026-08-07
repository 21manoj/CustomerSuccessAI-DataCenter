"""A fake LLM client for pilot-validation-06.

Deliberately mimics the shape the spec's Build Prompt assumes:

    response = llm_client.messages.create(model=model, ...prompt...)
    response.usage.input_tokens
    response.usage.output_tokens

No network, no API key, no real provider. Every behaviour the module needs to
degrade against is a mode you set explicitly:

    FakeLLMClient(mode="success", payload={...})   # well-formed JSON
    FakeLLMClient(mode="raise", exc=TimeoutError("upstream timeout"))
    FakeLLMClient(mode="malformed")                # non-JSON garbage
    FakeLLMClient(mode="partial", payload={...})   # valid JSON, missing keys

`calls` records every invocation so tests can assert call counts independently
of the usage table (the whole point of Gotcha 1 is that those two can diverge).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any


@dataclass
class FakeUsage:
    input_tokens: int
    output_tokens: int


@dataclass
class FakeContentBlock:
    text: str
    type: str = "text"


@dataclass
class FakeResponse:
    content: list
    usage: FakeUsage
    model: str

    @property
    def text(self) -> str:
        return "".join(b.text for b in self.content)


DEFAULT_PAYLOAD = {
    "sentiment": "negative",
    "relationship_sentiment": -0.4,
    "product_sentiment": -0.2,
    "urgency_score": 0.55,
    "intent_signals": ["renewal_risk"],
    "stakeholder_roles": {"jane@acme.test": "economic_buyer"},
    "suggested_action": "Schedule an exec sync within 5 business days.",
    "confidence": {"sentiment": 0.9, "urgency_score": 0.85},
}


class _Messages:
    def __init__(self, client: "FakeLLMClient"):
        self._client = client

    def create(self, model: str, **kwargs: Any) -> FakeResponse:
        return self._client._create(model=model, **kwargs)


class FakeLLMClient:
    """Controllable stand-in for an LLM SDK client."""

    def __init__(
        self,
        mode: str = "success",
        payload: dict | None = None,
        exc: BaseException | None = None,
        tokens_in: int = 1200,
        tokens_out: int = 300,
        raw_text: str | None = None,
    ):
        self.mode = mode
        self.payload = DEFAULT_PAYLOAD if payload is None else payload
        self.exc = exc or TimeoutError("simulated upstream timeout")
        self.tokens_in = tokens_in
        self.tokens_out = tokens_out
        self.raw_text = raw_text
        self.calls: list[dict] = []
        self.messages = _Messages(self)

    # -- control surface -------------------------------------------------
    def set_mode(self, mode: str, **kw: Any) -> None:
        self.mode = mode
        for k, v in kw.items():
            setattr(self, k, v)

    @property
    def call_count(self) -> int:
        return len(self.calls)

    # -- the "API" -------------------------------------------------------
    def _create(self, model: str, **kwargs: Any) -> FakeResponse:
        self.calls.append({"model": model, **kwargs})

        if self.mode == "raise":
            raise self.exc

        if self.mode == "malformed":
            body = self.raw_text if self.raw_text is not None else (
                "Sure! Here's my read on that ticket -- it feels pretty tense, "
                "but I'm not going to give you JSON today."
            )
        elif self.mode == "empty":
            body = ""
        else:  # success / partial -- both return whatever payload was set
            body = json.dumps(self.payload)

        return FakeResponse(
            content=[FakeContentBlock(text=body)],
            usage=FakeUsage(input_tokens=self.tokens_in, output_tokens=self.tokens_out),
            model=model,
        )


class ExplodingLLMClient(FakeLLMClient):
    """Raises on every call. Convenience for the degradation matrix."""

    def __init__(self, exc: BaseException | None = None, **kw: Any):
        super().__init__(mode="raise", exc=exc, **kw)
