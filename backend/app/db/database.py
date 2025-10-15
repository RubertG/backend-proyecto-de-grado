from typing import Any, Dict, List, Optional
from supabase import create_client, Client
from ..core.config import get_settings

settings = get_settings()

# Wrapper mínimo para operaciones necesarias (síncronas -> usando async interface superficial)
class Database:
    def __init__(self) -> None:
        self._client: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)

    # Users
    async def create_user(self, data: Dict[str, Any]) -> Dict[str, Any]:
        # data must not include password_hash; Supabase Auth stores credentials separately
        res = self._client.table('users').insert(data).execute()
        return res.data[0]

    async def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        res = self._client.table('users').select('*').eq('email', email).limit(1).execute()
        return res.data[0] if res.data else None

    async def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        res = self._client.table('users').select('*').eq('id', user_id).limit(1).execute()
        return res.data[0] if res.data else None

    async def list_users(self) -> List[Dict[str, Any]]:
        res = self._client.table('users').select('*').execute()
        return res.data

    # Guides
    async def create_guide(self, data: Dict[str, Any]) -> Dict[str, Any]:
        res = self._client.table('guides').insert(data).execute()
        return res.data[0]

    async def list_guides(self, active_only: bool = True) -> List[Dict[str, Any]]:
        query = self._client.table('guides').select('*')
        if active_only:
            query = query.eq('is_active', True)
        res = query.order('order', desc=False).execute()
        return res.data

    async def get_guide(self, guide_id: str) -> Optional[Dict[str, Any]]:
        res = self._client.table('guides').select('*').eq('id', guide_id).limit(1).execute()
        return res.data[0] if res.data else None

    async def update_guide(self, guide_id: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        res = self._client.table('guides').update(data).eq('id', guide_id).execute()
        return res.data[0] if res.data else None

    async def delete_guide(self, guide_id: str) -> None:
        self._client.table('guides').delete().eq('id', guide_id).execute()

    # Exercises
    async def create_exercise(self, data: Dict[str, Any]) -> Dict[str, Any]:
        res = self._client.table('exercises').insert(data).execute()
        return res.data[0]

    async def list_exercises_by_guide(self, guide_id: str) -> List[Dict[str, Any]]:
        res = self._client.table('exercises').select('*').eq('guide_id', guide_id).eq('is_active', True).execute()
        return res.data

    async def list_all_exercises(self, include_inactive: bool = True) -> List[Dict[str, Any]]:
        query = self._client.table('exercises').select('*')
        if not include_inactive:
            query = query.eq('is_active', True)
        res = query.order('created_at', desc=True).execute()
        return res.data

    async def get_exercise(self, exercise_id: str) -> Optional[Dict[str, Any]]:
        res = self._client.table('exercises').select('*').eq('id', exercise_id).limit(1).execute()
        return res.data[0] if res.data else None

    async def update_exercise(self, exercise_id: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        res = self._client.table('exercises').update(data).eq('id', exercise_id).execute()
        return res.data[0] if res.data else None

    async def delete_exercise(self, exercise_id: str) -> None:
        self._client.table('exercises').delete().eq('id', exercise_id).execute()

    # Attempts (sin feedback LLM)
    async def create_attempt(self, data: Dict[str, Any]) -> Dict[str, Any]:
        res = self._client.table('exercise_attempts').insert(data).execute()
        return res.data[0]

    async def list_attempts(self, exercise_id: str, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        query = self._client.table('exercise_attempts').select('*').eq('exercise_id', exercise_id)
        if user_id:
            query = query.eq('user_id', user_id)
        res = query.order('created_at', desc=True).execute()
        return res.data

    async def get_last_feedback(self, exercise_id: str, user_id: str) -> Optional[str]:
        res = self._client.table('exercise_attempts') \
            .select('llm_feedback') \
            .eq('exercise_id', exercise_id) \
            .eq('user_id', user_id) \
            .not_.is_('llm_feedback', 'null') \
            .order('created_at', desc=True) \
            .limit(1) \
            .execute()
        if res.data:
            return res.data[0].get('llm_feedback')
        return None

    async def mark_guide_completed(self, data: Dict[str, Any]) -> Dict[str, Any]:
        res = self._client.table('completed_guides').insert(data).execute()
        return res.data[0]

    async def list_completed_guides(self, user_id: str) -> List[Dict[str, Any]]:
        res = self._client.table('completed_guides').select('*').eq('user_id', user_id).execute()
        return res.data

    # LLM metrics
    async def create_llm_metric(self, data: Dict[str, Any]) -> Dict[str, Any]:
        res = self._client.table('llm_metrics').insert(data).execute()
        return res.data[0]

    async def list_llm_metrics(self, limit: int = 200) -> List[Dict[str, Any]]:
        # Devuelve las métricas más recientes primero
        res = self._client.table('llm_metrics').select('*').order('created_at', desc=True).limit(limit).execute()
        return res.data

    async def get_users_by_ids(self, user_ids: List[str]) -> Dict[str, Dict[str, Any]]:
        if not user_ids:
            return {}
        # Supabase in operator
        res = self._client.table('users').select('*').in_('id', user_ids).execute()
        return {u['id']: u for u in res.data}

    async def get_exercises_by_ids(self, exercise_ids: List[str]) -> Dict[str, Dict[str, Any]]:
        if not exercise_ids:
            return {}
        res = self._client.table('exercises').select('*').in_('id', exercise_ids).execute()
        return {e['id']: e for e in res.data}

    # Progress aggregations
    async def list_guides_progress(self, user_id: str) -> List[Dict[str, Any]]:
        """Devuelve por guía: total ejercicios y cuántos completados para el usuario.
        'Completado' se infiere si existe attempt.completed=true para ese ejercicio y usuario.
        """
        # Obtener todas las guías
        guides = self._client.table('guides').select('id,title,topic').execute().data
        guide_ids = [g['id'] for g in guides]
        if not guide_ids:
            return []
        # Ejercicios por guía
        exercises = self._client.table('exercises').select('id,guide_id').in_('guide_id', guide_ids).eq('is_active', True).execute().data
        exercise_ids = [e['id'] for e in exercises]
        # Attempts completados por usuario
        completed_attempts_map: Dict[str, bool] = {}
        if exercise_ids:
            attempts = self._client.table('exercise_attempts').select('exercise_id,completed').in_('exercise_id', exercise_ids).eq('user_id', user_id).eq('completed', True).execute().data
            for a in attempts:
                completed_attempts_map[a['exercise_id']] = True
        # Agregar
        # Map guía -> lista ejercicios
        guide_exercises: Dict[str, List[str]] = {}
        for e in exercises:
            guide_exercises.setdefault(e['guide_id'], []).append(e['id'])
        out: List[Dict[str, Any]] = []
        for g in guides:
            ex_ids = guide_exercises.get(g['id'], [])
            total = len(ex_ids)
            done = sum(1 for _id in ex_ids if completed_attempts_map.get(_id))
            out.append({
                'guide_id': g['id'],
                'title': g.get('title'),
                'topic': g.get('topic'),
                'total_exercises': total,
                'completed_exercises': done,
            })
        return out

    async def ensure_guide_completed(self, user_id: str, guide_id: str) -> None:
        """Marca una guía como completada para el usuario si TODOS sus ejercicios activos tienen al menos un attempt completed=true.

        Idempotente: si ya existe registro en completed_guides no crea duplicado.
        """
        # Verificar ya marcada
        existing = self._client.table('completed_guides').select('id').eq('guide_id', guide_id).eq('user_id', user_id).execute().data
        if existing:
            return
        # Obtener ejercicios activos de la guía
        exercises = self._client.table('exercises').select('id').eq('guide_id', guide_id).eq('is_active', True).execute().data
        if not exercises:
            return  # Guía sin ejercicios activos -> no marcamos
        exercise_ids = [e['id'] for e in exercises]
        # Attempts completados del usuario para esos ejercicios
        attempts = self._client.table('exercise_attempts').select('exercise_id,completed').in_('exercise_id', exercise_ids).eq('user_id', user_id).eq('completed', True).execute().data
        completed_set = {a['exercise_id'] for a in attempts if a.get('completed')}
        if len(completed_set) == len(exercise_ids):
            # Marcar guía
            self._client.table('completed_guides').insert({
                'id': __import__('uuid').uuid4().hex,
                'guide_id': guide_id,
                'user_id': user_id,
            }).execute()

    async def list_exercises_with_progress(self, guide_id: str, user_id: str) -> List[Dict[str, Any]]:
        exercises = self._client.table('exercises').select('id,title,type,difficulty').eq('guide_id', guide_id).eq('is_active', True).execute().data
        exercise_ids = [e['id'] for e in exercises]
        attempts_map: Dict[str, Dict[str, Any]] = {}
        attempts_count: Dict[str, int] = {eid: 0 for eid in exercise_ids}
        completed_map: Dict[str, bool] = {eid: False for eid in exercise_ids}
        if exercise_ids:
            attempts = self._client.table('exercise_attempts').select('exercise_id,completed').in_('exercise_id', exercise_ids).eq('user_id', user_id).execute().data
            for a in attempts:
                eid = a['exercise_id']
                attempts_count[eid] = attempts_count.get(eid, 0) + 1
                if a.get('completed'):
                    completed_map[eid] = True
        out: List[Dict[str, Any]] = []
        for e in exercises:
            eid = e['id']
            out.append({
                'id': eid,
                'title': e.get('title'),
                'type': e.get('type'),
                'difficulty': e.get('difficulty'),
                'completed': completed_map.get(eid, False),
                'attempts_count': attempts_count.get(eid, 0),
            })
        return out

    async def get_progress_overview(self, user_id: str, include_exercises: bool = False) -> Dict[str, Any]:
        """Devuelve métricas agregadas de progreso del usuario sobre todas las guías activas.

        Estructura:
        {
          totals: { total_guides, completed_guides, total_exercises, completed_exercises, percent_exercises },
          guides: [ { guide_id, title, order, total_exercises, completed_exercises, percent, completed, exercises? } ]
        }
        """
        # Guías activas
        guides = self._client.table('guides').select('id,title,topic,order').eq('is_active', True).order('order', desc=False).execute().data
        if not guides:
            return {
                'totals': {
                    'total_guides': 0,
                    'completed_guides': 0,
                    'total_exercises': 0,
                    'completed_exercises': 0,
                    'percent_exercises': 0.0
                },
                'guides': []
            }
        guide_ids = [g['id'] for g in guides]
        # Ejercicios activos de todas las guías
        exercises = self._client.table('exercises').select('id,guide_id,title').in_('guide_id', guide_ids).eq('is_active', True).execute().data
        exercise_ids = [e['id'] for e in exercises]
        # Attempts completados del usuario
        completed_exercise_ids: set[str] = set()
        if exercise_ids:
            attempts = self._client.table('exercise_attempts').select('exercise_id').in_('exercise_id', exercise_ids).eq('user_id', user_id).eq('completed', True).execute().data
            for a in attempts:
                completed_exercise_ids.add(a['exercise_id'])
        # Agrupar ejercicios por guía
        guide_exercises: Dict[str, List[Dict[str, Any]]] = {}
        for e in exercises:
            guide_exercises.setdefault(e['guide_id'], []).append(e)
        # Construir salida por guía
        guides_out: List[Dict[str, Any]] = []
        total_completed_exercises = 0
        for g in guides:
            ex_list = guide_exercises.get(g['id'], [])
            total_ex = len(ex_list)
            completed_ex = sum(1 for ex in ex_list if ex['id'] in completed_exercise_ids)
            total_completed_exercises += completed_ex
            percent = round((completed_ex / total_ex * 100.0), 2) if total_ex > 0 else 0.0
            guide_obj: Dict[str, Any] = {
                'guide_id': g['id'],
                'title': g.get('title'),
                'order': g.get('order'),
                'total_exercises': total_ex,
                'completed_exercises': completed_ex,
                'percent': percent,
                'completed': (total_ex > 0 and completed_ex == total_ex)
            }
            if include_exercises:
                guide_obj['exercises'] = [
                    {
                        'exercise_id': ex['id'],
                        'title': ex.get('title'),
                        'completed': ex['id'] in completed_exercise_ids
                    } for ex in ex_list
                ]
            guides_out.append(guide_obj)
        total_exercises = len(exercises)
        percent_exercises = round((total_completed_exercises / total_exercises * 100.0), 2) if total_exercises > 0 else 0.0
        completed_guides = sum(1 for g in guides_out if g['completed'])
        overview = {
            'totals': {
                'total_guides': len(guides),
                'completed_guides': completed_guides,
                'total_exercises': total_exercises,
                'completed_exercises': total_completed_exercises,
                'percent_exercises': percent_exercises
            },
            'guides': guides_out
        }
        return overview

_db_instance: Optional[Database] = None

async def get_db() -> Database:
    global _db_instance
    if _db_instance is None:
        _db_instance = Database()
    return _db_instance
