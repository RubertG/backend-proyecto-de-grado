CREATE TYPE user_role AS ENUM ('admin', 'student');
CREATE TYPE exercise_type AS ENUM ('command', 'dockerfile', 'conceptual');

-- Habilita la extensión vector para embeddings semánticos (si aún no está activa)
CREATE EXTENSION IF NOT EXISTS vector;

-- Tipos existentes
CREATE TYPE user_role AS ENUM ('admin', 'student');
CREATE TYPE exercise_type AS ENUM ('command', 'dockerfile', 'conceptual');

-- Tabla de usuarios
CREATE TABLE IF NOT EXISTS public.users (
	id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
	name TEXT NOT NULL,
	email TEXT UNIQUE NOT NULL,
	role user_role NOT NULL,
	created_at TIMESTAMPTZ DEFAULT NOW(),
	updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Tabla de guías
CREATE TABLE IF NOT EXISTS public.guides (
	id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
	title TEXT NOT NULL,
	content_html TEXT,
	"order" INTEGER NOT NULL,
	topic TEXT,
	is_active BOOLEAN DEFAULT TRUE,
	created_at TIMESTAMPTZ DEFAULT NOW(),
	updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Tabla de ejercicios
CREATE TABLE IF NOT EXISTS public.exercises (
	id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
	guide_id UUID REFERENCES guides(id) ON DELETE CASCADE,
	title TEXT NOT NULL,
	content_html TEXT,
	difficulty TEXT NOT NULL,
	expected_answer TEXT NOT NULL,
	ai_context TEXT,
	type exercise_type NOT NULL,
	enable_structural_validation BOOLEAN NOT NULL DEFAULT TRUE,
	enable_llm_feedback BOOLEAN NOT NULL DEFAULT TRUE,
	is_active BOOLEAN DEFAULT TRUE,
	created_at TIMESTAMPTZ DEFAULT NOW(),
	updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Tabla de intentos de ejercicios
CREATE TABLE IF NOT EXISTS public.exercise_attempts (
	id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
	exercise_id UUID REFERENCES exercises(id) ON DELETE CASCADE,
	user_id UUID REFERENCES users(id) ON DELETE CASCADE,
	submitted_answer TEXT,
	structural_validation_passed BOOLEAN,
	llm_feedback TEXT,
	completed BOOLEAN DEFAULT FALSE,
	created_at TIMESTAMPTZ DEFAULT NOW(),
	updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Tabla de guías completadas
CREATE TABLE IF NOT EXISTS public.completed_guides (
	id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
	guide_id UUID REFERENCES guides(id) ON DELETE CASCADE,
	user_id UUID REFERENCES users(id) ON DELETE CASCADE,
	completed_at TIMESTAMPTZ DEFAULT NOW()
);

-- NUEVA TABLA: Conversación semántica por ejercicio (memoria vectorial)
CREATE TABLE IF NOT EXISTS public.exercise_conversation_vectors (
	id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
	user_id UUID REFERENCES users(id) ON DELETE CASCADE,
	exercise_id UUID REFERENCES exercises(id) ON DELETE CASCADE,
	attempt_id UUID REFERENCES exercise_attempts(id) ON DELETE CASCADE,
	type TEXT, -- 'attempt', 'feedback', 'question', 'answer'
	content TEXT,
	embedding vector(1536), -- Cambia el tamaño si tu modelo de embedding es diferente
	created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Tabla de métricas de llamadas LLM
CREATE TABLE IF NOT EXISTS public.llm_metrics (
	id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
	user_id UUID REFERENCES users(id) ON DELETE CASCADE,
	exercise_id UUID REFERENCES exercises(id) ON DELETE CASCADE,
	attempt_id UUID REFERENCES exercise_attempts(id) ON DELETE SET NULL,
	model TEXT,
	prompt_tokens INTEGER,
	completion_tokens INTEGER,
	latency_ms DOUBLE PRECISION,
	quality_flags JSONB,
	created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Si necesitas actualizar una tabla existente para agregar algún campo, usa ALTER TABLE. 
-- Ejemplo: ALTER TABLE exercise_attempts ADD COLUMN nuevo_campo TEXT;
-- (En este caso, no se requiere editar las existentes, solo agregar la nueva tabla para memoria vectorial.)