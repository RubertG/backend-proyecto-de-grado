-- WARNING: This schema is for context only and is not meant to be run.
-- Table order and constraints may not be valid for execution.

CREATE TABLE public.completed_guides (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  guide_id uuid,
  user_id uuid,
  completed_at timestamp with time zone DEFAULT now(),
  CONSTRAINT completed_guides_pkey PRIMARY KEY (id),
  CONSTRAINT completed_guides_guide_id_fkey FOREIGN KEY (guide_id) REFERENCES public.guides(id),
  CONSTRAINT completed_guides_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id)
);
CREATE TABLE public.exercise_attempts (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  exercise_id uuid,
  user_id uuid,
  submitted_answer text,
  structural_validation_passed boolean,
  llm_feedback text,
  completed boolean DEFAULT false,
  created_at timestamp with time zone DEFAULT now(),
  updated_at timestamp with time zone DEFAULT now(),
  CONSTRAINT exercise_attempts_pkey PRIMARY KEY (id),
  CONSTRAINT exercise_attempts_exercise_id_fkey FOREIGN KEY (exercise_id) REFERENCES public.exercises(id),
  CONSTRAINT exercise_attempts_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id)
);
CREATE TABLE public.exercise_conversation_vectors (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  user_id uuid,
  exercise_id uuid,
  attempt_id uuid,
  type text,
  content text,
  embedding USER-DEFINED,
  created_at timestamp with time zone DEFAULT now(),
  CONSTRAINT exercise_conversation_vectors_pkey PRIMARY KEY (id),
  CONSTRAINT exercise_conversation_vectors_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id),
  CONSTRAINT exercise_conversation_vectors_exercise_id_fkey FOREIGN KEY (exercise_id) REFERENCES public.exercises(id),
  CONSTRAINT exercise_conversation_vectors_attempt_id_fkey FOREIGN KEY (attempt_id) REFERENCES public.exercise_attempts(id)
);
CREATE TABLE public.exercises (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  guide_id uuid,
  title text NOT NULL,
  content_html text,
  expected_answer text NOT NULL,
  ai_context text,
  type USER-DEFINED NOT NULL,
  is_active boolean DEFAULT true,
  created_at timestamp with time zone DEFAULT now(),
  updated_at timestamp with time zone DEFAULT now(),
  difficulty text,
  enable_structural_validation boolean NOT NULL DEFAULT true,
  enable_llm_feedback boolean NOT NULL DEFAULT true,
  CONSTRAINT exercises_pkey PRIMARY KEY (id),
  CONSTRAINT exercises_guide_id_fkey FOREIGN KEY (guide_id) REFERENCES public.guides(id)
);
CREATE TABLE public.guides (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  title text NOT NULL,
  content_html text,
  order integer NOT NULL,
  topic text,
  is_active boolean DEFAULT true,
  created_at timestamp with time zone DEFAULT now(),
  updated_at timestamp with time zone DEFAULT now(),
  CONSTRAINT guides_pkey PRIMARY KEY (id)
);
CREATE TABLE public.llm_metrics (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  user_id uuid,
  exercise_id uuid,
  attempt_id uuid,
  model text,
  prompt_tokens integer,
  completion_tokens integer,
  latency_ms double precision,
  quality_flags jsonb,
  created_at timestamp with time zone DEFAULT now(),
  CONSTRAINT llm_metrics_pkey PRIMARY KEY (id),
  CONSTRAINT llm_metrics_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id),
  CONSTRAINT llm_metrics_exercise_id_fkey FOREIGN KEY (exercise_id) REFERENCES public.exercises(id),
  CONSTRAINT llm_metrics_attempt_id_fkey FOREIGN KEY (attempt_id) REFERENCES public.exercise_attempts(id)
);
CREATE TABLE public.users (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  name text NOT NULL,
  email text NOT NULL UNIQUE,
  role USER-DEFINED NOT NULL,
  created_at timestamp with time zone DEFAULT now(),
  updated_at timestamp with time zone DEFAULT now(),
  CONSTRAINT users_pkey PRIMARY KEY (id)
);