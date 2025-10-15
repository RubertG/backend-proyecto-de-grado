"""Registro y métricas del módulo de feedback.

En entorno real podrías enviar a un sistema externo (OpenTelemetry, Prometheus, etc.).
Aquí dejamos hooks ligeros.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any
import time
import re

TOKEN_REGEX = re.compile(r"\w+|[^\s\w]")

def approximate_token_count(text: str) -> int:
        """Conteo simple de tokens aproximados.
        Estrategia:
            - Divide en palabras y signos separados.
            - Aprox razonable para modelos subword (mejor que chars/4 genérico).
        """
        if not text:
                return 0
        return len(TOKEN_REGEX.findall(text))

@dataclass(slots=True)
class LLMCallMetrics:
    model: str
    prompt_tokens: Optional[int]
    completion_tokens: Optional[int]
    latency_ms: float
    quality_flags: Dict[str, bool]
    density_chars_per_token: float | None = None
    lexical_diversity: float | None = None
    avg_sentence_length: float | None = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

class MetricsCollector:
    def __init__(self) -> None:
        self._events: list[Dict[str, Any]] = []

    def record(self, *, model: str, prompt_tokens: int | None, completion_tokens: int | None, start_time: float, quality_flags: Dict[str, bool], output_text: str | None = None) -> LLMCallMetrics:
        latency_ms = (time.time() - start_time) * 1000
        density = None
        lexical = None
        avg_sent = None
        if output_text:
            try:
                tokens = approximate_token_count(output_text)
                density = (len(output_text) / tokens) if tokens else None
                words = [w.lower() for w in TOKEN_REGEX.findall(output_text) if w.isalpha()]
                if words:
                    unique = len(set(words))
                    lexical = unique / len(words)
                # oración simple por separación en .!? (heurístico)
                sentences = [s.strip() for s in re.split(r'[.!?]+', output_text) if s.strip()]
                if sentences and words:
                    avg_sent = len(words) / len(sentences)
            except Exception:
                pass
        m = LLMCallMetrics(model=model, prompt_tokens=prompt_tokens, completion_tokens=completion_tokens, latency_ms=latency_ms, quality_flags=quality_flags, density_chars_per_token=density, lexical_diversity=lexical, avg_sentence_length=avg_sent)
        # asdict porque usamos slots y no hay __dict__ directo
        self._events.append(asdict(m))
        return m

    def dump(self) -> list[Dict[str, Any]]:
        return list(self._events)

_metrics = MetricsCollector()

def get_metrics_collector() -> MetricsCollector:
    return _metrics
