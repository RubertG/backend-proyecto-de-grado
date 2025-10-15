# Backend – Arquitectura Completa (API + Módulo LLM)

## 1. Objetivo General
Plataforma educativa para practicar y evaluar conocimientos técnicos mediante guías y ejercicios con retroalimentación automática impulsada por LLM. Soporta iteración (intentos múltiples), validación estructural previa (para ejercicios técnicos) y feedback pedagógico adaptativo.

## 2. Visión de Alto Nivel
- Capa de **autenticación delegada** a Supabase Auth.
- **API REST** con FastAPI para CRUD de contenido y gestión de intentos/progreso.
- **Módulo LLM** para generar feedback y chat contextual, con memoria vectorial ligera y métricas.
- Persistencia en Postgres (Supabase) con RLS.

## 3. Stack Tecnológico
| Área | Tecnología |
|------|------------|
| Backend | FastAPI (Python 3.12+) |
| DB | Supabase (PostgreSQL + RLS) |
| Auth | Supabase Auth (JWT) |
| Frontend (consumidor) | Next.js (TypeScript) |
| LLM | Gemini vía LangChain + wrapper personalizado |
| Embeddings | Gemini Embeddings (opcional) / Fallback determinista |
| Infra | Uvicorn (ASGI) |

## 4. Esquema de Datos (Resumen)
Tablas principales (ver `educational_platform_schema.sql` para detalle):
- `users (id, name, email, role)`
- `guides (title, topic, content_html, order, is_active)`
- `exercises (guide_id, title, content_html, expected_answer, ai_context, type, difficulty, enable_structural_validation, enable_llm_feedback)`
- `exercise_attempts (exercise_id, user_id, submitted_answer, structural_validation_passed, llm_feedback, completed)`
- `completed_guides (guide_id, user_id, completed_at)`
- `llm_metrics (attempt_id, exercise_id, user_id, model, prompt_tokens, completion_tokens, latency_ms, quality_flags)`
- `exercise_conversation_vectors (embedding, content, type, attempt_id, user_id, exercise_id)`

## 5. Roles y Seguridad
- Roles: `admin` y `student`.
- Auto-provisioning: primer request autenticado crea registro en `users` si no existe.
- RLS en Supabase asegura aislamiento por `user_id` donde aplica.
- Back aplica verificación de firma JWT (JWKS) y lectura de claims.

## 6. Flujo de Intento de Ejercicio
1. Cliente envía intento (`submitted_answer`).
2. API valida existencia del ejercicio y su configuración.
3. Si `enable_structural_validation` y tipo ∈ {`command`,`dockerfile`}: ejecuta validador estructural:
   - `command`: parseo sintáctico, flags prohibidos.
   - `dockerfile`: análisis con `dockerfile-parse`.
4. Guarda intento base.
5. Si `enable_llm_feedback`: invoca módulo LLM → genera `content_md` y métricas.
6. Persistencia de métrica y embeddings (memoria vectorial).

## 7. Módulo LLM – Componentes
| Archivo | Rol |
|---------|-----|
| `feedback_chain.py` | Orquestación intento/chat, invoca LLM y gestiona vectores. |
| `prompt_builder.py` | Prompt especializado (command/dockerfile/conceptual) + truncado progresivo. |
| `postprocess.py` | Normalización y sanitización (sin enlaces ni referencias). |
| `vector_store.py` | Embeddings + ranking híbrido (similitud * recency) + MMR + cache LRU. |
| `metrics.py` | Registro de latencia, tokens aproximados y métricas lingüísticas. |
| `llm_status.py` | Endpoint de introspección `/llm/status`. |

## 8. Generación de Prompt
Estrategia de truncado incremental (presupuesto ~6000 chars). Se prioriza: definición de ejercicio, últimos intentos, feedback previo. Especialización por tipo incluye criterios pedagógicos diferenciales.

## 9. Enriquecimiento Contextual (Similaridad)
- Embeddings (Gemini si hay API key; fallback determinista en stub).
- Recency decay exponencial: `score_hybrid = cosine * exp(-λ * horas)`.
- MMR para diversidad (`SIMILARITY_MMR_LAMBDA`).
- Controlado por `SIMILARITY_ENABLED` y `SIMILARITY_TOP_K`.

## 10. Flags y Métricas
- Flags: `similarity_used`, `truncated`, `stub_mode`, `specialization_applied`, `generic_feedback`.
- Conteo tokens aproximado (regex). Métricas extra: `density_chars_per_token`, `lexical_diversity`, `avg_sentence_length`.
- Persistencia en `llm_metrics` + buffer en memoria.

## 11. Chat Contextual
- Usa historial condensado (últimas N interacciones) + similaridad opcional.
- Respuestas concisas (≤8 líneas) en Markdown.

## 12. Configuración (Variables Clave)
| Variable | Descripción |
|----------|-------------|
| `GOOGLE_API_KEY` | Clave Gemini (activa LLM y embeddings reales). |
| `LLM_MODEL` / `LLM_TEMPERATURE` | Modelo y temperatura. |
| `EMBEDDING_MODEL` / `EMBEDDING_DIM` | Modelo y dimensión embeddings. |
| `SIMILARITY_ENABLED` | Activa/desactiva enriquecimiento semántico. |
| `SIMILARITY_TOP_K` | Nº máximo de fragmentos similares. |
| `SIMILARITY_RECENCY_DECAY` | Lambda de decaimiento temporal. |
| `SIMILARITY_MMR_LAMBDA` | Balance relevancia/diversidad. |
| `SIMILARITY_FETCH_LIMIT` | Límite de items cargados para ranking local. |

## 13. Limitaciones Actuales
- Tokenización aproximada (no exact tokenizer del modelo).
- Ranking local (no pgvector todavía).
- Fallback embeddings no semántico en ausencia de API key.
- Sin cache de prompts completos (solo embeddings LRU).

## 14. Extensiones Implementadas
- Embeddings reales opcionales + ranking híbrido + MMR.
- Token counting aproximado unificado.
- Flag de similaridad + parámetros afinables.
- Cache LRU de embeddings.
- Métricas de densidad y diversidad léxica.

## 15. Extensiones Pendientes
- Cache de prompts/respuestas completas.
- Migración a pgvector para ranking en DB.
- Métrica de coherencia evolutiva (delta de errores resueltos).
- Token counting específico del modelo (API). 
- Alertas automáticas (diversidad léxica baja).

## 16. Endpoints (Resumen Rápido)
Ver README de endpoints para detalle de payloads.
- `/users/me`, `/users/` (admin)
- `/guides/*`
- `/exercises/*`
- `/attempts/*`
- `/feedback/attempt`, `/feedback/chat`, `/feedback/history`
- `/progress/complete`, `/progress/completed`
- `/llm/status`

## 17. Flujo de Observabilidad
1. Llamada genera métricas locales (`metrics.py`).
2. Persistencia en `llm_metrics` (DB) para análisis consultable.
3. Endpoint `/llm/status` expone estado (stub, modelo, lazy attempts).

## 18. Estrategia de Calidad
- Validadores estructurales previos reducen basura al LLM.
- Similaridad enfocada minimiza tokens y repeticiones.
- Normalización de salida evita secciones vacías y referencias externas.
- Métricas lingüísticas para monitorizar densidad / legibilidad.

## 19. Riesgos y Mitigaciones
| Riesgo | Mitigación |
|--------|-----------|
| LLM sin clave | Modo stub + lazy init periódico. |
| Respuestas genéricas | Prompts especializados + similaridad. |
| Crecimiento de historial | Truncado progresivo + top K similares. |
| Redundancia contextual | MMR reduce duplicados. |
| Verborrea | Monitoreo densidad y longitud media oración. |

## 20. Pasos Futuro Cercano
1. Integrar pgvector para ranking server-side.
2. Cache prompts/outputs hash → respuesta idéntica.
3. Umbrales y alertas automáticas (diversidad baja / densidad alta).
4. Token counting real (dependiente de SDK). 

---
Documento vivo. Actualiza esta fuente en lugar de documentos paralelos para evitar desincronización.
