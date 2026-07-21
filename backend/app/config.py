"""Centralised settings for the IDI backend."""

import os

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


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

    # Root folder holding one subfolder per database (the DB-less context feed)
    databases_dir: str = Field(default="databases", alias="DATABASES_DIR")

    # Paths
    repo_root: str = Field(
        default_factory=lambda: os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    )

    # Freeze the pipeline clock (services/clock.py) to a fixed ISO timestamp,
    # e.g. "2026-07-17T12:00:00" — empty = real time. Used by tests/evals so
    # date-dependent SQL ("last 8 months") gives identical results on any day.
    freeze_now: str = Field(default="", alias="IDI_FREEZE_NOW")

    # Schema-grounded planning: when true, the SQL Generator runs a constrained-
    # decoding plan step first (llama.cpp json_schema -> GBNF grammar over enums
    # of the schema's tables/join edges/columns), so table & join selection is
    # physically unable to hallucinate. Costs one extra LLM call per query.
    constrained_planning: bool = Field(default=True, alias="IDI_CONSTRAINED_PLANNING")

    # Structured SQL emission (SQL_HARDENING_PLAN Step 2): the final SELECT is
    # filled into a JSON query object whose identifier slots are enums from the
    # locked plan, then rendered deterministically, instead of being written as
    # free text and regexed out. Shapes the object cannot represent (CTEs,
    # window functions, subqueries, self-joins) fall back to free-form
    # generation, so this narrows how the model can go wrong without narrowing
    # what it can answer.
    structured_sql: bool = Field(default=True, alias="IDI_STRUCTURED_SQL")

    # Greedy decoding for scored benchmark runs. EVALUATION_PROTOCOL.md §1.3
    # requires temperature=0, top_p=1 and a fixed seed: non-greedy sampling
    # makes Execution Accuracy a random variable, and a run executed with it is
    # reportable only alongside n>=3 repetitions. Each agent picks its own
    # temperature (0.0-0.4) for interactive use; this flag overrides all of them
    # at the single point they share, so the override cannot miss one.
    greedy: bool = Field(default=False, alias="IDI_GREEDY")
    greedy_seed: int = Field(default=20260721, alias="IDI_GREEDY_SEED")

    # Backend
    backend_port: int = Field(default=5000, alias="BACKEND_PORT")
    cors_origins: list[str] = Field(default=["*"])


settings = Settings()
