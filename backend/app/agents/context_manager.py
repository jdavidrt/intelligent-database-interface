"""Context Manager — DB introspection, survey, ChromaDB embedding."""

from __future__ import annotations
import glob
import json
import os
from backend.app.models.envelope import DBProfile
from backend.app.services.memory.vector import embed_db_profile, embed_text


class ContextManager:
    """
    1. Introspects the connected DB -> DBProfile.
    2. Injects human-supplied survey data (glossary, coded values, etc.), if a
       per-database survey file is present.
    3. Loads every domain-context markdown document into ChromaDB.
    4. Embeds the schema into ChromaDB for semantic retrieval.
    """

    def __init__(self, connector) -> None:
        # Any DBConnector implementation (protocol, not a concrete class).
        self._db = connector

    def build_profile(self) -> DBProfile:
        """Full pipeline: introspect -> enrich with survey -> embed."""
        profile = self._db.introspect()
        profile = self._apply_survey(profile)
        self._embed(profile)
        return profile

    # -- per-database survey data --------------------------------------------------
    # Human-supplied domain knowledge (glossary, coded values, source-of-truth notes)
    # that can't be derived from the schema alone. Loaded from an optional
    # <db_dir>/NN_<db_name>_survey.json file (see 04_soundwave_survey.json).
    # If no survey file exists for this database, the profile stays introspection-only.

    def _apply_survey(self, profile: DBProfile) -> DBProfile:
        matches = glob.glob(os.path.join(self._db.db_dir, "*_survey.json"))
        if not matches:
            return profile
        with open(matches[0], encoding="utf-8") as f:
            survey = json.load(f)
        profile.domain_description = survey.get("domain_description")
        profile.glossary = survey.get("glossary", {})
        profile.coded_value_maps = survey.get("coded_value_maps", {})
        profile.source_of_truth = survey.get("source_of_truth", {})
        return profile

    def _embed(self, profile: DBProfile) -> None:
        embed_db_profile(profile)
        # Ingest every domain-context markdown document into ChromaDB, skipping
        # the discovery-only db-documentation file (not agent context).
        for path in glob.glob(os.path.join(self._db.db_dir, "*.md")):
            fn = os.path.basename(path)
            if fn.endswith("_db_documentation.md"):
                continue
            with open(path, encoding="utf-8") as f:
                embed_text(f"{profile.db_name}::{fn}", f.read(), {"type": "domain_context"})
