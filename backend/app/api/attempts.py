from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from ..models.attempt import AttemptCreate, AttemptOut, AttemptUser
from ..db.database import get_db, Database
from ..core.security import get_current_user, AuthUser
from ..validators.dockerfile import validate_dockerfile
from ..validators.command import validate_command, validate_conceptual
from ..validators.compose import validate_compose
import uuid

router = APIRouter(prefix="/attempts", tags=["attempts"])

@router.post('/', response_model=AttemptOut, status_code=status.HTTP_201_CREATED, summary="Crear intento de ejercicio (valida estructura y determina completion automáticamente)")
async def create_attempt(payload: AttemptCreate, db: Database = Depends(get_db), current_user: AuthUser = Depends(get_current_user)):
    # Validar que el ejercicio exista
    exercise = await db.get_exercise(payload.exercise_id)
    if not exercise:
        raise HTTPException(status_code=404, detail="Ejercicio no encontrado")

    structural_passed = None
    structural_errors: list[str] | None = None
    structural_warnings: list[str] | None = None
    if exercise.get('enable_structural_validation'):
        ex_type = exercise.get('type')
        answer = payload.submitted_answer or ""
        if ex_type == 'dockerfile':
            result = validate_dockerfile(answer)
            structural_passed = result.is_valid
            structural_errors = result.errors if result.errors else []
            structural_warnings = result.warnings if getattr(result, 'warnings', None) else []
        elif ex_type == 'command':
            result = validate_command(answer)
            structural_passed = result.is_valid
            structural_errors = [] if result.is_valid else result.errors
            structural_warnings = []
        elif ex_type == 'compose':
            result = validate_compose(answer)
            structural_passed = result.is_valid
            structural_errors = result.errors if result.errors else []
            structural_warnings = result.warnings if result.warnings else []
        elif ex_type == 'conceptual':
            structural_passed = validate_conceptual(answer)
            structural_errors = [] if structural_passed else ["Error inesperado en conceptual"]
            structural_warnings = []

    # Reglas para 'completed':
    # - command/dockerfile: sólo si la validación estructural pasó (True)
    # - conceptual: se marca completo al enviar
    # - otros tipos: se deja False (extensible futuro)
    ex_type = exercise.get('type')
    completed_flag = False
    if ex_type in ('command', 'dockerfile', 'compose'):
        completed_flag = bool(structural_passed)  # True sólo si pasó validación
    elif ex_type == 'conceptual':
        completed_flag = True

    data = payload.model_dump(exclude={'completed'})  # ignoramos 'completed' del payload si llega
    data['id'] = str(uuid.uuid4())
    data['user_id'] = current_user.id
    data['completed'] = completed_flag
    if structural_passed is not None:
        data['structural_validation_passed'] = structural_passed
    created = await db.create_attempt(data)

    # Auto-marcado de guía completa si todos los ejercicios de la guía están completados por el usuario
    guide_id = exercise.get('guide_id')
    if guide_id:
        try:
            await db.ensure_guide_completed(user_id=current_user.id, guide_id=guide_id)
        except Exception:
            pass  # no romper el flujo principal
    # Inyectamos errores (no persistidos) en la respuesta
    attempt_out = AttemptOut(
        **created,
        user=AttemptUser(
            id=current_user.id,
            name=current_user.name,
            email=current_user.email,
            role=current_user.role,
        ),
        structural_validation_errors=structural_errors if structural_errors is not None else [],
        structural_validation_warnings=structural_warnings if structural_warnings is not None else [],
    )
    return attempt_out

@router.get('/by-exercise/{exercise_id}', response_model=List[AttemptOut], summary="Listar intentos de un ejercicio del usuario actual")
async def list_my_attempts_for_exercise(exercise_id: str, db: Database = Depends(get_db), current_user: AuthUser = Depends(get_current_user)):
    attempts = await db.list_attempts(exercise_id, user_id=current_user.id)
    user_obj = AttemptUser(
        id=current_user.id,
        name=current_user.name,
        email=current_user.email,
        role=current_user.role,
    )
    out: list[AttemptOut] = []
    for a in attempts:
        out.append(AttemptOut(
            **a,
            user=user_obj,
            structural_validation_errors=a.get('structural_validation_errors') or [],
            structural_validation_warnings=a.get('structural_validation_warnings') or [],
        ))
    return out
