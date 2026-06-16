"""
Configurações do agente financeiro.

Invariante: a fila de debounce e o estado de confirmação são mantidos em memória
no processo. Isso exige EXATAMENTE 1 worker Uvicorn/Gunicorn. Com múltiplos workers
o estado in-process diverge entre processos e o comportamento é incorreto.
"""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # --- infraestrutura ---
    DATABASE_URL: str
    OPENAI_API_KEY: str
    EVOLUTION_API_URL: str
    EVOLUTION_INSTANCE: str
    EVOLUTION_API_KEY: str

    # --- obrigatórios sem default ---
    # AGENTE_USUARIO_EMAIL: mantido no Settings para não quebrar .env legado;
    # não é mais usado no fluxo do agente (substituído por resolução in-process no webhook).
    AGENTE_USUARIO_EMAIL: str
    RESPONSAVEL_PADRAO: str
    WEBHOOK_APIKEY: str
    REDIS_URL: str

    # --- opcionais com defaults ---
    TIMEZONE_USUARIO: str = "America/Sao_Paulo"
    DEBOUNCE_SEGUNDOS: int = Field(default=5, ge=1)
    CONFIANCA_MINIMA: float = Field(default=0.7, ge=0.0, le=1.0)

    # Histórico de conversa
    HISTORICO_MAX_MENSAGENS: int = Field(default=10, ge=1)
    HISTORICO_TTL_HORAS: int = Field(default=2, ge=1)

    # RAG / busca semântica
    RAG_PISO: float = Field(default=1.0, ge=0.0)
    RAG_MARGEM: float = Field(default=0.15, ge=0.0)
    RAG_MAX_OPCOES: int = Field(default=5, ge=1)

    # LLM
    LLM_MODELO_CLASSIFICACAO: str = "gpt-4o-mini"
    LLM_MODELO_CONVERSAR: str = "gpt-4o"


settings = Settings()
