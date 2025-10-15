from fastapi import APIRouter, Depends
from typing import List
from ..core.security import require_role, AuthUser
from ..db.database import get_db, Database
from ..models.metrics import LLMMetricOverviewItem, LLMMetricOverviewResponse

router = APIRouter(prefix="/metrics", tags=["metrics"])


@router.get('/overview', response_model=LLMMetricOverviewResponse, summary="Listado enriquecido de métricas LLM (admin)")
async def metrics_overview(
    limit: int = 200,
    db: Database = Depends(get_db),
    _: AuthUser = Depends(require_role('admin')),
):
    metrics = await db.list_llm_metrics(limit=limit)
    user_ids = list({m['user_id'] for m in metrics if m.get('user_id')})
    exercise_ids = list({m['exercise_id'] for m in metrics if m.get('exercise_id')})
    users_map = await db.get_users_by_ids(user_ids)
    exercises_map = await db.get_exercises_by_ids(exercise_ids)

    items: List[LLMMetricOverviewItem] = []
    for m in metrics:
        u = users_map.get(m.get('user_id')) or {}
        e = exercises_map.get(m.get('exercise_id')) or {}
        # Reducir ejercicio y usuario a campos principales para no sobrecargar
        user_view = {
            'id': u.get('id'),
            'name': u.get('name'),
            'email': u.get('email'),
            'role': u.get('role'),
        } if u else {}
        exercise_view = {
            'id': e.get('id'),
            'title': e.get('title'),
            'type': e.get('type'),
            'difficulty': e.get('difficulty'),
        } if e else {}
        items.append(LLMMetricOverviewItem(
            **m,
            user=user_view,
            exercise=exercise_view,
        ))

    return LLMMetricOverviewResponse(items=items, count=len(items))
