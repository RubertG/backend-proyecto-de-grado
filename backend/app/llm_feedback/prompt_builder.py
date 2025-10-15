"""Construcción de prompts educativos para feedback LLM.

Responsabilidad:
- Ensamblar prompt estructurado según arquitectura.
- Mantener formato Markdown esperado en salida.
"""
from __future__ import annotations
from typing import Sequence, Any

MAX_PROMPT_CHARS = 6000  # Presupuesto aproximado (ajustable)

SPECIALIZATION_SNIPPETS = {
    'command': (
        "Enfatiza precisión del comando, flags seguros, alternativas y buenas prácticas de shell. "
        "Si el comando es correcto pero puede optimizarse, indícalo."
    ),
    'dockerfile': (
        "Evalúa capas, caché, tamaño de imagen, seguridad (no root si aplica), versionado de base, uso de COPY vs ADD, multi-stage si procede."
    ),
    'conceptual': (
        "Prioriza claridad conceptual, ejemplos cortos, analogías y corrección terminológica. "
        "Detecta malentendidos comunes y corrígelos suavemente."
    ),
}

PROMPT_TEMPLATE = """Eres un asistente educativo experto en tecnología.
Responde SIEMPRE en español neutro claro con un tono motivador, preciso y pedagógico.

Contexto pedagógico específico:
{specialization}

[Contexto de Guía]
Título: {guide_title}
Tema: {guide_topic}

[Contexto de Ejercicio]
Título: {exercise_title}
Tipo: {exercise_type}
Dificultad: {exercise_difficulty}
Descripción:
{exercise_content}

Respuesta esperada (no la repitas textualmente salvo fragmentos mínimos necesarios):
{expected_answer}

[Historial relevante]
Intentos previos del usuario (resumidos):
{attempt_summaries}
Feedback previo (si existe):
{previous_feedback}
Preguntas previas del usuario:
{previous_questions}
Respuestas previas del asistente:
{previous_answers}

[Respuesta actual del usuario]
{user_answer}

Produce feedback ÚTIL en Markdown. Usa solo encabezados con contenido real, por ejemplo:
## Fortalezas
## Errores
## Consejos de mejora

Lineamientos:
- NO inventes secciones vacías.
- Si casi todo está correcto, resalta brevemente lo positivo y ofrece 1–3 mejoras.
- NO hagas preguntas de seguimiento; finaliza con una frase motivadora breve opcional.
- No repitas íntegramente la respuesta esperada.
- No incluyas enlaces, referencias externas ni citas.
- Prioriza brevedad con claridad: normalmente 5–12 líneas.
""".strip()

def _truncate(text: str, budget: int) -> str:
    if len(text) <= budget:
        return text
    # Cortar en límite y añadir marcador
    return text[: budget - 60] + "\n...[TRUNCADO]" if budget > 60 else text[:budget]


def build_feedback_prompt(*, guide: dict[str, Any] | None, exercise: dict[str, Any], attempts: Sequence[dict[str, Any]], previous_feedback: str | None, previous_dialog: Sequence[dict[str, str]], user_answer: str) -> str:
    guide_title = guide.get("title") if guide else "(Sin guía)"
    guide_topic = guide.get("topic") if guide else "(Sin tema)"
    attempt_summaries = "\n".join(f"- {a.get('submitted_answer','')[:120]}" for a in attempts[-5:]) or "(Sin intentos previos)"
    prev_feedback = previous_feedback or "(Sin feedback previo)"
    user_questions = [d["content"] for d in previous_dialog if d.get("type") == "question"]
    assistant_answers = [d["content"] for d in previous_dialog if d.get("type") == "answer"]
    pq = "\n".join(f"- {q[:120]}" for q in user_questions[-5:]) or "(Sin preguntas)"
    pa = "\n".join(f"- {r[:120]}" for r in assistant_answers[-5:]) or "(Sin respuestas)"

    exercise_type = exercise.get("type")
    specialization = SPECIALIZATION_SNIPPETS.get(exercise_type, "Enfatiza exactitud, claridad y utilidad pedagógica.")

    base_prompt = PROMPT_TEMPLATE.format(
        specialization=specialization,
        guide_title=guide_title,
        guide_topic=guide_topic,
        exercise_title=exercise.get("title"),
        exercise_type=exercise_type,
        exercise_difficulty=exercise.get("difficulty"),
        exercise_content=exercise.get("content_html") or exercise.get("ai_context") or "(Sin descripción)",
        expected_answer=exercise.get("expected_answer") or "(No definida)",
        attempt_summaries=attempt_summaries,
        previous_feedback=prev_feedback,
        previous_questions=pq,
        previous_answers=pa,
        user_answer=user_answer or "(Vacío)"
    )

    if len(base_prompt) <= MAX_PROMPT_CHARS:
        return base_prompt

    # Estrategia de truncado progresivo
    # 1. Reducir historial de preguntas/respuestas
    reduced_pq = _truncate(pq, 400)
    reduced_pa = _truncate(pa, 400)
    reduced_attempts = _truncate(attempt_summaries, 600)
    reduced_prev_feedback = _truncate(prev_feedback, 800)
    reduced_content = _truncate(exercise.get("content_html") or exercise.get("ai_context") or "(Sin descripción)", 1200)

    truncated_prompt = PROMPT_TEMPLATE.format(
        specialization=specialization,
        guide_title=guide_title,
        guide_topic=guide_topic,
        exercise_title=exercise.get("title"),
        exercise_type=exercise_type,
        exercise_difficulty=exercise.get("difficulty"),
        exercise_content=reduced_content,
        expected_answer=exercise.get("expected_answer") or "(No definida)",
        attempt_summaries=reduced_attempts,
        previous_feedback=reduced_prev_feedback,
        previous_questions=reduced_pq,
        previous_answers=reduced_pa,
        user_answer=(user_answer or "(Vacío)")[:800]
    )
    if len(truncated_prompt) > MAX_PROMPT_CHARS:
        truncated_prompt = truncated_prompt[: MAX_PROMPT_CHARS - 80] + "\n...[TRUNCADO FINAL]"
    return truncated_prompt
