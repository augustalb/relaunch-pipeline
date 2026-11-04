"""LLM access. Real: Anthropic Messages API with structured outputs. Without a key the
generation stage falls back to the deterministic composer in `pipeline.stages.generation`.
"""

from __future__ import annotations

import json
from typing import Protocol

from ..config import get_settings
from ..costs import BudgetExceeded, CostTracker
from ..log import get_logger

log = get_logger("llm")


class LLM(Protocol):
    name: str

    def complete_json(self, system: str, user: str, schema: dict) -> dict: ...


class AnthropicLLM:
    name = "anthropic"

    def __init__(self, api_key: str, model: str, costs: CostTracker):
        import anthropic

        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model
        self.costs = costs

    def complete_json(self, system: str, user: str, schema: dict) -> dict:
        import anthropic

        s = get_settings()
        self.costs.check_eur("llm", s.LLM_MAX_COST_PER_RUN_EUR)
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=s.LLM_MAX_TOKENS,
                system=[{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
                messages=[{"role": "user", "content": user}],
                output_config={"effort": "low", "format": {"type": "json_schema", "schema": schema}},
            )
        except anthropic.RateLimitError:
            raise
        except anthropic.APIStatusError as e:
            log.error("anthropic api error", status=e.status_code, msg=str(e)[:300])
            raise
        usage = response.usage
        eur = (usage.input_tokens / 1e6) * s.COST_LLM_INPUT_PER_MTOK_EUR + (usage.output_tokens / 1e6) * s.COST_LLM_OUTPUT_PER_MTOK_EUR
        self.costs.record("llm", eur, units=usage.input_tokens + usage.output_tokens, note=self.model)
        if response.stop_reason == "refusal":
            raise RuntimeError("LLM refused the request")
        text = next((b.text for b in response.content if getattr(b, "type", "") == "text"), "")
        return json.loads(text)


def make_llm(costs: CostTracker) -> LLM | None:
    s = get_settings()
    if not s.ANTHROPIC_API_KEY:
        return None
    return AnthropicLLM(s.ANTHROPIC_API_KEY, s.LLM_MODEL, costs)


__all__ = ["LLM", "AnthropicLLM", "make_llm", "BudgetExceeded"]
