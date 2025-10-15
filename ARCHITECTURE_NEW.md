# Educational Platform – Backend Architecture Context

> NOTA: Este documento ha sido fusionado en `ARCHITECTURE.md`. Mantenerlo solo para referencia histórica temporal. Las actualizaciones futuras deben realizarse en `ARCHITECTURE.md`.

## 1. Resumen del Proyecto

El objetivo de esta plataforma es permitir el aprendizaje y la evaluación de conocimientos técnicos mediante guías y ejercicios interactivos. Los usuarios pueden ser **admins** (crean y gestionan contenido) o **students** (consumen contenido y resuelven ejercicios). El seguimiento del progreso y el feedback automatizado son fundamentales.  
**La retroalimentación automática de los ejercicios es generada usando modelos LLM (Gemini) vía LangChain y un wrapper propio.**  
**Las buenas prácticas de código y uso de herramientas también son evaluadas y retroalimentadas por el LLM.**

---

## 2. Stack Tecnológico

- **Backend:** FastAPI (Python 3.12+)
- **Frontend:** Next.js (TypeScript)
- **Base de datos:** Supabase (PostgreSQL + Row Level Security)
- **ORM/DB:** Conexión directa vía SDK Supabase (no ORM adicional)
- **Auth:** **Supabase Auth** (JWT); validación de firma (JWKS). No se manejan contraseñas en backend.
- **Roles:** Persistidos en tabla `users` y/o `app_metadata.role`.
- **Feedback automático:** Módulo LLM implementado (`app/llm_feedback/`) con: similitud semántica, prompts especializados, modo stub, lazy init, métricas y endpoint de estado.
- **Infraestructura:** Uvicorn (ASGI), despliegue en servicios compatibles.

---

## 3. Esquema de la Base de Datos

Ver `educational_platform_schema.sql`.

Tablas principales:
- `users`: id, name, email, role.
- `guides`: contenido organizado por temas.
- `exercises`: referencia a guía + tipo (`command|dockerfile|conceptual`), dificultad, expected_answer.
- `exercise_attempts`: intentos con `submitted_answer`, `structural_validation_passed`, `llm_feedback`.
- `completed_guides`: progreso.
- `llm_metrics`: métricas de invocaciones LLM (JSONB quality_flags).

---

## 4. Estructura de Carpetas (Backend)

```
backend/app/
  api/              # Routers FastAPI
  core/             # Config, seguridad
  db/               # Acceso DB
  llm_feedback/     # Módulo LLM (prompt, chain, vector store, métricas)
  validators/       # Validación estructural
  models/           # Schemas Pydantic
  main.py           # FastAPI app
```

---

## 5. Reglas de Negocio (resumen)
- Auto-provisioning de usuarios al primer request autenticado.
- Ejercicios tipados; validación estructural para `command` y `dockerfile` antes del feedback semántico.
- Feedback LLM almacenado en `exercise_attempts.llm_feedback`.
- Múltiples intentos por usuario; cada intento genera nuevo feedback (sin reuso forzado).

---

## 6. Validación Estructural
- `command`: chequeo sintaxis, comandos prohibidos, flags.
- `dockerfile`: uso de `dockerfile-parse`, verificación de instrucciones.
- `conceptual`: no aplica validación estructural (se considera válido).

---

## 7. Endpoints Clave
- Usuarios: `/users/me`
- Guías & ejercicios CRUD (admin) y lectura (student)
- Intentos: crear intento, historial, métricas implícitas
- Feedback LLM: `POST /feedback/attempt`, `POST /feedback/chat`, `GET /feedback/history`, `GET /llm/status`

---

## 8. Convenciones de Código
- Pydantic v2, endpoints organizados por recurso.
- Dependencias para auth y roles.
- Logs estructurados (logger `llm`).
- Tiempos y timestamps en UTC.

---

## 9. Flujo de Usuario (alto nivel)
1. Autenticación (Supabase) en frontend.
2. Backend valida JWT y auto-registra usuario.
3. Usuario consume guías y envía intentos.
4. Validación estructural (según tipo).
5. Generación de feedback LLM y persistencia.
6. Historial y métricas disponibles.

---

## 10. Referencias
- FastAPI, Supabase, LangChain, dockerfile-parse.

---

## 11. Módulo de Feedback LLM

### 11.1 Objetivo
Retroalimentación pedagógica concisa (6–14 líneas) y chat de mejora continua, evitando secciones vacías y enlaces externos.

### 11.2 Componentes
- `feedback_chain.py`: Orquestación completo ciclo.
- `prompt_builder.py`: Prompt especializado por tipo + truncado progresivo (budget ~6000 chars).
- `postprocess.py`: `normalize_output` (remueve encabezados vacíos) + sanitización de enlaces/citas.
- `vector_store.py`: Guarda intentos y feedback; similaridad coseno simple.
- `metrics.py`: Latencia, tamaño estimado (chars/4), quality_flags.
- `llm_status.py`: Estado interno (`/llm/status`).

### 11.3 Flujo de Intento
1. Validar ejercicio y flag.
2. Recolectar contexto (intentos previos, diálogo, feedback previo).
3. Construir prompt especializado y truncar si excede budget.
4. Enriquecer con fragmentos similares (si no sobrepasa ~18% extra).
5. Invocar LLM (o stub; lazy init si aparece API key luego).
6. Normalizar salida y sanitizar enlaces.
7. Persistir intento, feedback, métricas y vector store.

### 11.4 Chat
- Entrada: mensaje + historial condensado + similaridad opcional.
- Salida: `content_md` flexible (no secciones obligatorias).

### 11.5 Flags de Calidad
`similarity_used`, `truncated`, `stub_mode`, `specialization_applied`, `generic_feedback`.

### 11.6 Diseño
- Sin reutilización rígida de feedback.
- Estructura opcional (encabezados sólo si agregan valor).
- Sanitización para evitar “referencias” o enlaces.
- Stub claro cuando falta `GOOGLE_API_KEY`.

### 11.7 Limitaciones
- Conteo tokens heurístico.
- Embeddings placeholder (fáciles de reemplazar).
- Similaridad siempre activa (faltaría feature flag dedicado).

### 11.8 Extensiones Implementadas y Pendientes
Implementadas:
- Embeddings reales opcionales + fallback determinista y ranking híbrido (similitud * recency) con MMR.
- Conteo de tokens nativo aproximado (regex palabras + signos) centralizado.
- Flag de configuración `SIMILARITY_ENABLED` para activar/desactivar similaridad.
- Cache LRU (256 entradas) para embeddings de texto.
- Métricas adicionales: `density_chars_per_token`, `lexical_diversity`, `avg_sentence_length`.

Pendientes / Futuras:
- Cache de prompts completos (actualmente sólo embeddings) y respuestas frecuentes.
- Reemplazar heurística de tokens por conteo específico del modelo (si SDK expone endpoint).
- Persistencia y ranking en base de datos con pgvector (evitar carga local de todos los items).
- Métrica de "coherencia evolutiva" entre intentos (delta de errores resueltos).
- Alertas automáticas si `lexical_diversity` < umbral (posible repetición o verborrea).

---

## 12. Futuras Mejoras Generales
- Soft delete, categorías de guías, estadísticas avanzadas.
- Métricas de reintentos y tiempo de resolución.
- Cache distribuido para JWKS.
- Roles o scopes más finos.
- Validadores estructurales avanzados.

