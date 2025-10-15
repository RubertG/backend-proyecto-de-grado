# Arquitectura del Módulo de Feedback Automático con LLM

Este módulo genera retroalimentación educativa y constructiva para los intentos de ejercicios, usando un LLM integrado vía LangChain (modelo por defecto: Gemini 2.5, fácilmente migrable).  
Incluye memoria conversacional usando vectores (embedding size configurable según modelo de embeddings elegido) y soporte para diálogo interactivo.

---

## 1. **Requerimientos Clave**

- **Modularidad y abstracción:** Cambia el LLM fácilmente (Gemini, GPT, Claude, etc.) sin modificar lógica central.
- **Contexto óptimo:** El LLM recibe:
  - Guía y ejercicio (título, descripción, tipo, dificultad, respuesta esperada).
  - Respuestas actuales y previas del usuario en ese ejercicio.
  - Feedback anterior y preguntas/respuestas adicionales (diálogo).
  - Idioma español siempre.
- **Prompt engineering:** Prompts educativos y motivadores, adaptados al nivel y tipo de ejercicio.
- **Post-procesamiento:** Feedback estructurado en formato Markdown (`.md`) con secciones claras (fortalezas, errores, consejos, pregunta de seguimiento, recursos).  
  - **En la API:** El feedback se entrega como un solo string en formato Markdown, sin separar en campos.  
  - **En el Frontend:** Se parsea el Markdown, mostrando las secciones con estilo y permitiendo animaciones tipo "máquina de escribir" (efecto ChatGPT).
- **Logging y métricas:** Registra prompts, respuestas, tiempos, tokens, errores y calidad de feedback.
- **Memoria vectorial:** Cada intento, feedback, pregunta y respuesta se embebe y almacena en vector store (embedding size configurable).
- **Preguntas de seguimiento:** El LLM sugiere preguntas para profundizar/reflexionar.
- **Diálogo interactivo:** El usuario puede preguntar sobre el ejercicio/feedback y el sistema responde contextualizando el historial relevante.

---

## 2. **Configuración de embeddings**

- El tamaño de la columna `embedding vector(X)` debe coincidir con el modelo de embedding que uses:
  - **OpenAI:** 1536
  - **HuggingFace MiniLM:** 384
  - **HuggingFace BGE:** 768 o 1024
  - **Gemini:** Ajustar si Google lanza embeddings
- El backend debe poder cambiar el modelo de embeddings y el tamaño del vector fácilmente.

---

## 3. **Feedback según tipo de ejercicio**

- Para ejercicios **conceptuales y abiertos**: feedback completo y educativo.
- Para ejercicios **cerrados** (opciones, selección, etc.): feedback configurable (solo corrección, sugerencias breves, recursos).
- Permitir configurar el nivel de feedback por tipo de ejercicio en el backend.

---

## 4. **Estructura y Componentes**

```
backend/
└── app/
    └── llm_feedback/
        ├── feedback_chain.py       # Flujo principal de feedback
        ├── prompt_builder.py       # Genera prompts educativos con contexto
        ├── postprocess.py          # Estructura y limpia output del LLM
        ├── metrics.py              # Logging y métricas
        ├── vector_store.py         # Memoria vectorial integrada con Supabase
        └── dialog_chain.py         # Soporte de diálogo interactivo
```

---

## 5. **Flujo completo**

1. Obtén el contexto (guía, ejercicio, historial, tipo de ejercicio).
2. Construye el prompt educativo y estructurado.
3. Llama al LLM vía LangChain (modelo configurable, por defecto Gemini 2.5).
4. Post-procesa el output.
    - El output del LLM debe ser un string Markdown con secciones:
      - ## Fortalezas
      - ## Errores
      - ## Consejos de mejora
      - ## Pregunta de seguimiento
      - ## Recursos
    - El backend no separa en campos, solo entrega el Markdown.
5. Guarda feedback y embeddings.
6. Loguea métricas y calidad.
7. Soporta preguntas de seguimiento y diálogo interactivo.

---

## 6. **Formato recomendado para el prompt y respuesta**

Solicita al LLM que devuelva la respuesta estructurada en Markdown, por ejemplo:

```python
prompt = f"""
Eres un asistente educativo experto en tecnología.
Guía:
Título: {guide_title}
Objetivos: {guide_objectives}
Tema: {guide_topic}
Ejercicio:
Título: {exercise_title}
Descripción: {exercise_content}
Tipo: {exercise_type}
Dificultad: {exercise_difficulty}
Respuesta esperada: {expected_answer}
Intentos previos relevantes del usuario: {relevant_attempts}
Feedback previo: {previous_feedback}
Preguntas previas del usuario: {previous_questions}
Respuestas previas del asistente: {previous_answers}
Respuesta actual del usuario:
{user_answer}

Proporciona feedback educativo en español, usando el siguiente formato Markdown, con secciones claras:

## Fortalezas
(Lista de aciertos y aspectos positivos del usuario)

## Errores
(Lista de errores, omisiones, o conceptos a mejorar)

## Consejos de mejora
(Sugerencias para mejorar la respuesta)

## Pregunta de seguimiento
(Una pregunta para que el usuario reflexione o profundice)

## Recursos
(Lista de enlaces, libros o recursos útiles)
"""
```

---

## 7. **Notas para Frontend**

- Parsear Markdown y mostrar secciones con estilo.
- Animación tipo “máquina de escribir” se implementa en el frontend (React, Vue, etc.).
- El feedback llega como un solo string Markdown desde la API.

---

## 8. **Notas generales**

- El backend nunca separa el feedback en campos, solo entrega el Markdown estructurado.
- El tamaño de embeddings debe ser configurable y acorde al modelo elegido.
- El feedback puede ser adaptativo según el tipo de ejercicio y necesidades pedagógicas.

---

## 9. **Endpoints de API sugeridos**

Para cubrir todas las acciones de feedback y conversación, implementa los siguientes endpoints:

### 9.1. **Recibir intento y generar feedback**
- `POST /api/feedback/attempt`
  - **Input:**  
    - `exercise_id` (UUID)
    - `user_id` (UUID)
    - `submitted_answer` (string)
  - **Output:**  
    - `feedback_md` (string, Markdown estructurado)
    - `attempt_id` (UUID, si se crea el intento)
  - **Acciones:**  
    - Guarda el intento y el feedback en la base y en vector store.

### 9.2. **Seguir hablando (conversación/chat sobre ejercicio/feedback)**
- `POST /api/feedback/chat`
  - **Input:**  
    - `exercise_id` (UUID)
    - `user_id` (UUID)
    - `attempt_id` (UUID, opcional para asociar al intento)
    - `message` (string, pregunta o comentario del usuario)
  - **Output:**  
    - `reply_md` (string, respuesta del LLM en Markdown)
    - `chat_message_id` (UUID o timestamp)
  - **Acciones:**  
    - Recupera el historial relevante (de vector store).
    - Envía el mensaje al LLM junto al contexto.
    - Guarda pregunta y respuesta en memoria vectorial.

### 9.3. **Obtener historial de conversación y feedback**
- `GET /api/feedback/history`
  - **Input:**  
    - `exercise_id` (UUID)
    - `user_id` (UUID)
    - Opcional: `attempt_id` (UUID)
  - **Output:**  
    - Lista de mensajes:  
      - `type` ('attempt', 'feedback', 'question', 'answer')
      - `content_md` (string, Markdown)
      - `timestamp`
  - **Acciones:**  
    - Recupera historial relevante y lo devuelve ordenado.

---

**Define los parámetros, formatos y lógica según las necesidades del frontend y la arquitectura.  
Si alguna acción requiere endpoint adicional, justifica y sugiere su implementación.**