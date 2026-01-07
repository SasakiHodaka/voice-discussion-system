"""Application configuration."""

import os
from typing import List
from pydantic_settings import BaseSettings


class ServerSettings(BaseSettings):
    """Server configuration."""

    host: str = "127.0.0.1"
    port: int = 8000
    reload: bool = False
    workers: int = 1


class LLMSettings(BaseSettings):
    """LLM configuration."""

    provider: str = "openai"
    api_key: str = ""
    model: str = "gpt-4o-mini"
    temperature: float = 0.7
    max_tokens: int = 1024


class ASRSettings(BaseSettings):
    """Speech Recognition configuration."""

    service_uri: str = "http://localhost:50051"
    enabled: bool = True
    timeout_sec: int = 30


class SessionSettings(BaseSettings):
    """Session configuration."""

    timeout_minutes: int = 60
    max_participants: int = 20
    max_discussions: int = 100


class AnalysisSettings(BaseSettings):
    """Analysis configuration."""

    segment_length_sec: float = 20.0
    min_chars_for_evaluation: int = 40
    enable_issue_mapping: bool = True


class Settings(BaseSettings):
    """Application settings."""

    # Server
    server: ServerSettings = ServerSettings()

    # LLM
    llm: LLMSettings = LLMSettings()

    # ASR
    asr: ASRSettings = ASRSettings()

    # Session
    session: SessionSettings = SessionSettings()

    # Analysis
    analysis: AnalysisSettings = AnalysisSettings()

    # Frontend
    spa_path: str = "../frontend/dist"
    enable_cors: bool = True
    cors_origins: List[str] = ["*"]

    class Config:
        case_sensitive = False


# Global settings instance
settings = Settings(
    llm=LLMSettings(api_key=os.getenv("OPENAI_API_KEY", "sk-test-key"))
)
