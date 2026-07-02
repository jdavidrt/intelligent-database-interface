"""Context Manager — DB introspection, survey, ChromaDB embedding."""

from __future__ import annotations
import os
from backend.app.models.envelope import DBProfile
from backend.app.services.memory.vector import embed_db_profile, embed_text
from backend.app.config import settings


class ContextManager:
    """
    1. Introspects the connected DB -> DBProfile.
    2. Injects human-supplied survey data (glossary, coded values, etc.).
    3. Loads every soundwave context document into ChromaDB.
    4. Embeds the schema into ChromaDB for semantic retrieval.
    """

    def __init__(self, connector) -> None:
        # Any DBConnector implementation (protocol, not a concrete class).
        self._db = connector

    def build_profile(self) -> DBProfile:
        """Full pipeline: introspect -> enrich with survey -> embed."""
        profile = self._db.introspect()
        profile = self._apply_soundwave_survey(profile)
        self._embed(profile)
        return profile

    # -- soundwave-specific survey data ------------------------------------------
    # In a future UI, this comes from the characterization form (§6 of MASTERPLAN).
    # For now, it is hardcoded from 02_soundwave_context.md.

    def _apply_soundwave_survey(self, profile: DBProfile) -> DBProfile:
        profile.domain_description = (
            "Soundwave is a music streaming platform database. "
            "It tracks artists, albums, tracks, users, playlists, "
            "subscriptions, play events, and payments."
        )
        profile.glossary = {
            "trk_dur_ms": "track duration in milliseconds",
            "is_exp": "is explicit content (1=yes, 0=no)",
            "is_prim": "is primary artist on a track (1=yes, 0=no)",
            "usr_acq_src": "user acquisition source code",
            "trk_position_ms": "playback position in milliseconds",
        }
        profile.coded_value_maps = {
            "plan_type": {
                "1": "Free",
                "2": "Individual Premium",
                "3": "Student Premium",
                "4": "Family Premium",
            },
            "usr_acq_src": {
                "1": "organic",
                "2": "referral",
                "3": "paid_ad",
                "4": "social",
            },
        }
        profile.source_of_truth = {
            "play_count": "play_events table (raw)",
            "monthly_listeners_cached": "daily_artist_metrics (pre-aggregated — use for reports, not real-time)",
            "total_plays": "tracks.total_plays is a cached counter; use COUNT(play_events) for accuracy",
        }
        return profile

    def _embed(self, profile: DBProfile) -> None:
        embed_db_profile(profile)
        # Ingest every soundwave context document into ChromaDB.
        sw_dir = os.path.join(settings.repo_root, settings.soundwave_dir)
        for fn in ("02_soundwave_context.md", "03_soundwave_edge_cases.md"):
            path = os.path.join(sw_dir, fn)
            if os.path.isfile(path):
                with open(path, encoding="utf-8") as f:
                    embed_text(f"soundwave::{fn}", f.read(), {"type": "domain_context"})
