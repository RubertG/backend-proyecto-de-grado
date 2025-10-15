# Guía de pruebas: Módulo de Feedback LLM (Insomnia / Postman)

Esta guía cubre las pruebas manuales del módulo de feedback automático y chat educativo.

Asume:
- Backend corriendo en `http://localhost:8000`
- Prefijo de API (ajusta si tu app lo usa) por ejemplo `/api/v1`
- Token JWT Supabase válido (rol `authenticated` => usuario interno `student`)
- Semilla ejecutada (`seed_test_data.sql`) que marcó ciertos ejercicios con `enable_llm_feedback = true`
- Variable `GOOGLE_API_KEY` opcional: si no está definida el sistema devolverá respuestas stub estructuradas.

## Objetivos de verificación
1. Generar feedback LLM para un intento de ejercicio con flag activo.
2. Confirmar que se persiste intento con `llm_feedback`.
3. Observar métricas (`prompt_tokens`, `completion_tokens`, `latency_ms`, `quality_flags`).
4. Validar manejo de errores: ejercicio inexistente, feedback deshabilitado, sin token.
5. Probar conversación (`/feedback/chat`) y ver historial acumulado (`/feedback/history`).
6. Ver almacenamiento dual (attempt + feedback) en vector store reflejado en `/feedback/history`.

## Encabezados comunes
```
Authorization: Bearer <TU_TOKEN_JWT_SUPABASE>
Content-Type: application/json
```

## IDs de ejemplo (ajusta según tus seeds)
Ejercicios con LLM habilitado (ejemplo):
- Ejercicio command: `aaaaaaa1-0000-0000-0000-000000000001`
- Ejercicio dockerfile: `bbbbbbb1-0000-0000-0000-000000000001`
- Ejercicio conceptual: `ccccccc1-0000-0000-0000-000000000001`

Verifica antes vía `GET /exercises/<id>` que `enable_llm_feedback` sea `true`.

## 1. Crear feedback de intento
POST `/feedback/attempt`
Body ejemplo (command):
```json
{
  "exercise_id": "aaaaaaa1-0000-0000-0000-000000000001",
  "submitted_answer": "ls -la"
}
```
Respuesta esperada (claves principales):
```jsonc
{
  "attempt_id": "<uuid>",
  "content_md": "Texto en Markdown (puede contener algunos encabezados opcionales)...",
  "metrics": {
    "model": "<modelo_configurado>",
    "prompt_tokens": 120, // aprox
    "completion_tokens": 160, // aprox
    "latency_ms": 850, // depende
    "quality_flags": { /* puede estar vacío o tener banderas */ }
  }
}
```
Notas:
- Si no hay `GOOGLE_API_KEY` `content_md` tendrá un mensaje stub breve (sin secciones obligatorias).
- Las secciones (`## Fortalezas`, `## Errores`, etc.) son OPCIONALES: sólo aparecen si el modelo aporta contenido útil.
- No se incluyen enlaces externos ni referencias.

### 1.1 Error: ejercicio inexistente
```json
{
  "exercise_id": "zzzzzzzz-1111-2222-3333-444444444444",
  "submitted_answer": "echo test"
}
```
Respuesta: 404 `{ "detail": "Ejercicio no encontrado" }`

### 1.2 Error: feedback deshabilitado
1. PATCH (admin) `/exercises/<id>` con body:
```json
{ "enable_llm_feedback": false }
```
2. Repite POST `/feedback/attempt`.
Esperado: 400 `{ "detail": "Feedback LLM deshabilitado para este ejercicio" }`

## 2. Verificar intento creado (endpoint de intentos existente)
GET `/attempts/by-exercise/aaaaaaa1-0000-0000-0000-000000000001`
Busca el `attempt_id` retornado en paso 1. Debe mostrar:
- `llm_feedback` (Markdown completo)
- `structural_validation_passed` puede ser `true/false/null` según flags
- `submitted_answer` igual al enviado

## 3. Crear múltiples intentos y observar reutilización de contexto
Realiza 3 veces POST `/feedback/attempt` variando `submitted_answer`:
1. `ls -la`
2. `ls`
3. `pwd`
Luego un cuarto intento con algo distinto: `whoami`

Verifica que:
- La calidad de feedback puede mencionar consistencia o comparar con previos (si el modelo real está activo).
- `prompt_tokens` tienden a subir moderadamente (más historial incluido) hasta un límite.

## 4. Chat de seguimiento
POST `/feedback/chat`
Body:
```json
{
  "exercise_id": "aaaaaaa1-0000-0000-0000-000000000001",
  "message": "¿Cómo podría mejorar el uso de este comando?"
}
```
Respuesta esperada:
```jsonc
{
  "content_md": "Respuesta breve en Markdown (6-14 líneas aprox)",
  "metrics": {
    "model": "<modelo>",
    "prompt_tokens": <num>,
    "completion_tokens": <num>,
    "latency_ms": <num>
  }
}
```
Notas:
- El chat usa formato flexible; no se fuerzan encabezados ni placeholders.

### 4.1 Mensaje vacío (client-side)
Si envías `"message": ""` debería fallar validación 422 (Pydantic) por `min_length=1`.

## 5. Historial agregado
GET `/feedback/history?exercise_id=aaaaaaa1-0000-0000-0000-000000000001`
Esperado: lista ordenada cronológicamente (ascendente) de items:
```jsonc
[
  { "type": "attempt", "content_md": "ls -la", "created_at": "..." },
  { "type": "feedback", "content_md": "## Fortalezas...", ... },
  { "type": "attempt", ... },
  { "type": "feedback", ... },
  { "type": "question", "content_md": "¿Cómo podría..." },
  { "type": "answer", "content_md": "## Fortalezas..." }
]
```
Verifica alternancia lógica.

## 6. Métricas persistidas (opcional, inspección directa DB)
Consulta en Postgres:
```sql
SELECT model, prompt_tokens, completion_tokens, latency_ms, quality_flags
FROM llm_metrics
WHERE exercise_id = 'aaaaaaa1-0000-0000-0000-000000000001'
ORDER BY created_at DESC
LIMIT 10;
```
Revisa variación de tokens y latencia.

## 7. Pruebas con otro tipo de ejercicio (dockerfile)
POST `/feedback/attempt`
```json
{
  "exercise_id": "bbbbbbb1-0000-0000-0000-000000000001",
  "submitted_answer": "FROM python:3.12-slim\nWORKDIR /app\nCMD [\"python\", \"--version\"]"
}
```
Revisa que el feedback se adapta mínimamente (si el modelo real está activo podría mencionar Docker). Si stub, texto genérico.

## 8. Comportamiento sin `GOOGLE_API_KEY`
Quita (o no definas) la variable y repite pasos 1 y 4. Debes obtener siempre el stub con secciones fijas y sin errores.

## 9. Campos y formatos obligatorios
Checklist de cada respuesta /feedback/attempt:
- attempt_id presente
- content_md no vacío
- metrics.model coincide con configuración
- metrics.prompt_tokens > 0
- metrics.completion_tokens > 0
- metrics.latency_ms >= 0

Checklist de cada respuesta /feedback/chat:
- content_md no vacío
- metrics presentes

## 10. Errores comunes adicionales
| Situación | Resultado esperado |
|-----------|--------------------|
| Falta header Authorization | 401 Unauthorized |
| exercise_id vacío | 422 Unprocessable Entity |
| submitted_answer vacío | 422 (min_length=1) |
| enable_llm_feedback false | 400 detalle específico |

## 11. Estrategia de regresión rápida
1. Ejecutar un intento válido (command).
2. Ejecutar un chat.
3. Ver historial (contar elementos >=4 tras ambos pasos).
4. Desactivar flag -> forzar error 400.
5. Reactivar flag -> nuevo intento succeed.

## 12. Siguientes mejoras (no probadas aún)
- Recuperación semántica por similitud (YA incorporada).
- Prompts adaptados por `exercise.type` (YA incorporado).
- Conteo real de tokens desde API del proveedor (pendiente).

---
Checklist rápido de verificación manual:
- [ ] /feedback/attempt éxito
- [ ] /feedback/attempt error ejercicio inexistente
- [ ] /feedback/attempt feedback deshabilitado
- [ ] Múltiples intentos con métricas crecientes
- [ ] /feedback/chat respuesta estructurada
- [ ] /feedback/history orden correcto
- [ ] Stub funciona sin GOOGLE_API_KEY
- [ ] Desactivar y reactivar flag funciona
- [ ] Métricas presentes y razonables
