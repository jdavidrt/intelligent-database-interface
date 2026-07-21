# Soundwave DB — Master Documentation & Context

**NL2SQL Test Database for the IDI (Intelligent Database Interface) Project**
Universidad Nacional de Colombia — Computer and Systems Engineering Thesis — 2026

---

## 1. What This Database Is

`soundwave_db` is a synthetic MySQL 8.0+ (InnoDB, utf8mb4) database modeling a fictional music streaming platform (Spotify/Deezer analog). It is the test bed for the IDI multi-agent NL2SQL system.

It is deliberately adversarial: every abbreviated column, nullable foreign key, integer code, and pre-aggregated table reproduces a documented NL2SQL failure mode from the Spider, BIRD, Dr. Spider, KaggleDBQA, and NL2SQL-BUGs benchmarks. The schema is the exam; the edge-case catalog is the syllabus.

## 2. File Map (this folder)

| File | Role |
|---|---|
| `00_soundwave_db_documentation.md` | This file — entry point and consolidated context |
| `01_soundwave_schema.sql` | DDL for all 19 tables, with EC annotations in comments |
| `02_soundwave_context.md` | Detailed per-table catalog (columns, types, NL2SQL challenges) |
| `02_soundwave_data.sql` | Seed data (~500 rows across 19 tables) |
| `03_soundwave_edge_cases.md` | Q01–Q30 edge-case query catalog: NL question, wrong SQL, correct SQL |
| `03_soundwave_edge_cases.sql` | Runnable versions of all 30 queries |
| `04_soundwave_survey.json` | Machine-readable business glossary, coded-value maps, and source-of-truth notes — loaded by `ContextManager` to enrich the auto-introspected `DBProfile` (added 2026-07-03, part of the generic per-database survey-file convention) |

## 3. Deployment

```sql
-- Run in order:
source 01_soundwave_schema.sql
source 02_soundwave_data.sql
source 03_soundwave_edge_cases.sql   -- optional: verification queries
```

```
mysql -u root -p < 01_soundwave_schema.sql
mysql -u root -p soundwave_db < 02_soundwave_data.sql
mysql -u root -p soundwave_db < 03_soundwave_edge_cases.sql
```

## 4. Schema at a Glance — 19 Tables in 4 Layers

| Layer | Tables |
|---|---|
| 1 — Core entities | `subscription_plans`, `genres`, `artists`, `albums`, `tracks`, `users` |
| 2 — Bridge / junction | `track_artists`, `artist_genres`, `track_genres`, `playlist_tracks`, `user_follows_artists`, `user_liked_tracks` |
| 3 — Transactional / event | `playlists`, `subscriptions`, `subscription_periods`, `pricing_history`, `payments`, `play_events` |
| 4 — Analytical / derived | `daily_artist_metrics` |

### Relationship Map

```
subscription_plans ──< pricing_history
subscription_plans ──< subscriptions ──< payments
                       subscriptions ──< subscription_periods
users >── subscriptions
users >── user_follows_artists ──< artists
users >── user_liked_tracks ──< tracks
users >── play_events
users >── playlists ──< playlist_tracks ──< tracks
users >── users               (referred_by_user_id, self-ref)

artists ──< albums ──< tracks
artists ──< track_artists >── tracks
artists ──< artist_genres >── genres
tracks  ──< track_genres  >── genres
tracks  ──< play_events
playlists >── playlists       (forked_from_id, self-ref)
genres    >── genres          (parent_genre_id, self-ref)
```

## 5. Critical Semantic Rules (context every agent needs)

These rules are not derivable from column names alone. An NL2SQL system must know them to produce correct SQL.

### 5.1 Coded values (no human-readable fallback in data)

| Column | Codes |
|---|---|
| `subscription_plans.plan_type` | 1=free, 2=student, 3=individual, 4=family |
| `subscriptions.status` | 0=inactive, 1=active, 2=suspended |
| `users.status` | 0=inactive, 1=active, 2=banned |
| `users.usr_acq_src` | 1=organic, 2=social, 3=referral, 4=ad |
| `play_events.event_type` | 'play', 'skip', 'save', 'share' (discriminator) |
| `payments.payment_status` | 'completed', 'failed', 'refunded', 'pending' |
| `playlists.playlist_type` | 'user', 'curated', 'algorithmic' |

### 5.2 NULL semantics (IS NULL, never = NULL)

| Column | NULL means |
|---|---|
| `tracks.album_id` | Standalone single |
| `users.referred_by_user_id` | Organic signup |
| `play_events.playlist_id` | Played outside any playlist |
| `pricing_history.effective_to` | Currently active price |
| `subscriptions.end_date` | Currently active subscription |
| `subscription_periods.period_end` | Currently running period |
| `playlist_tracks.added_by` | Added by the system |

### 5.3 Abbreviated columns

| Column | Meaning |
|---|---|
| `trk_dur_ms` | Track duration in milliseconds |
| `is_exp` | is_explicit flag |
| `is_prim` | is_primary flag (bridge tables) |
| `usr_acq_src` | User acquisition source |
| `trk_position_ms` | Position within track when event fired |

### 5.4 Two sources, two answers (pre-aggregated vs raw)

| Cached / pre-aggregated | Raw source | Measured divergence |
|---|---|---|
| `daily_artist_metrics.stream_count` | `COUNT(play_events WHERE event_type='play')` | 290,000× – 1,070,000× |
| `tracks.total_plays` | Raw play_events | 479× – 200,000,000× |
| `artists.monthly_listeners_cached` | `COUNT(DISTINCT user_id)` in play_events | 2.4M× – 9.1M× |

Never mix both sources for the same aggregate — double counting. Both answers are "correct"; the ambiguity is intentional (EC-07).

> **Corrected 2026-07-21.** This table previously described the divergence as "~5% higher (ETL inflation)". That was the design intent and it is not what the seed generator produced: the cached and pre-aggregated columns hold production-scale figures (millions to billions) while `play_events` is a ~1,000-row teaching sample, so the two disagree by five to eight orders of magnitude. The ratios above were measured per artist and per track against the seeded data, not estimated.
>
> The size of the gap changes what a benchmark question may claim. At 5% it is defensible to accept either source as correct; at 500,000× an item that accepts both is unfalsifiable, since almost any answer falls between them. `docs/EVALUATION_PROTOCOL.md` §9 quirk 2 was amended accordingly — every EC-07 benchmark item must name its source, and `accepted_alternatives` is forbidden on them.

### 5.5 Duplicated column names across tables

`name` appears in 5 tables (plans, genres, artists, users, playlists). `title` and `release_date` appear in both `albums` and `tracks`. `country` appears in `users` and `artists`; `play_events.country_code` is the event location (VPN/travel), distinct from `users.country`. `status` appears in `users` and `subscriptions` with different code meanings.

### 5.6 Genre paths are ambiguous by design

"Genre of a track" (`track_genres`) and "genre of a track's artist" (`artist_genres`) are different join paths that can disagree (e.g., a rapper releasing a pop track). Likewise, "saved tracks" can mean `user_liked_tracks` rows OR `play_events WHERE event_type='save'` — different counts.

## 6. Edge Case Taxonomy — EC-01 … EC-18

The verification test syllabus. Q01–Q30 in `03_soundwave_edge_cases.md` each trigger one or more of these.

| Code | Failure Category | Where Embedded |
|---|---|---|
| EC-01 | Ambiguous column names | `name` (5 tables); `title`, `release_date`, `country`, `status` (2 each) |
| EC-02 | Coded / enumerated values | `plan_type`, `status`, `usr_acq_src`, `event_type` |
| EC-03 | Nullable foreign keys | `tracks.album_id`, `users.referred_by_user_id`, `play_events.playlist_id` |
| EC-04 | Self-referential tables | `genres.parent_genre_id`, `users.referred_by_user_id`, `playlists.forked_from_id` |
| EC-05 | Abbreviated column names | `trk_dur_ms`, `is_exp`, `is_prim`, `usr_acq_src`, `trk_position_ms` |
| EC-06 | Temporal SCD | `pricing_history`, `subscription_periods`, `subscriptions` |
| EC-07 | Pre-aggregated vs raw | `daily_artist_metrics` vs `play_events`; cached counters |
| EC-08 | Multi-hop junction joins | 5-table chain: playlists→playlist_tracks→tracks→track_artists→artists |
| EC-09 | Self-joins | YoY temporal comparison; referral chain |
| EC-10 | Correlated subqueries | Per-group averages; per-artist comparisons |
| EC-11 | NULL handling in aggregations | LEFT JOIN + IS NULL; COUNT(*) vs COUNT(col) |
| EC-12 | Ordinal references | "Second most", "top 3"; DENSE_RANK vs LIMIT OFFSET |
| EC-13 | Superlative queries | "Most popular", tie handling |
| EC-14 | Negation / anti-join | NOT EXISTS, NOT IN, LEFT JOIN IS NULL |
| EC-15 | COUNT DISTINCT vs COUNT | Multi-artist tracks |
| EC-16 | GROUP BY correctness | Composite PK on `daily_artist_metrics` |
| EC-17 | Value matching / string filtering | `payment_status`, `playlist_type`, `event_type` |
| EC-18 | Compositional generalization | Patterns combined in novel configurations |

## 7. Seed Data Snapshot & Planted Test Targets

| Table | Rows | Notable |
|---|---|---|
| subscription_plans | 4 | Free, Student, Individual, Family |
| pricing_history | 11 | 1–4 historical prices per plan; changes in 2023, 2024 and 2025 |
| genres | 18 | 8 roots + 10 sub-genres (depth 2) |
| artists | 12 | 6 countries; Karol G is the Colombian artist |
| albums | 20 | 19 albums + 1 EP |
| tracks | 48 | 40 on albums + 8 singles (`album_id IS NULL`) |
| users | 40 | 28 organic + 12 referred; users 7, 8, 12 inactive/banned with zero play events |
| playlists | 18 | 15 original + 3 forked; 2 private |
| track_artists | 49 | Track 10 has 2 artists (Bad Bunny + Karol G) |
| artist_genres | 27 | 2–3 genres per artist, `is_prim` set |
| track_genres | 53 | 1–2 genres per track |
| playlist_tracks | 109 | 4 tracks appear in no playlist (anti-join) |
| user_follows_artists | 74 | User 7 follows Kendrick Lamar with zero Kendrick plays (canonical anti-join) |
| user_liked_tracks | 151 | Partial overlap with `event_type='save'` — only 4 rows appear in both (intentional) |
| subscriptions | 40 | 33 active + 6 inactive + 1 suspended |
| subscription_periods | 35 | plan upgrades give overlapping periods (cohort queries) |
| payments | 442 | 420 completed + 14 failed + 8 refunded; no pending rows survive |
| play_events | 1,230 | 2023-01-05 to 2026-07-17; 963 `play`, 145 `skip`, 64 `save`, 58 `share` |
| daily_artist_metrics | 134 | 2023-01-05 to 2026-07-13; see §5.4 for the divergence from raw events |

Temporal coverage: 2023-01-05 → 2026-07-17 12:00:00, the frozen-clock instant. Relative windows resolve to: last month (June 2026) 78 events, this year (2026) 502, trailing 12 months 808, last calendar year (2025) 588.

> **Corrected 2026-07-21.** Every figure in this table was re-counted against the seeded database. The previous values described the dataset as it stood *before* `scripts/extend_seed_data.py` extended it forward to the frozen clock, and had drifted badly — play_events was listed at ~150 against an actual 1,230, payments at 20 against 442, users at 20 against 40. The "8 full quarters (Jan 2023 – Jan 2025)" line was from the same era and understated coverage by six quarters.

## 8. How IDI Agents Should Use This Context

| Agent | Relevant sections |
|---|---|
| Context Manager | §5 semantic rules, §7 seed data — the domain knowledge to surface |
| Query Understanding | §5.5, §5.6 — ambiguity sources to detect and clarify |
| SQL Generator | §4 relationship map, §5.1–5.3 — code mappings and join paths |
| Verification Agent | §6 taxonomy + `03_soundwave_edge_cases.md` — the test syllabus |
| Visualization Engine | §7 temporal coverage — chart-worthy dimensions (time, country, genre) |

---

*Soundwave DB — designed for the IDI thesis project, Universidad Nacional de Colombia, 2026.*
