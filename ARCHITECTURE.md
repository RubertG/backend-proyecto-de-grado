# Educational Platform – Backend Architecture Context

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
- **Auth:** **Supabase Auth** (JWT emitido por Supabase); el backend solo valida firma (JWKS) y sincroniza usuario local si falta. No se manejan contraseñas en el backend.
- **Roles:** Guardados en la tabla `users` y/o en `app_metadata.role` dentro de Supabase Auth. El backend prioriza claim de token y persiste en tabla.
- **Feedback automático:** Módulo LLM implementado (`app/llm_feedback/`) con: similitud semántica, prompts especializados, modo stub, lazy init, métricas y endpoint de estado.
- **Infraestructura:** Uvicorn para desarrollo, despliegue en servicios compatibles ASGI

---

## 3. Esquema de la Base de Datos

Véase `educational_platform_schema.sql` para la definición exacta.  
Resumen de tablas y relaciones principales (sin gestión local de contraseñas: Supabase Auth almacena credenciales en su propio esquema interno):

- **users**
  - Campos: id (UUID), name, email, role (admin/student), timestamps
  - Creación: se auto-provisiona un registro local en el primer request autenticado si no existe.
- **guides**
  - Campos: id, title, content_html, order, topic, is_active, timestamps
- **exercises**
  - Campos: id, guide_id, title, content_html, expected_answer, ai_context, type (command/dockerfile/conceptual), **difficulty**, is_active, timestamps
  - Relación: muchos ejercicios por guía (guide_id)
  - **Nuevo:** El campo `difficulty` indica el nivel de dificultad del ejercicio (ejemplo: fácil, medio, difícil).  
- **exercise_attempts**
  - Campos: id, exercise_id, user_id, submitted_answer, structural_validation_passed, llm_feedback, completed, timestamps
  - Relación: muchos intentos por usuario por ejercicio
  - **Nuevo:** El campo `llm_feedback` será generado automáticamente usando modelos LLM mediante LangChain.
- **completed_guides**
  - Campos: id, guide_id, user_id, completed_at
  - Relación: registro de guías completadas por usuario

**Tipos y restricciones**:
- `user_role`: ENUM ('admin', 'student')
- `exercise_type`: ENUM ('command', 'dockerfile', 'conceptual')
- Uso de UUIDs como PK y FK
- ON DELETE CASCADE en relaciones

---

## 4. Estructura de Carpetas del Backend

```
backend/
├── app/
│   ├── api/                # Endpoints FastAPI (routers)
│   │   ├── users.py
│   │   ├── guides.py
│   │   ├── exercises.py
│   │   ├── attempts.py
│   │   └── __init__.py
│   ├── core/               # Configuración, seguridad, utilidades
│   │   ├── config.py
│   │   ├── security.py
│   │   └── __init__.py
│   ├── db/                 # Conexión y queries a la DB
│   │   ├── database.py
│   │   ├── crud.py
│   │   └── __init__.py
│   ├── llm/                # Lógica para feedback automático con LangChain
│   │   ├── feedback.py
│   │   └── __init__.py
│   ├── validators/         # Validación estructural de ejercicios
│   │   ├── dockerfile.py   # Validador estructural para Dockerfile
│   │   ├── command.py      # Validador estructural para comandos normales
│   │   └── __init__.py
│   ├── models/             # Modelos Pydantic (schemas)
│   │   ├── user.py
│   │   ├── guide.py
│   │   ├── exercise.py
│   │   ├── attempt.py
│   │   └── __init__.py
│   ├── main.py             # App principal de FastAPI
│   └── __init__.py
└── requirements.txt
```

---

## 5. Reglas de Negocio

- **Usuarios:**
  - Registro / login se realiza en el frontend usando Supabase Auth (`supabase-js`).
  - El backend recibe `Authorization: Bearer <token>` y valida contra JWKS público de Supabase.
  - Si el usuario no existe en la tabla `users`, se crea automáticamente (auto-provisioning) con rol por defecto `student` salvo que el token incluya `app_metadata.role`.
  - Rol 'admin': crea, edita y elimina guías y ejercicios.
  - Rol 'student': puede leer guías, resolver ejercicios y ver su progreso.
  - El email es único (constraint en DB).
- **Guías:**
  - Ordenadas por campo `order`.
  - Pueden estar activas/inactivas.
- **Ejercicios:**
  - Asociados a una guía.
  - Tienen tipo (`command`, `dockerfile`, `conceptual`).
  - **Tienen dificultad** (`difficulty`: fácil, medio, difícil, etc.).
  - Validación automática posible (campo `structural_validation_passed`, feedback LLM).
  - **El feedback tras un intento se genera automáticamente usando modelos LLM mediante LangChain y se almacena en `llm_feedback`.**
  - **Las buenas prácticas, estilo y uso correcto de herramientas en los ejercicios de código serán evaluados y retroalimentados por el LLM.**
- **Intentos de ejercicio:**
  - Un usuario puede intentar varias veces un ejercicio.
  - Registro de respuesta, validación estructural y feedback.
- **Progreso del usuario:**
  - Se registra en `completed_guides` cuando se termina una guía.

---

## 6. Validación Estructural de Ejercicios

**La validación estructural es obligatoria para los ejercicios de tipo `command` (comandos de terminal) y `dockerfile`.**

- La validación estructural debe implementarse antes de enviar la respuesta al módulo de feedback automático (LLM).
- El resultado (`True`/`False` y mensaje de error opcional) se almacena en el campo `structural_validation_passed` de la tabla `exercise_attempts`.

### a) Ejercicios tipo `command`:
- Implementar un validador estructural que verifique:
  - Que el comando tenga una sintaxis válida (puede apoyarse en `shlex.split` o expresiones regulares).
  - Que el comando pertenezca a una lista permitida (si aplica), o que no contenga sintaxis peligrosa.
  - Opcional: Validar presencia de flags u opciones requeridas.
- El validador debe estar en `app/validators/command.py` y ser fácilmente testeable.

### b) Ejercicios tipo `dockerfile`:
- Implementar un validador estructural que verifique:
  - Que el contenido sea un Dockerfile válido.
  - Utilizar la librería Python [dockerfile-parse](https://github.com/containerbuildsystem/dockerfile-parse) para reducir dependencias externas y facilitar el despliegue en MVPs.
  - El validador debe detectar errores de sintaxis e instrucciones inválidas y retornar el resultado estructural (no semántico).
- El validador debe estar en `app/validators/dockerfile.py` y ser fácilmente testeable.

### c) Ejercicios tipo `conceptual`:
- No requieren validación estructural. El valor de `structural_validation_passed` se puede marcar siempre como `True` para este tipo.

---

## 7. Endpoints Clave

### Autenticación y usuarios
- (Frontend) Signup / login con Supabase Auth (no endpoints propios de registro/login en backend).
- Obtener perfil autenticado: `GET /api/v1/users/me`.
- Listar usuarios (admin): `GET /api/v1/users/`.
  - El backend no expone endpoint de emisión de tokens; solo valida.

### Guías
- CRUD de guías (solo admin)
- Listar guías (todos)
- Consultar guía por id

### Ejercicios
- CRUD de ejercicios (solo admin)
- Listar ejercicios por guía
- Consultar ejercicio por id

### Intentos y progreso
- Enviar intento de ejercicio:
  - Antes de procesar, se ejecuta la validación estructural según el tipo de ejercicio (`command`, `dockerfile`). El resultado se almacena en el registro de intento.
  - Si falla la validación estructural, el intento puede ser rechazado o marcado como inválido según reglas de negocio.
  - El feedback de buenas prácticas y semántica será generado por el LLM y almacenado en `llm_feedback`.
- Obtener intentos previos del usuario actual
- Marcar guía como completada
- Consultar progreso del usuario

---

## 8. Convenciones de Código

- Modelos Pydantic v2 para todas las entidades expuestas en API.
- Endpoints organizados por recurso en `app/api/`.
- Validaciones exhaustivas en modelos y endpoints (campos requeridos, tipos, longitud).
- Dependencias para autenticación (`get_current_user`) y autorización (`require_role`).
- Manejo de errores con HTTPException; se puede centralizar middleware a futuro.
- Respuestas tipadas y documentadas (OpenAPI auto-generado por FastAPI).
- Fechas siempre en UTC (delegado a Postgres `NOW()` / TIMESTAMPTZ).
- Feedback automático y evaluación de buenas prácticas pendiente en `llm/` (no activo todavía).
- Verificación de JWT contra JWKS de Supabase (cache en memoria).
- Los validadores estructurales deben ser modulares, fácilmente testeables y documentados.

---

## 9. Ejemplo de Flujo de Usuario

1. **Signup/Login (frontend):** Usuario se autentica vía Supabase Auth (email/password o proveedores OAuth).
2. **Token:** Frontend envía el access token JWT al backend en cada request protegido.
3. **Auto-provisioning:** Si el usuario no existe en tabla `users`, el backend lo crea (rol por defecto `student`).
4. **Exploración:** Student ve guías, navega contenido.
5. **Resolución de ejercicios:** Student responde ejercicios. El backend realiza la validación estructural automática:
   - Si es tipo `command` o `dockerfile`, valida la estructura y almacena el resultado.
   - Si es tipo `conceptual`, marca como válido por defecto.
   - Posteriormente, el LLM evalúa la respuesta para feedback semántico y buenas prácticas.
6. **Progreso:** Al completar ejercicios de una guía se marca completada.
7. **Admin:** Crea/edita guías y ejercicios, revisa intentos y progreso.

---

## 10. Referencias

- [SQL completo en educational_platform_schema.sql](./educational_platform_schema.sql)
- [Documentación de FastAPI](https://fastapi.tiangolo.com/)
- [Supabase Docs](https://supabase.com/docs)
- [Pydantic v2+ Docs](https://docs.pydantic.dev/)
- [LangChain Docs](https://python.langchain.com/)
- [dockerfile-parse](https://github.com/containerbuildsystem/dockerfile-parse)

---

## 11. Módulo de Feedback LLM

### 11.1 Objetivo
Retroalimentación pedagógica concisa (6–14 líneas) y chat de mejora continua, evitando secciones vacías y enlaces externos.

### 11.2 Componentes
- `feedback_chain.py`: Orquestación del ciclo completo (intento y chat).
- `prompt_builder.py`: Prompt especializado por tipo + truncado progresivo (budget ~6000 chars).
- `postprocess.py`: `normalize_output` (remueve encabezados vacíos) + sanitización de enlaces/citas.
- `vector_store.py`: Memoria de intentos/feedback conversacional; similaridad con embeddings y ranking híbrido.
- `metrics.py`: Latencia, tokens aproximados, quality_flags y métricas de densidad/legibilidad.
- `llm_status.py`: Estado interno expuesto (`/llm/status`).

### 11.3 Flujo de Intento
1. Recuperar ejercicio y guía.
2. Recolectar intentos previos, feedback previo, diálogo reciente.
3. Construir prompt especializado y truncar si excede límite.
4. (Opcional) Enriquecer con similaridad (si `SIMILARITY_ENABLED`).
5. Invocar LLM (o stub si falta clave) con lazy re-init.
6. Normalizar salida, sanitizar enlaces y marcar flags.
7. Persistir intento, feedback, métricas y embeddings.

### 11.4 Chat
Historial condensado + similaridad opcional. Respuesta reducida (≤8 líneas) en `content_md`.

### 11.5 Flags de Calidad
`similarity_used`, `truncated`, `stub_mode`, `specialization_applied`, `generic_feedback`.

### 11.6 Diseño
- Sin reutilización rígida de feedback previo.
- Estructura flexible (encabezados solo si aportan valor real).
- Eliminación de enlaces y referencias externas.
- Modo stub claro si no hay `GOOGLE_API_KEY`.
- Lazy init para reconectar cuando aparece la clave.

### 11.7 Limitaciones Actuales
- Conteo de tokens aproximado (regex, no tokenizador real del modelo).
- Embeddings Gemini opcionales; fallback determinista (no semántica “real” en modo sin API key).
- Ranking en memoria (no pgvector todavía) y carga local hasta `SIMILARITY_FETCH_LIMIT`.
- Sin cache de prompts/respuestas completas (solo embeddings LRU).

### 11.8 Extensiones Implementadas y Pendientes
Implementadas:
- Embeddings reales opcionales + fallback determinista y ranking híbrido (similitud * recency) con MMR.
- Conteo de tokens nativo aproximado (regex palabras + signos) centralizado.
- Flag de configuración `SIMILARITY_ENABLED` para activar/desactivar similaridad.
- Cache LRU (256 entradas) para embeddings de texto.
- Métricas adicionales: `density_chars_per_token`, `lexical_diversity`, `avg_sentence_length`.

Pendientes / Futuras:
- Cache de prompts completos y respuestas frecuentes.
- Conteo específico del modelo si SDK expone endpoint.
- Persistencia y ranking en base de datos con pgvector.
- Métrica de "coherencia evolutiva" entre intentos.
- Alertas automáticas por baja diversidad léxica.

## 12. Futuras Mejoras Generales
- Soft delete, categorías de guías, estadísticas avanzadas.
- Métricas de reintentos y tiempo de resolución.
- Cache distribuido para JWKS.
- Roles / scopes más finos.
- Validadores estructurales enriquecidos (reglas adicionales y sugerencias contextuales).
