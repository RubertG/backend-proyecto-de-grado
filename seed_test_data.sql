-- Seed de datos de prueba para validación estructural
-- Ejecutar esto en el editor SQL de Supabase (o psql) DESPUÉS de crear las tablas.
-- Ajusta los UUID si ya existen conflictos.

-- Limpieza opcional (cuidado en ambientes compartidos)
-- DELETE FROM exercise_attempts;
-- DELETE FROM exercises;
-- DELETE FROM guides;

INSERT INTO public.guides (id, title, content_html, "order", topic, is_active) VALUES
  ('11111111-1111-1111-1111-111111111111', 'CLI Básico', '<p>Guía de comandos básicos.</p>', 1, 'cli', TRUE),
  ('22222222-2222-2222-2222-222222222222', 'Docker Fundamentos', '<p>Introducción a Docker y construcción de imágenes.</p>', 2, 'docker', TRUE),
  ('33333333-3333-3333-3333-333333333333', 'Conceptos de Contenedores', '<p>Conceptos clave sobre contenedores e imágenes.</p>', 3, 'docker', TRUE);

-- Ejercicios de tipo command
INSERT INTO public.exercises (
  id, guide_id, title, content_html, difficulty, expected_answer, ai_context, type, is_active, enable_structural_validation, enable_llm_feedback
) VALUES
  ('aaaaaaa1-0000-0000-0000-000000000001', '11111111-1111-1111-1111-111111111111',
    'Listado de archivos',
    '<p>Escribe un comando que liste archivos del directorio actual.</p>',
    'easy',
    'ls -la',
    'Contexto IA opcional',
    'command',
    TRUE, TRUE, TRUE),
  ('aaaaaaa1-0000-0000-0000-000000000002', '11111111-1111-1111-1111-111111111111',
    'Mostrar versión de Docker',
    '<p>Comando para ver la versión de Docker instalada.</p>',
    'easy',
    'docker --version',
    NULL,
    'command',
    TRUE, TRUE, TRUE);

-- Ejercicios de tipo dockerfile
INSERT INTO public.exercises (
  id, guide_id, title, content_html, difficulty, expected_answer, ai_context, type, is_active, enable_structural_validation, enable_llm_feedback
) VALUES
  ('bbbbbbb1-0000-0000-0000-000000000001', '22222222-2222-2222-2222-222222222222',
    'Dockerfile Python FastAPI',
    '<p>Crea un Dockerfile mínimo que ejecute una app FastAPI.</p>',
    'medium',
    'FROM python:3.12-slim\nWORKDIR /app\nCOPY requirements.txt .\nRUN pip install -r requirements.txt\nCOPY . .\nCMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]',
    'Usar imagen slim y uvicorn',
    'dockerfile',
    TRUE, TRUE, TRUE),
  ('bbbbbbb1-0000-0000-0000-000000000002', '22222222-2222-2222-2222-222222222222',
    'Dockerfile con multi-stage (opcional)',
    '<p>Un Dockerfile multi-stage simple.</p>',
    'hard',
    'FROM node:20-alpine as build\nWORKDIR /app\nCOPY package*.json ./\nRUN npm ci\nCOPY . .\nRUN npm run build\nFROM nginx:alpine\nCOPY --from=build /app/dist /usr/share/nginx/html',
    NULL,
    'dockerfile',
    TRUE, TRUE, TRUE);

INSERT INTO public.exercises (
  id, guide_id, title, content_html, difficulty, expected_answer, ai_context, type, is_active, enable_structural_validation, enable_llm_feedback
) VALUES
  ('ccccccc1-0000-0000-0000-000000000001', '11111111-1111-1111-1111-111111111111',
    'Pregunta conceptual sobre contenedores',
    '<p>¿Qué diferencia hay entre una imagen y un contenedor?</p>',
    'easy',
    'Una imagen es una plantilla inmutable; un contenedor es una instancia en ejecución de una imagen.',
    NULL,
    'conceptual',
    TRUE, TRUE, TRUE);

-- Ejercicios conceptuales extra para la tercera guía
INSERT INTO public.exercises (
  id, guide_id, title, content_html, difficulty, expected_answer, ai_context, type, is_active, enable_structural_validation, enable_llm_feedback
) VALUES
  ('ccccccc1-0000-0000-0000-000000000002', '33333333-3333-3333-3333-333333333333',
    '¿Qué es una capa (layer) en una imagen?',
    '<p>Explica brevemente qué representa una capa dentro de una imagen.</p>',
    'easy',
    'Una capa es un conjunto de cambios (filesystem diff) apilados; cada instrucción genera una nueva capa inmutable.',
    NULL,
    'conceptual',
    TRUE, TRUE, TRUE),
  ('ccccccc1-0000-0000-0000-000000000003', '33333333-3333-3333-3333-333333333333',
    'Ventajas de multi-stage builds',
    '<p>Menciona una ventaja de usar multi-stage builds.</p>',
    'easy',
    'Reducir el tamaño final de la imagen al copiar solo artefactos necesarios.',
    NULL,
    'conceptual',
    TRUE, TRUE, TRUE);

-- Attempts de ejemplo (schema orientativo: id, exercise_id, user_id, submitted_answer, completed, structural_validation_passed, llm_feedback)
-- Nota: Ajusta nombres de columnas según tu schema real en exercise_attempts
-- Intento conceptual (se marca completed=true automáticamente por la lógica backend)
INSERT INTO public.exercise_attempts (
  id, exercise_id, user_id, submitted_answer, completed, structural_validation_passed, llm_feedback
) VALUES
  ('att11111-0000-0000-0000-000000000001', 'ccccccc1-0000-0000-0000-000000000001', 'test-user-0000-0000-0000-000000000001', 'Una imagen es una plantilla...', TRUE, TRUE, '## Fortalezas\n- Respuesta clara');

-- Intento command válido (pero aún no marcado completed si la lógica requiere validación estructural explícita en tiempo real)
INSERT INTO public.exercise_attempts (
  id, exercise_id, user_id, submitted_answer, completed, structural_validation_passed, llm_feedback
) VALUES
  ('att22222-0000-0000-0000-000000000001', 'aaaaaaa1-0000-0000-0000-000000000001', 'test-user-0000-0000-0000-000000000001', 'ls -la', TRUE, TRUE, '## Oportunidades\n- Podrías filtrar.');

-- Intento dockerfile incompleto (no completado todavía)
INSERT INTO public.exercise_attempts (
  id, exercise_id, user_id, submitted_answer, completed, structural_validation_passed, llm_feedback
) VALUES
  ('att33333-0000-0000-0000-000000000001', 'bbbbbbb1-0000-0000-0000-000000000001', 'test-user-0000-0000-0000-000000000001', 'FROM python:3.12-slim', FALSE, TRUE, NULL);

-- Guía completada manualmente (CLI Básico) si todos sus ejercicios están completos (ajusta según attempts reales)
INSERT INTO public.completed_guides (id, guide_id, user_id) VALUES
  ('comp1111-0000-0000-0000-000000000001', '11111111-1111-1111-1111-111111111111', 'test-user-0000-0000-0000-000000000001');

-- SELECT * FROM exercise_attempts LIMIT 10;
-- SELECT * FROM completed_guides LIMIT 10;
