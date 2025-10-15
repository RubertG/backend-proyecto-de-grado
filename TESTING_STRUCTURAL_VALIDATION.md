# Guía de pruebas: Validación estructural (Insomnia / Postman)

Esta guía asume:
- Backend corriendo en `http://localhost:8000`
- Autenticación via Supabase: ya obtuviste un JWT válido (usuario con rol `authenticated` => interno `student` o un `admin` para crear recursos)
- Semilla ejecutada: `seed_test_data.sql`

## IDs relevantes sembrados
Guías:
- CLI Básico: `11111111-1111-1111-1111-111111111111`
- Docker Fundamentos: `22222222-2222-2222-2222-222222222222`

Ejercicios (type / flag estructural):
| ID | Título | Tipo | enable_structural_validation |
| --- | --- | --- | --- |
| aaaaaaa1-0000-0000-0000-000000000001 | Listado de archivos | command | true |
| aaaaaaa1-0000-0000-0000-000000000002 | Mostrar versión de Docker | command | true |
| bbbbbbb1-0000-0000-0000-000000000001 | Dockerfile Python FastAPI | dockerfile | true |
| bbbbbbb1-0000-0000-0000-000000000002 | Dockerfile multi-stage | dockerfile | true |
| ccccccc1-0000-0000-0000-000000000001 | Pregunta conceptual | conceptual | true |

## Autenticación
Añade un header:
```
Authorization: Bearer <TU_TOKEN_JWT_SUPABASE>
```

## 1. Probar ejercicio tipo command
### 1.1 Caso válido (ls -la)
POST `/api/v1/attempts`
```json
{
  "exercise_id": "aaaaaaa1-0000-0000-0000-000000000001",
  "submitted_answer": "ls -la"
}
```
Respuesta esperada (clave):
- `structural_validation_passed: true`
- `structural_validation_errors: []`
- `structural_validation_warnings: []`
- `submitted_answer` igual a enviado.

### 1.2 Comando vacío
```json
{
  "exercise_id": "aaaaaaa1-0000-0000-0000-000000000001",
  "submitted_answer": "   "
}
```
Esperado:
- `structural_validation_passed: false`
- `structural_validation_errors` contiene `"Comando vacío"`
- `structural_validation_warnings: []`

### 1.3 Comando no permitido
```json
{
  "exercise_id": "aaaaaaa1-0000-0000-0000-000000000001",
  "submitted_answer": "rm -rf /"
}
```
Esperado:
- `structural_validation_passed: false`
- `structural_validation_errors` incluye `"Comando no permitido: rm"`
- Warnings vacíos

### 1.4 Comillas sin cerrar (error sintáctico)
```json
{
  "exercise_id": "aaaaaaa1-0000-0000-0000-000000000001",
  "submitted_answer": "echo 'hola"
}
```
Esperado: `structural_validation_passed: false` con error `Comillas sin cerrar`.

## 2. Probar ejercicio tipo dockerfile
### 2.1 Dockerfile válido
```json
{
  "exercise_id": "bbbbbbb1-0000-0000-0000-000000000001",
  "submitted_answer": "FROM python:3.12-slim\nWORKDIR /app\nCMD [\"python\", \"--version\"]"
}
```
Esperado:
- `structural_validation_passed: true`
- Si usas tag `:latest` aparecería warning correspondiente; con `python:3.12-slim` no hay warnings.

### 2.2 Dockerfile vacío
```json
{
  "exercise_id": "bbbbbbb1-0000-0000-0000-000000000001",
  "submitted_answer": "   "
}
```
Esperado:
- `structural_validation_passed: false`
- `structural_validation_errors` incluye al menos:
  - `"La primera instrucción debe ser FROM"`
  - `"Instrucciones desconocidas: FRM"`

### 2.3 Dockerfile con instrucción rota
```json
{
  "exercise_id": "bbbbbbb1-0000-0000-0000-000000000001",
  "submitted_answer": "FRM python:3.12-slim"
}
```
`FRM` no es `FROM`. La librería probablemente fallará al parsear.
Esperado: `structural_validation_passed: false`

### 2.4 Multi-stage simple válido
```json
{
  "exercise_id": "bbbbbbb1-0000-0000-0000-000000000002",
  "submitted_answer": "FROM node:20-alpine as build\nWORKDIR /app\nCMD [\"node\", \"--version\"]\nFROM nginx:alpine\nCMD [\"nginx\", \"-g\", \"daemon off;\"]"
}
```
Esperado: `structural_validation_passed: true` (puede haber warnings si se usa `latest`).

## 3. Probar ejercicio conceptual
```json
{
  "exercise_id": "ccccccc1-0000-0000-0000-000000000001",
  "submitted_answer": "Una imagen es ..."
}
```
Esperado:
- `structural_validation_passed: true`
- `structural_validation_errors: []`
- `structural_validation_warnings: []` (conceptual no genera warnings)

## 4. Desactivar validación estructural y reintentar
PATCH `/exercises/aaaaaaa1-0000-0000-0000-000000000001`
(Requires rol admin) Body:
```json
{
  "enable_structural_validation": false
}
```
Ahora repetir un intento con comando inválido:
```json
{
  "exercise_id": "aaaaaaa1-0000-0000-0000-000000000001",
  "submitted_answer": "rm -rf /"
}
```
Esperado:
- `structural_validation_passed: null`
- `structural_validation_errors: []`
- `structural_validation_warnings: []`
Porque se omite la validación.

## 5. Listar intentos por ejercicio
GET `/attempts/by-exercise/aaaaaaa1-0000-0000-0000-000000000001`
Devuelve lista ordenada desc (por `created_at` en DB). Verifica distintos valores de `structural_validation_passed`.

## 6. Errores esperados
- Ejercicio inexistente: 404 con `detail: "Ejercicio no encontrado"`
- Sin token válido: 401

## Notas
- No se compara contra `expected_answer` aún (eso sería evaluación de corrección, diferente de validación estructural).
- `llm_feedback` permanece null; se poblará cuando se implemente lógica de LLM.
- Campos nuevos siempre presentes: `structural_validation_errors` y `structural_validation_warnings` (listas vacías si no aplica).
- Si `enable_llm_feedback` es false actualmente no impacta nada.

---
Checklist rápido:
- [ ] Intentos command válidos/ inválidos
- [ ] Intentos dockerfile válidos/ inválidos
- [ ] Conceptual siempre true
- [ ] Flag apagado omite validación
- [ ] Listado de intentos refleja resultados
