"""Cadena principal para generar feedback de un intento usando LLM.

Diseñada para ser intercambiable de modelo (Gemini por defecto)."""
from __future__ import annotations
from typing import Optional, Dict, Any, Sequence
import time
import os

from ..db.database import Database
from ..core.config import get_settings
from .prompt_builder import build_feedback_prompt, MAX_PROMPT_CHARS
from .postprocess import normalize_output, basic_quality_flags, sanitize_references
from .metrics import get_metrics_collector, approximate_token_count
from .vector_store import get_vector_store
from langchain_google_genai import ChatGoogleGenerativeAI  # type: ignore
import logging
import warnings

logger = logging.getLogger("llm")

settings = get_settings()

# Abstracción mínima de cliente LLM. Se puede extender.
class LangChainLLMWrapper:
    def __init__(self, model: str, temperature: float) -> None:
        api_key = settings.GOOGLE_API_KEY
        if not api_key:
            self._chain = None
            self.model = model
            self.temperature = temperature
            logger.warning("LLM en modo STUB: no se encontró GOOGLE_API_KEY al inicializar. Modelo=%s", model)
            self._lazy_attempts = 0
            self._last_lazy_error: str | None = None
            self._last_lazy_time: float | None = None
        else:
            # Pasamos api_key explícita para evitar que busque Application Default Credentials
            # Intentamos sin el parámetro deprecado para evitar el warning.
            try:
                self._chain = ChatGoogleGenerativeAI(
                    model=model,
                    temperature=temperature,
                    api_key=api_key,
                )
                logger.info("LLM inicializado correctamente con modelo=%s temperatura=%.2f (sin convert_system_message_to_human)", model, temperature)
            except TypeError:
                # Compatibilidad con versiones más antiguas que aún requieran el flag
                warnings.filterwarnings("ignore", message="Convert_system_message_to_human will be deprecated!"
                )
                try:
                    self._chain = ChatGoogleGenerativeAI(
                        model=model,
                        temperature=temperature,
                        convert_system_message_to_human=True,
                        api_key=api_key,
                    )
                    logger.info("LLM inicializado correctamente con modelo=%s usando flag legacy convert_system_message_to_human", model)
                except Exception as e:
                    logger.exception("Fallo inicializando LLM (legacy intento), entrando a modo STUB. Modelo=%s Error=%s", model, e)
                    self._chain = None
            except Exception as e:
                logger.exception("Fallo inicializando LLM, entrando a modo STUB. Modelo=%s Error=%s", model, e)
                self._chain = None
            self.model = model
            self.temperature = temperature
            self._lazy_attempts = 0
            self._last_lazy_error = None
            self._last_lazy_time = None

    def _try_lazy_init(self) -> None:
        """Intento perezoso de inicializar el modelo si anteriormente estaba en stub.
        Throttle: no más de un intento cada 60s si falla.
        """
        if self._chain is not None:
            return
        now = time.time()
        if self._last_lazy_time and (now - self._last_lazy_time) < 60:
            return
        self._last_lazy_time = now
        new_settings = get_settings()
        api_key = new_settings.GOOGLE_API_KEY
        if not api_key:
            return
        try:
            self._chain = ChatGoogleGenerativeAI(
                model=self.model,
                temperature=self.temperature,
                api_key=api_key,
            )
            self._lazy_attempts += 1
            logger.info("Lazy init LLM exitosa. Modelo=%s intentos_previos=%d", self.model, self._lazy_attempts)
            self._last_lazy_error = None
        except Exception as e:
            self._lazy_attempts += 1
            self._last_lazy_error = str(e)
            logger.warning("Lazy init LLM falló: %s", e)

    def generate(self, prompt: str) -> str:
        if not self._chain:
            # Intento lazy antes de rendirme
            self._try_lazy_init()
            if not self._chain:
                logger.error("Invocación LLM en modo STUB. Devuelvo respuesta placeholder. Modelo=%s", self.model)
                return ("Retroalimentación (modo stub sin modelo):\n"
                    "- No se evaluó ejecución real.\n"
                    "- Aporta más detalle si buscas análisis profundo.\n"
                    "- (Fin del feedback)")
        
        try:
            resp = self._chain.invoke(prompt)
            if hasattr(resp, 'content'):
                return resp.content  # type: ignore[attr-defined]
            return str(resp)
        except Exception as e:
            logger.exception("Error ejecutando LLM model=%s: %s", self.model, e)
            return ("Respuesta no disponible por error interno: {error}. Intenta nuevamente y aporta contexto puntual si puedes.").format(error=e)

_llm_wrapper = LangChainLLMWrapper(settings.LLM_MODEL, settings.LLM_TEMPERATURE)

def get_llm_client() -> LangChainLLMWrapper:
    return _llm_wrapper

class FeedbackService:
    def __init__(self, db: Database, llm_client: LangChainLLMWrapper | None = None) -> None:
        self.db = db
        self.llm = llm_client or get_llm_client()
        self.vs = get_vector_store()

    async def generate_feedback(self, *, user_id: str, exercise_id: str, submitted_answer: str) -> Dict[str, Any]:
        exercise = await self.db.get_exercise(exercise_id)
        if not exercise:
            raise ValueError("Ejercicio no encontrado")
        guide = await self.db.get_guide(exercise.get('guide_id')) if exercise.get('guide_id') else None
        past_attempts = await self.db.list_attempts(exercise_id, user_id=user_id)
        previous_feedback = await self.db.get_last_feedback(exercise_id, user_id)
        recent_dialog = self.vs.recent(user_id=user_id, exercise_id=exercise_id, limit=20)

        # (Lógica de reutilización eliminada a petición del usuario)

        prompt = build_feedback_prompt(
            guide=guide,
            exercise=exercise,
            attempts=past_attempts,
            previous_feedback=previous_feedback,
            previous_dialog=recent_dialog,
            user_answer=submitted_answer,
        )

        # Similaridad (enriquecer)
        if settings.SIMILARITY_ENABLED:
            try:
                similar_items = []
                if hasattr(self.vs, 'similar'):
                    similar_items = self.vs.similar(
                        user_id=user_id,
                        exercise_id=exercise_id,
                        query_text=submitted_answer or (exercise.get('title') or ''),
                        limit=settings.SIMILARITY_TOP_K,
                    )
                if similar_items:
                    lines = []
                    for it in similar_items:
                        c = it.get('content') or it.get('submitted_answer') or ''
                        if not c:
                            continue
                        s = it.get('score_hybrid') or it.get('score') or it.get('score_cosine')
                        if isinstance(s, (int, float)):
                            s_txt = f"{s:.2f}"
                        else:
                            s_txt = '?'
                        lines.append(f"[Relacionado score={s_txt}] {c[:300]}")
                    block = "\n".join(lines)
                    augmented = prompt + "\n\n--- CONTEXTO RELACIONADO (similaridad) ---\n" + block + "\n--- FIN CONTEXTO RELACIONADO ---\n"
                    if len(augmented) <= int(MAX_PROMPT_CHARS * 1.18):
                        prompt = augmented
            except Exception as e:
                logger.warning(f"Fallo al enriquecer con similitud: {e}")

        start = time.time()
        raw = self.llm.generate(prompt)
        processed = normalize_output(raw)
        # Saneamos por precaución, pero no registramos flag específico
        processed, _ = sanitize_references(processed)
        quality = basic_quality_flags(processed)
        # Añadimos flags enriquecidos
        quality['similarity_used'] = '--- CONTEXTO RELACIONADO (similaridad) ---' in prompt
        quality['truncated'] = len(prompt) > MAX_PROMPT_CHARS
        quality['stub_mode'] = self.llm._chain is None
        quality['specialization_applied'] = 'Contexto pedagógico específico:' in prompt
        # Conteo aproximado de tokens (palabras + signos)
        prompt_tokens = approximate_token_count(prompt)
        completion_tokens = approximate_token_count(processed)
        metrics = get_metrics_collector().record(
            model=self.llm.model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            start_time=start,
            quality_flags=quality,
            output_text=processed,
        )

        # Almacenar intento y feedback
        attempt_data = {
            'id': __import__('uuid').uuid4().hex,
            'exercise_id': exercise_id,
            'user_id': user_id,
            'submitted_answer': submitted_answer,
            'structural_validation_passed': None,
            'llm_feedback': processed,
            'completed': False,
        }
        created = await self.db.create_attempt(attempt_data)

        # Guardar en memoria vectorial
        self.vs.add(user_id=user_id, exercise_id=exercise_id, attempt_id=created['id'], type_='attempt', content=submitted_answer)
        self.vs.add(user_id=user_id, exercise_id=exercise_id, attempt_id=created['id'], type_='feedback', content=processed)

        # Persist metrics
        try:
            await self.db.create_llm_metric({
                'user_id': user_id,
                'exercise_id': exercise_id,
                'attempt_id': created['id'],
                'model': self.llm.model,
                'prompt_tokens': prompt_tokens,
                'completion_tokens': completion_tokens,
                'latency_ms': metrics.latency_ms,
                'quality_flags': quality,
            })
        except Exception:
            pass

        return {
            'attempt_id': created['id'],
            'content_md': processed,
            'metrics': metrics.to_dict(),
        }

    async def chat(self, *, user_id: str, exercise_id: str, message: str) -> Dict[str, Any]:
        exercise = await self.db.get_exercise(exercise_id)
        if not exercise:
            raise ValueError("Ejercicio no encontrado")
        recent_dialog = self.vs.recent(user_id=user_id, exercise_id=exercise_id, limit=30)
        history_concat = "\n".join(f"[{d['type']}] {d['content'][:300]}" for d in reversed(recent_dialog[-12:]))
        guide = await self.db.get_guide(exercise.get('guide_id')) if exercise.get('guide_id') else None
        guide_title = guide.get('title') if guide else '(Sin guía)'
        guide_topic = guide.get('topic') if guide else '(Sin tema)'
        # Prompt con control de tema: si la pregunta se desvía totalmente, debe redirigir.
        prompt = (
            "Eres un asistente educativo en español. Mantente ENFOCADO estrictamente en la temática de la guía y el ejercicio.\n"
            f"Guía: {guide_title} | Tema: {guide_topic} | Ejercicio: {exercise.get('title')} (tipo={exercise.get('type')})\n"
            "Si el usuario pregunta algo totalmente ajeno (ej. chistes, política, clima, temas personales, tecnología no relacionada), NO respondas el contenido ajeno: responde educadamente que seguirán enfocados en la guía y su temática.\n"
            "Historial (resumido, últimos turnos inversos):\n"
            f"{history_concat}\n\n"
            f"Mensaje del usuario: {message}\n"
            "Instrucciones de respuesta:\n"
            "- Máx ~8 líneas.\n"
            "- Si es on-topic, profundiza con precisión y ejemplos cortos.\n"
            "- Si es off-topic, responde SOLO una breve redirección (sin contenido ajeno).\n"
            "- No inventes datos ni enlaces.\n"
            "- Formato Markdown claro (puedes usar listas concisas)."
        )
        # Similaridad para chat
        if settings.SIMILARITY_ENABLED:
            try:
                similar_items = []
                if hasattr(self.vs, 'similar'):
                    similar_items = self.vs.similar(
                        user_id=user_id,
                        exercise_id=exercise_id,
                        query_text=message,
                        limit=max(1, settings.SIMILARITY_TOP_K - 1),
                    )
                if similar_items:
                    lines = []
                    for it in similar_items:
                        c = it.get('content') or ''
                        if not c:
                            continue
                        lines.append(c[:250])
                    block = "\n".join(lines)
                    augmented = prompt + "\n\nContextoRelacionado:\n" + block
                    if len(augmented) < int(MAX_PROMPT_CHARS * 0.5):
                        prompt = augmented
            except Exception as e:
                logger.warning(f"Fallo similitud en chat: {e}")
        start = time.time()
        raw = self.llm.generate(prompt)
        processed = normalize_output(raw)
        processed, _ = sanitize_references(processed)
        prompt_tokens = approximate_token_count(prompt)
        completion_tokens = approximate_token_count(processed)
        quality_flags_chat: dict[str, bool] = {
            'similarity_used': 'ContextoRelacionado:' in prompt,
            'stub_mode': self.llm._chain is None,
            'truncated': len(prompt) > MAX_PROMPT_CHARS * 0.5,  # para chat usamos menor budget
        }
        metrics = get_metrics_collector().record(model=self.llm.model, prompt_tokens=prompt_tokens, completion_tokens=completion_tokens, start_time=start, quality_flags=quality_flags_chat, output_text=processed)
        try:
            await self.db.create_llm_metric({
                'user_id': user_id,
                'exercise_id': exercise_id,
                'attempt_id': None,
                'model': self.llm.model,
                'prompt_tokens': prompt_tokens,
                'completion_tokens': completion_tokens,
                'latency_ms': metrics.latency_ms,
                'quality_flags': {},
            })
        except Exception:
            pass
        # Persistir en vector store
        self.vs.add(user_id=user_id, exercise_id=exercise_id, attempt_id=None, type_='question', content=message)
        self.vs.add(user_id=user_id, exercise_id=exercise_id, attempt_id=None, type_='answer', content=processed)
        return {'content_md': processed, 'metrics': metrics.to_dict()}

_feedback_service_singleton: FeedbackService | None = None

async def get_feedback_service(db: Database) -> FeedbackService:
    global _feedback_service_singleton
    if _feedback_service_singleton is None:
        _feedback_service_singleton = FeedbackService(db)
    return _feedback_service_singleton
