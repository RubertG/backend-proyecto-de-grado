# Backend – Educational Platform

## 1. Resumen
API FastAPI para gestión de usuarios (perfil), guías, ejercicios, intentos y progreso. Feedback LLM aún no implementado.

## 2. Stack
- FastAPI / Uvicorn
- Supabase (PostgreSQL + Auth + RLS)
- Pydantic v2
- Supabase Python SDK

## 3. Flujo de Autenticación (Supabase Auth)
1. Frontend (Next.js) realiza signup/login con `supabase-js`.
2. Obtiene `session.access_token` (JWT firmado por Supabase).
3. El frontend envía `Authorization: Bearer <token>` al backend.
4. El backend descarga (cachea) JWKS público (`<SUPABASE_URL>/auth/v1/.well-known/jwks.json`) y valida la firma.
5. Extrae `sub` (user id). Si no existe en tabla `users`, crea registro local (auto-provisioning) con rol por defecto `student`.
6. Autorización por rol mediante dependencia `require_role('admin')`.

## 4. Variables de Entorno (.env)
```
SUPABASE_URL=https://<PROJECT_ID>.supabase.co
SUPABASE_ANON_KEY=YOUR_PUBLIC_ANON_KEY
```
(No se usan claves JWT propias.)

Obtenerlas: Supabase Dashboard > Project Settings > API.

## 5. Roles
- Campo `role` en tabla `users`.
- (Opcional) Añadir `app_metadata.role` para que viaje dentro del JWT.
- Si se define `app_metadata.role`, tras un nuevo login el backend puede confiar directamente sin lookup adicional (aun así se mantiene la tabla para queries).

### Cómo asignar rol admin en `app_metadata`
Dashboard:
1. Auth > Users > seleccionar usuario.
2. Edit user > `app_metadata` agregar `{ "role": "admin" }`.
3. Guardar y pedir al usuario re-login.

Admin API (curl ejemplo – usar Service Role Key en backend, nunca en frontend):
```
curl -X PATCH \
  -H "apikey: $SERVICE_ROLE_KEY" \
  -H "Authorization: Bearer $SERVICE_ROLE_KEY" \
  -H "Content-Type: application/json" \
  https://<PROJECT_ID>.supabase.co/auth/v1/admin/users/<USER_ID> \
  -d '{"app_metadata": {"role": "admin"}}'
```

## 6. Endpoints Principales (prefijo `/api/v1`)
- Users: `GET /users/me`, `GET /users/` (admin)
- Guides: CRUD
- Exercises: CRUD y listar por guía
- Attempts: crear intento, listar intentos propios
- Progress: marcar guía completada, listar completadas

## 7. Ejecución Local
```
python -m venv .venv
. .venv/Scripts/Activate.ps1  # Windows PowerShell
pip install -r requirements.txt
uvicorn app.main:app --reload
```
Swagger UI: `http://localhost:8000/docs`

## 8. Auto-Provisioning de Usuarios
Primer request autenticado:
- Si user `sub` no está en tabla `users`, se crea: `{id=sub, email, name derivado, role=student}`.
- Para elevar a admin, actualizar fila o `app_metadata.role` y reloguear.

## 9. Próximos Pasos
- Añadir feedback automático LLM en `app/llm/`.
- Tests (pytest) para autorización y roles.
- RLS en Postgres para capas extra si se expone Supabase directamente al frontend.

## 10. Solución de Problemas
| Problema | Causa Común | Acción |
|----------|-------------|-------|
| 401 Token inválido | Proyecto URL incorrecto o token expirado | Verificar `SUPABASE_URL`, re-login |
| 403 No autorizado | Rol insuficiente | Confirmar `users.role` o `app_metadata.role` |
| Usuario no creado | JWT sin email en claims | Revisar provider / añadir email a user_metadata |

## 11. Seguridad
- No exponer Service Role Key en frontend.
- Rotar anon key si se filtra.
- Usar HTTPS siempre en producción.

## 12. Seed de Datos de Prueba
Archivo raíz: `seed_test_data.sql`

Objetivo: Poblar guías, ejercicios y attempts de ejemplo para validar lógica de progreso y validación estructural.

Contenido principal:
- 3 guías activas (CLI Básico, Docker Fundamentos, Conceptos de Contenedores)
- Ejercicios de tipos `command`, `dockerfile`, `conceptual`
- Attempts de ejemplo (conceptual completo, command completo, dockerfile incompleto)
- Registro en `completed_guides` para una guía

Ejecución (Supabase Dashboard):
1. SQL Editor > pegar contenido > ejecutar.
2. Ajustar `user_id` de attempts si no corresponde a un usuario real (puedes crear usuario manualmente en tabla `users`).

Ejecución CLI (`psql`):
```bash
psql $SUPABASE_DB_URL -f seed_test_data.sql
```
Variables: usar la conexión directa del proyecto (Settings > Database > Connection string). No usar en producción.

Advertencias:
- Los `DELETE` iniciales están comentados; descoméntalos sólo en entornos aislados.
- Cambiar UUID si chocan con datos existentes.
- No contiene transacciones; si falla mitad, limpiar manualmente.

Validación rápida post-seed:
```bash
psql $SUPABASE_DB_URL -c "SELECT count(*) FROM guides;"
psql $SUPABASE_DB_URL -c "SELECT count(*) FROM exercises;"
psql $SUPABASE_DB_URL -c "SELECT count(*) FROM exercise_attempts;"
```
Luego iniciar backend y llamar `GET /api/v1/progress/overview` autenticado para verificar totales.

---
Este README refleja el estado actual (sin feedback LLM).
