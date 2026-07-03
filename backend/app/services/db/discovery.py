"""Database discovery — scans databases/ for valid DB folders at request time."""

from __future__ import annotations
import glob
import os
import re

from pydantic import BaseModel

from backend.app.config import settings


class DatabaseSummary(BaseModel):
    db_name: str            # folder name — canonical identifier used everywhere
    display_name: str       # derived from the doc file's H1, or title-cased db_name
    description: str | None = None
    has_survey: bool = False


def list_available_databases() -> list[DatabaseSummary]:
    """Scan databases/<name>/ subfolders; a folder is valid iff it has exactly
    one *_schema.sql file (mirrors FileConnector's own validity check)."""
    base = os.path.join(settings.repo_root, settings.databases_dir)
    if not os.path.isdir(base):
        return []

    results: list[DatabaseSummary] = []
    for entry in sorted(os.scandir(base), key=lambda e: e.name):
        if not entry.is_dir():
            continue
        schema_matches = glob.glob(os.path.join(entry.path, "*_schema.sql"))
        if len(schema_matches) != 1:
            continue  # not a valid DB folder — skip silently

        doc_matches = glob.glob(os.path.join(entry.path, "*_db_documentation.md"))
        survey_matches = glob.glob(os.path.join(entry.path, "*_survey.json"))
        display_name, description = _derive_display(entry.name, doc_matches)
        results.append(DatabaseSummary(
            db_name=entry.name,
            display_name=display_name,
            description=description,
            has_survey=len(survey_matches) > 0,
        ))
    return results


def _derive_display(db_name: str, doc_matches: list[str]) -> tuple[str, str | None]:
    if doc_matches:
        with open(doc_matches[0], encoding="utf-8") as f:
            lines = [line.strip() for line in f if line.strip()]
        title = re.sub(r"^#+\s*", "", lines[0]) if lines else ""
        description = re.sub(r"^\*+|\*+$", "", lines[1]) if len(lines) > 1 else None
        return (title or db_name.title(), description or None)
    return (db_name.replace("_", " ").title(), None)
