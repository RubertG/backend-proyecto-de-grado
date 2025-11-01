from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8')

    PROJECT_NAME: str = 'Educational Platform API'
    API_V1_STR: str = '/api/v1'
    SUPABASE_URL: str
    SUPABASE_ANON_KEY: str
    SUPABASE_JWT_SECRET: str | None = None  # Se usa para validar HS256 si está disponible
    DEBUG_AUTH: bool = False
    EMBEDDING_MODEL: str = "text-embedding-004"  # Modelo Gemini embedding por defecto
    EMBEDDING_DIM: int | None = None  # Si None se infiere por modelo
    LLM_MODEL: str = "gemini-2.0-flash"  # Modelo conversacional por defecto
    LLM_TEMPERATURE: float = 0.4
    GOOGLE_API_KEY: str | None = None  # Clave para modelos Gemini (opcional)
    # --- Similaridad / embeddings avanzados ---
    SIMILARITY_TOP_K: int = 4
    SIMILARITY_RECENCY_DECAY: float = 0.04  # lambda por hora (e^{-lambda*t})
    SIMILARITY_MMR_LAMBDA: float = 0.65  # trade-off entre relevancia y diversidad
    SIMILARITY_FETCH_LIMIT: int = 200
    SIMILARITY_ENABLED: bool = True
    # --- CORS ---
    FRONTEND_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000"
    ]

@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[arg-type]
