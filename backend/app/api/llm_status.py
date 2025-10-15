from fastapi import APIRouter, Depends
from ..core.security import get_current_user, AuthUser
from ..db.database import get_db, Database
from ..llm_feedback.feedback_chain import get_llm_client, get_feedback_service
from ..llm_feedback.prompt_builder import MAX_PROMPT_CHARS

router = APIRouter(prefix="/llm", tags=["llm"])

@router.get('/status')
async def llm_status(db: Database = Depends(get_db), current_user: AuthUser = Depends(get_current_user)):
    client = get_llm_client()
    # Determinar si similitud está disponible
    service = await get_feedback_service(db)
    similarity_enabled = hasattr(service.vs, 'similar')
    api_key_present = bool(client._chain)  # si hay cadena real se asumirá clave presente
    return {
        'model': client.model,
        'temperature': client.temperature,
        'stub_mode': client._chain is None,
        'api_key_present': api_key_present,
        'similarity_enabled': similarity_enabled,
        'prompt_budget_chars': MAX_PROMPT_CHARS,
        'lazy_attempts': getattr(client, '_lazy_attempts', None),
        'last_lazy_error': getattr(client, '_last_lazy_error', None),
        'last_lazy_time': getattr(client, '_last_lazy_time', None),
    }
