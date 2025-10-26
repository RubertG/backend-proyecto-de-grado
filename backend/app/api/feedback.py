from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List
from ..validators.command import validate_command
from ..validators.dockerfile import validate_dockerfile
from ..validators.compose import validate_compose
from ..core.security import get_current_user, AuthUser
from ..db.database import get_db, Database
from ..llm_feedback.feedback_chain import get_feedback_service, FeedbackService

router = APIRouter(prefix="/feedback", tags=["feedback"])

class FeedbackAttemptIn(BaseModel):
    exercise_id: str
    submitted_answer: str = Field(min_length=1)

class FeedbackAttemptOut(BaseModel):
    attempt_id: str
    content_md: str
    metrics: dict

@router.post('/attempt', response_model=FeedbackAttemptOut, summary="Generar feedback (valida estructura antes de invocar LLM si aplica)")
async def create_attempt_feedback(payload: FeedbackAttemptIn, db: Database = Depends(get_db), current_user: AuthUser = Depends(get_current_user)):
    """Genera feedback utilizando el LLM solo si la validación estructural (cuando está habilitada) pasa.

    Flujo:
    1. Verificar ejercicio y flags.
    2. Si enable_structural_validation y tipo es command/dockerfile => validar.
       - Si falla => 422 con detalle y sin invocar LLM.
    3. Invocar servicio LLM para generar feedback y registrar intento.
    """
    service: FeedbackService = await get_feedback_service(db)
    exercise = await db.get_exercise(payload.exercise_id)
    if not exercise:
        raise HTTPException(status_code=404, detail="Ejercicio no encontrado")
    if not exercise.get('enable_llm_feedback'):
        raise HTTPException(status_code=400, detail="Feedback LLM deshabilitado para este ejercicio")

    ex_type = exercise.get('type')
    # Validación estructural previa si está habilitada
    if exercise.get('enable_structural_validation') and ex_type in ("command", "dockerfile", "compose"):
        answer = payload.submitted_answer or ""
        if ex_type == "command":
            cmd_res = validate_command(answer)
            if not cmd_res.is_valid:
                # No llamamos al LLM
                raise HTTPException(status_code=422, detail={
                    "message": "Validación estructural falló (command)",
                    "errors": cmd_res.errors,
                    "structure_valid": False
                })
        elif ex_type == "dockerfile":
            df_res = validate_dockerfile(answer)
            if not df_res.is_valid:
                raise HTTPException(status_code=422, detail={
                    "message": "Validación estructural falló (dockerfile)",
                    "errors": df_res.errors,
                    "warnings": df_res.warnings,
                    "structure_valid": False
                })
        elif ex_type == "compose":
            comp_res = validate_compose(answer)
            if not comp_res.is_valid:
                raise HTTPException(status_code=422, detail={
                    "message": "Validación estructural falló (compose)",
                    "errors": comp_res.errors,
                    "warnings": comp_res.warnings,
                    "structure_valid": False
                })

    result = await service.generate_feedback(user_id=current_user.id, exercise_id=payload.exercise_id, submitted_answer=payload.submitted_answer)
    return FeedbackAttemptOut(**result)

class ChatIn(BaseModel):
    exercise_id: str
    message: str = Field(min_length=1)

class ChatOut(BaseModel):
    content_md: str
    metrics: dict

@router.post('/chat', response_model=ChatOut)
async def chat(payload: ChatIn, db: Database = Depends(get_db), current_user: AuthUser = Depends(get_current_user)):
    service: FeedbackService = await get_feedback_service(db)
    exercise = await db.get_exercise(payload.exercise_id)
    if not exercise:
        raise HTTPException(status_code=404, detail="Ejercicio no encontrado")
    if not exercise.get('enable_llm_feedback'):
        raise HTTPException(status_code=400, detail="Feedback LLM deshabilitado para este ejercicio")
    result = await service.chat(user_id=current_user.id, exercise_id=payload.exercise_id, message=payload.message)
    return ChatOut(**result)

class HistoryItem(BaseModel):
    type: str
    content_md: str
    created_at: str | None = None

@router.get('/history', response_model=List[HistoryItem])
async def history(exercise_id: str, db: Database = Depends(get_db), current_user: AuthUser = Depends(get_current_user)):
    # Reutiliza vector store tabla para reconstruir historial (orden ascendente)
    service: FeedbackService = await get_feedback_service(db)
    vs = service.vs
    raw = vs.recent(user_id=current_user.id, exercise_id=exercise_id, limit=200)
    # vienen ordenados desc -> invertimos
    ordered = list(reversed(raw))
    items = []
    for r in ordered:
        items.append(HistoryItem(type=r.get('type',''), content_md=r.get('content',''), created_at=r.get('created_at')))
    return items
