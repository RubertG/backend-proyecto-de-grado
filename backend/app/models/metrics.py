from pydantic import BaseModel
from typing import Any, Optional


class LLMMetricBase(BaseModel):
    user_id: str
    exercise_id: str
    attempt_id: str | None = None
    model: str | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    latency_ms: float | None = None
    quality_flags: dict[str, Any] | None = None
    created_at: str | None = None  # ISO timestamp


class LLMMetricOverviewItem(LLMMetricBase):
    id: str
    # Enriquecido
    user: dict[str, Any]
    exercise: dict[str, Any]


class LLMMetricOverviewResponse(BaseModel):
    items: list[LLMMetricOverviewItem]
    count: int
