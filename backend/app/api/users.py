from fastapi import APIRouter, Depends
from typing import List
from ..models.user import UserOut
from ..core.security import get_current_user, require_role, AuthUser
from ..db.database import get_db, Database

router = APIRouter(prefix="/users", tags=["users"])

@router.get('/me', response_model=UserOut, summary="Perfil del usuario autenticado (Supabase)")
async def me(current_user: AuthUser = Depends(get_current_user)):
    return current_user

@router.get('/', response_model=List[UserOut], dependencies=[Depends(require_role('admin'))], summary="Listar usuarios (admin)")
async def list_users(db: Database = Depends(get_db)):
    users = await db.list_users()
    return [UserOut(**u) for u in users]
