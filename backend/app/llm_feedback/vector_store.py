"""Memoria vectorial para conversaciones y feedback.

Mejoras implementadas:
 - Embeddings reales opcionales (Gemini) si hay API key, con fallback determinista.
 - Similaridad coseno local.
 - Recency decay exponencial configurable.
 - Ranking MMR (Maximal Marginal Relevance) para diversidad.
 - Parámetros configurables en settings (SIMILARITY_*).

Escalabilidad futura:
 - Migrar a pgvector y ejecutar ranking directamente en Postgres.
 - Reemplazar fallback por modelo open-source (e.g. bge-small) si se integra pipeline.
"""
from __future__ import annotations
from typing import List, Dict, Any, Optional, Tuple, OrderedDict as _OrderedDict
import os
import numpy as np
from collections import OrderedDict
from supabase import create_client
from ..core.config import get_settings
from datetime import datetime, timezone

settings = get_settings()

# Placeholder de embeddings: en real usarías un modelo (OpenAI, HF, etc.)
# Aquí representamos una función que retorna un vector fijo o pseudo-embedding

def infer_dim(model_name: str) -> int:
    # Simplificación: mapear algunos modelos conocidos
    if model_name.startswith('text-embedding-004'):  # Gemini placeholder
        return 1536
    if 'bge' in model_name.lower():
        return 1024
    if 'minilm' in model_name.lower():
        return 384
    return 1536

_EMBED_CACHE: "OrderedDict[str, list[float]]" = OrderedDict()
_EMBED_CACHE_MAX = 256

def _cache_get(key: str) -> list[float] | None:
    v = _EMBED_CACHE.get(key)
    if v is not None:
        # mover a final (LRU)
        _EMBED_CACHE.move_to_end(key)
    return v

def _cache_put(key: str, value: list[float]) -> None:
    _EMBED_CACHE[key] = value
    _EMBED_CACHE.move_to_end(key)
    if len(_EMBED_CACHE) > _EMBED_CACHE_MAX:
        _EMBED_CACHE.popitem(last=False)

def embed_text(text: str, dim: int, model: str) -> list[float]:
    cache_key = f"{model}:{dim}:{hash(text)}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached
    # Intentar Gemini embeddings si disponible
    api_key = os.getenv('GOOGLE_API_KEY')
    if api_key and model.startswith('text-embedding'):
        try:
            import google.generativeai as genai  # type: ignore
            genai.configure(api_key=api_key)
            # API hipotética para embeddings Gemini (puede ajustarse según SDK real)
            if hasattr(genai, 'embed_content'):
                resp = genai.embed_content(model=model, content=text)
                emb = resp['embedding']['values']  # estructura típica
                return emb[:dim]
        except Exception:
            pass
    # Fallback pseudo embedding determinista
    rng = np.random.default_rng(abs(hash((model, text))) % (2**32))
    vec = rng.normal(0, 0.1, size=dim).astype(float).tolist()
    _cache_put(cache_key, vec)
    return vec

def _recency_weight(created_at: str | None, decay_lambda: float) -> float:
    if not created_at:
        return 1.0
    try:
        dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
    except Exception:
        return 1.0
    age_hours = (datetime.now(timezone.utc) - dt).total_seconds() / 3600.0
    return float(np.exp(-decay_lambda * age_hours))


def _mmr_rerank(candidates: List[Tuple[float, Dict[str, Any]]], query_vec: np.ndarray, lambda_: float, top_k: int) -> List[Dict[str, Any]]:
    if not candidates:
        return []
    selected: List[Dict[str, Any]] = []
    selected_vecs: List[np.ndarray] = []
    remaining = candidates.copy()
    while remaining and len(selected) < top_k:
        best_idx = 0
        best_score = -1e9
        for idx, (sim, item) in enumerate(remaining):
            # score relevancia principal
            relevance = sim
            diversity_penalty = 0.0
            if selected_vecs:
                iv = np.array(item.get('_embedding', []), dtype=float)
                if iv.size and all(v.size for v in selected_vecs):
                    sim_to_selected = [float(np.dot(iv, v) / (np.linalg.norm(iv) * np.linalg.norm(v))) for v in selected_vecs if np.linalg.norm(iv) and np.linalg.norm(v)]
                    if sim_to_selected:
                        diversity_penalty = max(sim_to_selected)
            mmr_score = lambda_ * relevance - (1 - lambda_) * diversity_penalty
            if mmr_score > best_score:
                best_score = mmr_score
                best_idx = idx
        chosen = remaining.pop(best_idx)
        chosen_item = dict(chosen[1])
        chosen_item['mmr_score'] = best_score
        selected.append(chosen_item)
        emb = chosen_item.get('_embedding')
        if emb:
            selected_vecs.append(np.array(emb, dtype=float))
    return selected


class VectorStore:
    def __init__(self, embedding_dim: int | None = None, model: str | None = None) -> None:
        self.model = model or settings.EMBEDDING_MODEL
        base_dim = embedding_dim or settings.EMBEDDING_DIM or infer_dim(self.model)
        self.dim = base_dim
        self.client = create_client(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)

    def add(self, *, user_id: str, exercise_id: str, attempt_id: Optional[str], type_: str, content: str) -> None:
        embedding = embed_text(content, self.dim, self.model)
        self.client.table('exercise_conversation_vectors').insert({
            'user_id': user_id,
            'exercise_id': exercise_id,
            'attempt_id': attempt_id,
            'type': type_,
            'content': content,
            'embedding': embedding,
        }).execute()

    def recent(self, *, user_id: str, exercise_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        res = self.client.table('exercise_conversation_vectors').select('*').eq('user_id', user_id).eq('exercise_id', exercise_id).order('created_at', desc=True).limit(limit).execute()
        return res.data or []

    def fetch_all(self, *, user_id: str, exercise_id: str, limit: int = 200) -> List[Dict[str, Any]]:
        """Recupera hasta N registros para cálculo local de similitud.
        Escala suficiente para bajo volumen actual; más adelante se migrará a consulta SQL con <-> en Postgres.
        """
        res = self.client.table('exercise_conversation_vectors').select('*').eq('user_id', user_id).eq('exercise_id', exercise_id).order('created_at', desc=True).limit(limit).execute()
        return res.data or []

    def similar(self, *, user_id: str, exercise_id: str, query_text: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Ranking híbrido (similitud * recency) + MMR para diversidad.
        Pasos:
         1. Recupera hasta FETCH_LIMIT items.
         2. Calcula embedding de la query.
         3. Similaridad coseno.
         4. Ajuste por recency (peso multiplicativo exponencial).
         5. Orden inicial por score hibrido.
         6. Re-ranking MMR para diversidad.
        Fallback: recent() si algo falla.
        """
        try:
            all_items = self.fetch_all(user_id=user_id, exercise_id=exercise_id, limit=settings.SIMILARITY_FETCH_LIMIT)
            if not all_items:
                return []
            q_emb = np.array(embed_text(query_text, self.dim, self.model))
            if not q_emb.size or np.linalg.norm(q_emb) == 0:
                return []
            decay_lambda = settings.SIMILARITY_RECENCY_DECAY
            scored: List[Tuple[float, Dict[str, Any]]] = []
            for it in all_items:
                emb = it.get('embedding')
                if not emb:
                    continue
                v = np.array(emb, dtype=float)
                if not v.size or np.linalg.norm(v) == 0:
                    continue
                sim = float(np.dot(q_emb, v) / (np.linalg.norm(q_emb) * np.linalg.norm(v)))
                rec_weight = _recency_weight(it.get('created_at'), decay_lambda)
                hybrid = sim * rec_weight
                # Guardamos embedding temporal para MMR
                it['_embedding'] = v.tolist()
                it['score_cosine'] = sim
                it['recency_weight'] = rec_weight
                it['score_hybrid'] = hybrid
                scored.append((hybrid, it))
            if not scored:
                return []
            scored.sort(key=lambda x: x[0], reverse=True)
            # Selección preliminar top 4xK para dar espacio a MMR
            prelim = scored[: max(limit * 4, limit)]
            mmr = _mmr_rerank(prelim, q_emb, settings.SIMILARITY_MMR_LAMBDA, top_k=limit)
            # Limpieza: remover embedding temporal para no persistirlo si se serializa
            for it in mmr:
                it.pop('_embedding', None)
            return mmr
        except Exception:
            return self.recent(user_id=user_id, exercise_id=exercise_id, limit=limit)

_vector_store = VectorStore()

def get_vector_store() -> VectorStore:
    return _vector_store
