from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from ..models.guide import GuideCreate, GuideOut, GuideUpdate
from ..db.database import get_db, Database
from ..core.security import require_role
import uuid

router = APIRouter(prefix="/guides", tags=["guides"])

from ..core.security import get_current_user, AuthUser
from pydantic import BaseModel

class ExerciseWithProgressOut(BaseModel):
    id: str
    title: str | None = None
    type: str | None = None
    difficulty: str | None = None
    completed: bool
    attempts_count: int

@router.post('/', response_model=GuideOut, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_role('admin'))])
async def create_guide(payload: GuideCreate, db: Database = Depends(get_db)):
    data = payload.model_dump()
    data['id'] = str(uuid.uuid4())
    created = await db.create_guide(data)
    return GuideOut(**created)

@router.get('/', response_model=List[GuideOut])
async def list_guides(db: Database = Depends(get_db)):
    guides = await db.list_guides(active_only=False)
    return [GuideOut(**g) for g in guides]

@router.get('/{guide_id}', response_model=GuideOut)
async def get_guide(guide_id: str, db: Database = Depends(get_db)):
    guide = await db.get_guide(guide_id)
    if not guide:
        raise HTTPException(status_code=404, detail="Guía no encontrada")
    return GuideOut(**guide)

@router.get('/{guide_id}/exercises-with-progress', response_model=List[ExerciseWithProgressOut], summary="Lista ejercicios de la guía con flags de progreso del usuario actual")
async def exercises_with_progress(guide_id: str, db: Database = Depends(get_db), current_user: AuthUser = Depends(get_current_user)):
    # Validar guía existe (para 404 coherente)
    guide = await db.get_guide(guide_id)
    if not guide:
        raise HTTPException(status_code=404, detail="Guía no encontrada")
    rows = await db.list_exercises_with_progress(guide_id, current_user.id)
    return [ExerciseWithProgressOut(**r) for r in rows]

@router.patch('/{guide_id}', response_model=GuideOut, dependencies=[Depends(require_role('admin'))])
async def update_guide(guide_id: str, payload: GuideUpdate, db: Database = Depends(get_db)):
    existing = await db.get_guide(guide_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Guía no encontrada")
    update_data = {k: v for k, v in payload.model_dump(exclude_unset=True).items()}
    updated = await db.update_guide(guide_id, update_data)
    return GuideOut(**updated)

@router.delete('/{guide_id}', status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_role('admin'))])
async def delete_guide(guide_id: str, db: Database = Depends(get_db)):
    existing = await db.get_guide(guide_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Guía no encontrada")
    await db.delete_guide(guide_id)
    return None
