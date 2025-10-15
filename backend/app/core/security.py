from typing import Annotated, Dict, Any, Optional
import re
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
import jwt
import httpx
from functools import lru_cache
from ..core.config import get_settings
from ..db.database import get_db, Database

# Ajustamos auto_error=False para poder controlar el mensaje y devolver 401 en lugar de 403
http_bearer = HTTPBearer(auto_error=False)
settings = get_settings()

JWKS_URL_SUFFIX = "/auth/v1/.well-known/jwks.json"

class AuthUser(BaseModel):
    id: str
    role: str
    email: str
    name: str

@lru_cache
def _jwks() -> Dict[str, Any]:  # type: ignore[override]
    # Sin uso directo; placeholder para tipado
    return {}

_cached_jwks: Dict[str, Any] | None = None

async def _get_jwks() -> Dict[str, Any]:
    global _cached_jwks
    if _cached_jwks is None:
        url = settings.SUPABASE_URL.rstrip('/') + JWKS_URL_SUFFIX
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url)
            if resp.status_code != 200:
                raise HTTPException(status_code=500, detail="No se pudo obtener JWKS de Supabase")
            _cached_jwks = resp.json()
    return _cached_jwks

def _match_jwk(jwks: Dict[str, Any], kid: str) -> Dict[str, Any] | None:
    for k in jwks.get('keys', []):
        if k.get('kid') == kid:
            return k
    return None

async def _decode_supabase_token(token: str) -> Dict[str, Any]:
    try:
        unverified = jwt.get_unverified_header(token)
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Header JWT inválido")
    kid = unverified.get('kid')
    alg = unverified.get('alg')
    if settings.DEBUG_AUTH:
        print(f"[AUTH DEBUG] header={unverified}")
    # HS* tokens (Supabase default) – validar siempre con secreto aunque venga kid
    if alg and alg.startswith('HS'):
        secret = settings.SUPABASE_JWT_SECRET
        if not secret:
            raise HTTPException(status_code=500, detail="Falta SUPABASE_JWT_SECRET en entorno para validar tokens HS256")
        if settings.DEBUG_AUTH:
            print("[AUTH DEBUG] Validando HS con SUPABASE_JWT_SECRET")
        try:
            return jwt.decode(
                token,
                secret,
                algorithms=[alg],
                options={"verify_aud": False},
            )
        except jwt.PyJWTError as e:
            raise HTTPException(status_code=401, detail=f"Token inválido (HS): {e}")

    # RS* (cuando Supabase esté configurado para rotar a claves públicas)
    jwks = await _get_jwks()
    jwk_dict = _match_jwk(jwks, kid)
    if not jwk_dict:
        raise HTTPException(status_code=401, detail="Clave JWK no encontrada")
    try:
        public_key = jwt.algorithms.RSAAlgorithm.from_jwk(jwk_dict)  # type: ignore[attr-defined]
        return jwt.decode(
            token,
            public_key,
            algorithms=[jwk_dict.get('alg', 'RS256')],
            audience=None,
            options={"verify_aud": False},
        )
    except jwt.PyJWTError as e:
        raise HTTPException(status_code=401, detail=f"Token inválido (RSA): {e}")

async def get_current_user(
    creds: Annotated[Optional[HTTPAuthorizationCredentials], Depends(http_bearer)],
    db: Annotated[Database, Depends(get_db)],
    request: Request = None,
) -> AuthUser:
    token: Optional[str] = None
    # Obtener header intentando ambas capitalizaciones
    auth_header = None
    if request:
        auth_header = request.headers.get('Authorization') or request.headers.get('authorization')

    if settings.DEBUG_AUTH:
        print(f"[AUTH DEBUG] raw Authorization repr={repr(auth_header)}")

    # 1) Si HTTPBearer lo parseó
    if creds and creds.credentials:
        token = creds.credentials.strip()
        if settings.DEBUG_AUTH:
            print(f"[AUTH DEBUG] HTTPBearer extrajo token len={len(token)}")
    else:
        # 2) Fallback manual simple
        if auth_header:
            stripped = auth_header.strip()
            if settings.DEBUG_AUTH and stripped != auth_header:
                print(f"[AUTH DEBUG] Header tenía espacios externos, normalizado: {repr(stripped)}")
            if re.fullmatch(r'Bearer\s*', stripped, flags=re.IGNORECASE):
                if settings.DEBUG_AUTH:
                    print("[AUTH DEBUG] Sólo 'Bearer' sin token")
            elif re.match(r'Bearer\s+', stripped, flags=re.IGNORECASE):
                parts = stripped.split(None, 1)  # máximo 2 partes
                if len(parts) == 2:
                    candidate = parts[1].strip()
                    if candidate:
                        token = candidate
                        if settings.DEBUG_AUTH:
                            print(f"[AUTH DEBUG] Fallback extrajo token len={len(token)} head_snip={candidate[:10]}")
                    else:
                        if settings.DEBUG_AUTH:
                            print("[AUTH DEBUG] Token vacío tras 'Bearer'")
            else:
                if settings.DEBUG_AUTH:
                    print(f"[AUTH DEBUG] Header sin prefijo Bearer: {repr(stripped)}")

    if not token:
        if settings.DEBUG_AUTH and request:
            print("[AUTH DEBUG] ---- HEADERS COMPLETOS ----")
            for k, v in request.headers.items():
                print(f"[AUTH DEBUG] {k}: {repr(v)}")
        raise HTTPException(
            status_code=401,
            detail="Missing bearer token (Authorization: Bearer <token>)"
        )

    if settings.DEBUG_AUTH:
        print(f"[AUTH DEBUG] Decodificando token len={len(token)}")

    payload = await _decode_supabase_token(token)
    user_id = payload.get('sub') or payload.get('user_id')
    if not user_id:
        raise HTTPException(status_code=401, detail="Token sin sub")
    # Recuperar info de tabla users (enlazada por email o id)
    user = await db.get_user_by_id(user_id)
    if not user:
        # fallback: crear registro de usuario local si no existe
        # Se asume que payload contiene email
        email = payload.get('email') or payload.get('user_metadata', {}).get('email')
        if not email:
            raise HTTPException(status_code=401, detail="Usuario no registrado en base local")
        # Rol: mapear claims externos a roles soportados ('admin','student')
        raw_role = (
            payload.get('role')
            or payload.get('app_metadata', {}).get('role')
            or payload.get('user_role')
            or 'student'
        )
        role = raw_role if raw_role in ("admin", "student") else "student"
        # Nombre derivado
        name = payload.get('user_metadata', {}).get('name') or email.split('@')[0]
        # Insert simple
        user = await db.create_user({
            'id': user_id,
            'name': name,
            'email': email,
            'role': role,
        })
    return AuthUser(**user)

def require_role(*roles: str):
    async def role_checker(current_user: Annotated[AuthUser, Depends(get_current_user)]) -> AuthUser:
        if current_user.role not in roles:
            raise HTTPException(status_code=403, detail="No autorizado")
        return current_user
    return role_checker
