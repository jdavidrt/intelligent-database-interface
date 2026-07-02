"""Centralised settings for the IDI backend."""

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
import os


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # llama.cpp
    llama_cpp_server_url: str = Field(
        default="http://localhost:7860/v1/chat/completions",
        alias="LLAMA_CPP_SERVER_URL",
    )
    llama_cpp_port: int = Field(default=7860, alias="LLAMA_CPP_SERVER_PORT")

    # Connector selection: "file" (Days 1-3) | "mysql" (Day 4+)
    connector: str = Field(default="file", alias="IDI_CONNECTOR")

    # Soundwave source files (the DB-less context feed)
    soundwave_dir: str = Field(default="soundwave", alias="SOUNDWAVE_DIR")

    # Paths
    repo_root: str = Field(default_factory=lambda: os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..")
    ))

    # Backend
    backend_port: int = Field(default=5000, alias="BACKEND_PORT")
    cors_origins: list[str] = Field(default=["*"])


settings = Settings()
