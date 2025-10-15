from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from uuid import UUID
from ..models.exercise import ExerciseCreate, ExerciseOut, ExerciseUpdate
from ..db.database import get_db, Database
from ..core.security import require_role
import uuid

router = APIRouter(prefix="/exercises", tags=["exercises"])

@router.post('/', response_model=ExerciseOut, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_role('admin'))], summary="Crear ejercicio (incluye flags de validación/LLM)")
async def create_exercise(payload: ExerciseCreate, db: Database = Depends(get_db)):
    data = payload.model_dump()
    data['id'] = str(uuid.uuid4())
    created = await db.create_exercise(data)
    return ExerciseOut(**created)

@router.get('/by-guide/{guide_id}', response_model=List[ExerciseOut])
async def list_exercises_by_guide(guide_id: str, db: Database = Depends(get_db)):
    exercises = await db.list_exercises_by_guide(guide_id)
    return [ExerciseOut(**e) for e in exercises]

@router.get('/all', response_model=List[ExerciseOut], dependencies=[Depends(require_role('admin'))], summary="Listar todos los ejercicios (admin, incluye inactivos)")
async def list_all_exercises(db: Database = Depends(get_db), only_active: bool = False):
    exercises = await db.list_all_exercises(include_inactive=not only_active)
    return [ExerciseOut(**e) for e in exercises]

@router.get('/{exercise_id}', response_model=ExerciseOut)
async def get_exercise(exercise_id: UUID, db: Database = Depends(get_db)):
    exercise = await db.get_exercise(str(exercise_id))
    if not exercise:
        raise HTTPException(status_code=404, detail="Ejercicio no encontrado")
    return ExerciseOut(**exercise)

@router.patch('/{exercise_id}', response_model=ExerciseOut, dependencies=[Depends(require_role('admin'))], summary="Actualizar ejercicio (permite cambiar flags)")
async def update_exercise(exercise_id: UUID, payload: ExerciseUpdate, db: Database = Depends(get_db)):
    existing = await db.get_exercise(str(exercise_id))
    if not existing:
        raise HTTPException(status_code=404, detail="Ejercicio no encontrado")
    update_data = {k: v for k, v in payload.model_dump(exclude_unset=True).items()}
    updated = await db.update_exercise(str(exercise_id), update_data)
    return ExerciseOut(**updated)

@router.delete('/{exercise_id}', status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_role('admin'))])
async def delete_exercise(exercise_id: UUID, db: Database = Depends(get_db)):
    existing = await db.get_exercise(str(exercise_id))
    if not existing:
        raise HTTPException(status_code=404, detail="Ejercicio no encontrado")
    await db.delete_exercise(str(exercise_id))
    return None
