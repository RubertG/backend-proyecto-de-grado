from fastapi import APIRouter, Depends, HTTPException, status, Query
from ..core.security import get_current_user, AuthUser
from ..db.database import get_db, Database
from pydantic import BaseModel
import uuid
from typing import List, Optional, Any, Dict

router = APIRouter(prefix="/progress", tags=["progress"])


class CompletedGuideIn(BaseModel):
    guide_id: str


class CompletedGuideOut(BaseModel):
    id: str
    guide_id: str
    user_id: str
    completed_at: str


class GuideProgressOut(BaseModel):
    guide_id: str
    title: str | None = None
    topic: str | None = None
    total_exercises: int
    completed_exercises: int


class GuideExerciseMini(BaseModel):
    exercise_id: str
    title: str | None = None
    completed: bool


class GuideOverviewOut(BaseModel):
    guide_id: str
    title: str | None
    order: int | None = None
    total_exercises: int
    completed_exercises: int
    percent: float
    completed: bool
    exercises: Optional[List[GuideExerciseMini]] = None


class ProgressTotalsOut(BaseModel):
    total_guides: int
    completed_guides: int
    total_exercises: int
    completed_exercises: int
    percent_exercises: float


class ProgressOverviewOut(BaseModel):
    totals: ProgressTotalsOut
    guides: List[GuideOverviewOut]


@router.post('/complete', response_model=CompletedGuideOut, status_code=status.HTTP_201_CREATED, summary="Marcar guía como completada")
async def complete_guide(payload: CompletedGuideIn, db: Database = Depends(get_db), current_user: AuthUser = Depends(get_current_user)):
    guide = await db.get_guide(payload.guide_id)
    if not guide:
        raise HTTPException(status_code=404, detail="Guía no encontrada")
    data = {"id": str(uuid.uuid4()), "guide_id": payload.guide_id, "user_id": current_user.id}
    created = await db.mark_guide_completed(data)
    return CompletedGuideOut(**created)


@router.get('/completed', response_model=List[CompletedGuideOut], summary="Listar guías completadas del usuario actual")
async def list_completed(db: Database = Depends(get_db), current_user: AuthUser = Depends(get_current_user)):
    rows = await db.list_completed_guides(current_user.id)
    return [CompletedGuideOut(**r) for r in rows]


@router.get('/guides', response_model=List[GuideProgressOut], summary="Progreso agregado por guía del usuario actual")
async def guides_progress(db: Database = Depends(get_db), current_user: AuthUser = Depends(get_current_user)):
    rows = await db.list_guides_progress(current_user.id)
    return [GuideProgressOut(**r) for r in rows]


@router.get(
    '/overview',
    response_model=ProgressOverviewOut,
    response_model_exclude_none=True,
    summary="Resumen global de progreso del usuario actual"
)
async def progress_overview(
    include_exercises: bool = Query(False, description="Si true, incluye listado resumido de ejercicios por guía"),
    db: Database = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user)
):
    data: Dict[str, Any] = await db.get_progress_overview(current_user.id, include_exercises=include_exercises)
    # Adaptar dict a modelos Pydantic
    totals = ProgressTotalsOut(**data['totals'])
    guides_models: List[GuideOverviewOut] = []
    for g in data['guides']:
        exercises_list = None
        if include_exercises and 'exercises' in g:
            exercises_list = [GuideExerciseMini(**e) for e in g['exercises']]
        guides_models.append(GuideOverviewOut(
            guide_id=g['guide_id'],
            title=g.get('title'),
            order=g.get('order'),
            total_exercises=g['total_exercises'],
            completed_exercises=g['completed_exercises'],
            percent=g['percent'],
            completed=g['completed'],
            exercises=exercises_list
        ))
    return ProgressOverviewOut(totals=totals, guides=guides_models)
