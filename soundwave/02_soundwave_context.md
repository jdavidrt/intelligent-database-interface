# Soundwave DB — General Database Context
## NL2SQL Test Database for the IDI Project
**Universidad Nacional de Colombia — Computer and Systems Engineering Thesis — 2026**

---

## 1. Purpose

`soundwave_db` is a synthetic relational database designed to test and evaluate the **IDI system** (Intelligent Database Interface), a multi-agent NL2SQL architecture. Its domain is a music streaming service — analogous to Spotify, Apple Music, or Deezer — chosen because it naturally produces the full range of analytical questions a non-technical manager or executive would ask, while also requiring the full spectrum of SQL complexity documented in NL2SQL research benchmarks (Spider, BIRD, Dr. Spider, KaggleDBQA, NL2SQL-BUGs).

The database is not a toy schema. Every table, every abbreviated column name, every nullable foreign key, and every pre-aggregated summary table was placed deliberately to reproduce a documented NL2SQL failure mode. See `03_soundwave_edge_cases.md` for the complete failure taxonomy mapped to specific queries.

---

## 2. Domain Description

The database models a fictional music streaming platform with the following business entities and processes:

| Business Entity | Description |
|---|---|
| Artists | Musicians and bands who publish content on the platform |
| Albums & Tracks | The music catalog, including standalone singles |
| Users | Registered listeners with subscription accounts |
| Subscription Plans | Tiered plans (Free, Student, Individual, Family) |
| Playlists | User-created, algorithmically-generated, and editorially curated collections |
| Play Events | Every interaction a user has with a track (play, skip, save, share) |
| Payments | Billing records tied to subscriptions |
| Analytics | Daily pre-aggregated metrics per artist and country |

---

## 3. Schema Overview

The 19 tables are organized in four logical layers:

```
LAYER 1 — CORE ENTITIES (6 tables)
  subscription_plans  genres  artists  albums  tracks  users

LAYER 2 — BRIDGE / JUNCTION TABLES (6 tables)
  track_artists  artist_genres  track_genres
  playlist_tracks  user_follows_artists  user_liked_tracks

LAYER 3 — TRANSACTIONAL / EVENT TABLES (4 tables)
  playlists  subscriptions  subscription_periods  payments  play_events

LAYER 4 — ANALYTICAL / DERIVED (1 table)
  daily_artist_metrics
```

---

## 4. Table Catalog

### 4.1 subscription_plans

| Column | Type | Description |
|---|---|---|
| plan_id | INT UNSIGNED PK | Auto-incremented identifier |
| **name** | VARCHAR(50) | Plan display name — **shared with artists, users, genres** |
| **plan_type** | TINYINT | **Coded value: 1=free, 2=student, 3=individual, 4=family** |
| monthly_price | DECIMAL(6,2) | Current listed price (see pricing_history for historical) |
| max_devices | TINYINT | Maximum simultaneous streams |
| has_downloads | TINYINT(1) | Offline download permission flag |
| has_hifi | TINYINT(1) | High-fidelity audio permission flag |

> NL2SQL challenge: `plan_type` is an integer code. "Which plans include lossless audio?" must map "lossless audio" → `has_hifi = 1`. "Show the Individual plan" must map "Individual" → `plan_type = 3` OR `name = 'Individual'`.

---

### 4.2 pricing_history

| Column | Type | Description |
|---|---|---|
| price_id | INT UNSIGNED PK | Auto-incremented identifier |
| plan_id | INT UNSIGNED FK | References subscription_plans |
| monthly_price | DECIMAL(6,2) | Price valid during the interval |
| effective_from | DATE | Start of this price's validity |
| **effective_to** | DATE **NULLABLE** | End of validity — **NULL = currently active** |
| changed_reason | VARCHAR(100) | Free-text rationale |

> NL2SQL challenge: "What is the current price of each plan?" requires `WHERE effective_to IS NULL`. "What was the price of Individual in mid-2023?" requires temporal overlap: `effective_from <= '2023-06-30' AND (effective_to IS NULL OR effective_to >= '2023-04-01')`.

---

### 4.3 genres

| Column | Type | Description |
|---|---|---|
| genre_id | INT UNSIGNED PK | Auto-incremented identifier |
| **name** | VARCHAR(80) UNIQUE | Genre name — **shared with artists, users, plans** |
| **parent_genre_id** | INT UNSIGNED FK NULLABLE | **Self-reference: NULL = root genre** |
| description | TEXT | Optional free-text |

> Hierarchy: Rock (root) → Indie Rock, Alternative; Latin (root) → Reggaeton, Salsa; etc.
> NL2SQL challenge: "Find all genres under Electronic" requires a self-join on `parent_genre_id`.

---

### 4.4 artists

| Column | Type | Description |
|---|---|---|
| artist_id | INT UNSIGNED PK | Auto-incremented identifier |
| **name** | VARCHAR(150) | Artist name — **shared with users, genres, plans** |
| **country** | CHAR(2) | ISO-3166 alpha-2 — **shared with users** |
| bio | TEXT | Optional biography |
| verified | TINYINT(1) | Platform-verified flag |
| **monthly_listeners_cached** | INT UNSIGNED | **Pre-aggregated; ~5% above raw play_events** |
| debut_year | YEAR | Year of debut |
| label | VARCHAR(100) | Record label |

> NL2SQL challenge: `monthly_listeners_cached` diverges from `COUNT(DISTINCT user_id)` in `play_events`. "How many monthly listeners does Bad Bunny have?" can return two different answers depending on which source the system queries.

---

### 4.5 albums

| Column | Type | Description |
|---|---|---|
| album_id | INT UNSIGNED PK | Auto-incremented identifier |
| **title** | VARCHAR(200) | Album title — **shared with tracks** |
| artist_id | INT UNSIGNED FK | Lead/primary artist |
| **release_date** | DATE | Release date — **shared with tracks** |
| album_type | ENUM | 'album', 'ep', 'compilation' |
| label | VARCHAR(100) | Record label |
| total_tracks | TINYINT | Number of tracks on the album |

---

### 4.6 tracks

| Column | Type | Description |
|---|---|---|
| track_id | INT UNSIGNED PK | Auto-incremented identifier |
| **title** | VARCHAR(200) | Track title — **shared with albums** |
| **album_id** | INT UNSIGNED FK **NULLABLE** | **NULL = standalone single; must use IS NULL, not = NULL** |
| **trk_dur_ms** | INT UNSIGNED | **Abbreviated: track duration in milliseconds** |
| **release_date** | DATE | Release date — **shared with albums** |
| **is_exp** | TINYINT(1) | **Abbreviated: is_explicit flag** |
| isrc | CHAR(12) | International Standard Recording Code |
| track_number | TINYINT NULLABLE | Position on album; NULL if single |
| **total_plays** | BIGINT UNSIGNED | **Cached count; ~5% lower than raw play_events** |

> NL2SQL challenge: "How many tracks are standalone singles?" must use `WHERE album_id IS NULL`. The common error `WHERE album_id = NULL` always returns 0 rows in MySQL.

---

### 4.7 users

| Column | Type | Description |
|---|---|---|
| user_id | INT UNSIGNED PK | Auto-incremented identifier |
| **name** | VARCHAR(120) | Full name — **shared with artists, genres, plans** |
| display_name | VARCHAR(80) | Public username |
| email | VARCHAR(255) UNIQUE | Login email |
| **country** | CHAR(2) | ISO-3166 — **shared with artists** |
| birth_date | DATE NULLABLE | Date of birth |
| **status** | TINYINT | **Coded: 0=inactive, 1=active, 2=banned — shared with subscriptions** |
| **usr_acq_src** | TINYINT | **Abbreviated + coded: 1=organic, 2=social, 3=referral, 4=ad** |
| **referred_by_user_id** | INT UNSIGNED FK NULLABLE | **Self-reference: NULL = organic signup** |
| joined_at | DATETIME | Account creation timestamp |
| last_login | DATETIME NULLABLE | Last login timestamp; NULL if never logged in again |

> Seed data includes: 3 users with status ≠ 1 (users 7, 8, 12), 5 referred users (16–20), 3 users with no play_events at all (7, 8, 12) — targets for anti-join queries.

---

### 4.8 playlists

| Column | Type | Description |
|---|---|---|
| playlist_id | INT UNSIGNED PK | Auto-incremented identifier |
| **name** | VARCHAR(200) | Playlist name — **shared with artists, users, genres** |
| user_id | INT UNSIGNED FK | Owner/creator |
| **playlist_type** | ENUM | **'user', 'curated', 'algorithmic' — value mapping required** |
| is_public | TINYINT(1) | Visibility flag; 2 playlists are private (is_public = 0) |
| **forked_from_id** | INT UNSIGNED FK NULLABLE | **Self-reference: NULL = original; non-NULL = forked** |
| follower_count | INT UNSIGNED | Cached follower count |

---

### 4.9 track_artists (bridge)

| Column | Type | Description |
|---|---|---|
| track_id | INT UNSIGNED PK | References tracks |
| artist_id | INT UNSIGNED PK | References artists |
| **is_prim** | TINYINT(1) | **Abbreviated: is_primary (1 = lead artist)** |
| role | ENUM | 'main', 'featured', 'producer' |

> Some tracks have 2 artists (e.g., track 10 "Me Porto Bonito": Bad Bunny + Karol G). This creates `COUNT(*)` vs `COUNT(DISTINCT artist_id)` test cases.

---

### 4.10 artist_genres (bridge)

| Column | Type | Description |
|---|---|---|
| artist_id | INT UNSIGNED PK | References artists |
| genre_id | INT UNSIGNED PK | References genres |
| **is_prim** | TINYINT(1) | **Abbreviated: is_primary (1 = artist's main genre)** |

---

### 4.11 track_genres (bridge)

| Column | Type | Description |
|---|---|---|
| track_id | INT UNSIGNED PK | References tracks |
| genre_id | INT UNSIGNED PK | References genres |

> This table is deliberately separate from `artist_genres`. A track may belong to a different genre than its artist (e.g., a rap artist releasing a pop track). "What genre is this track?" and "What genre is this artist?" are two different join paths — a schema-linking ambiguity stress test.

---

### 4.12 playlist_tracks (bridge)

| Column | Type | Description |
|---|---|---|
| playlist_id | INT UNSIGNED PK | References playlists |
| track_id | INT UNSIGNED PK | References tracks |
| position | SMALLINT | Position in playlist (supports ordinal queries) |
| added_at | DATETIME | Timestamp when track was added (supports temporal queries) |
| added_by | INT UNSIGNED NULLABLE | User who added it; NULL = system-added |

> Tracks 2, 5, 7, 11, 15, 17, 19, 21, 29 appear in NO playlists — targets for anti-join queries.

---

### 4.13 user_follows_artists (bridge)

| Column | Type | Description |
|---|---|---|
| user_id | INT UNSIGNED PK | References users |
| artist_id | INT UNSIGNED PK | References artists |
| followed_at | DATETIME | When the user followed the artist |

> User 7 follows artist 6 (Kendrick Lamar) but has ZERO play events involving Kendrick. This is the canonical seed row for anti-join tests.

---

### 4.14 user_liked_tracks (bridge)

| Column | Type | Description |
|---|---|---|
| user_id | INT UNSIGNED PK | References users |
| track_id | INT UNSIGNED PK | References tracks |
| liked_at | DATETIME | When the track was liked |

> Overlaps semantically with `play_events WHERE event_type = 'save'`. These two sources give different counts for "saved tracks" — intentional ambiguity.

---

### 4.15 subscriptions

| Column | Type | Description |
|---|---|---|
| subscription_id | INT UNSIGNED PK | Auto-incremented identifier |
| user_id | INT UNSIGNED FK | References users |
| plan_id | INT UNSIGNED FK | References subscription_plans |
| **status** | TINYINT | **Coded: 0=inactive, 1=active, 2=suspended — shared with users.status** |
| start_date | DATE | Subscription start |
| **end_date** | DATE NULLABLE | **NULL = currently active; IS NULL required** |
| auto_renew | TINYINT(1) | Auto-renewal flag |

---

### 4.16 subscription_periods (SCD)

| Column | Type | Description |
|---|---|---|
| period_id | INT UNSIGNED PK | Auto-incremented identifier |
| user_id | INT UNSIGNED FK | References users |
| plan_id | INT UNSIGNED FK | References subscription_plans |
| period_start | DATE | Start of this plan period |
| **period_end** | DATE NULLABLE | **NULL = currently running period** |
| monthly_fee | DECIMAL(6,2) | Fee locked at signup time (may differ from current pricing) |

> Some users have multiple rows (plan upgrades): James (Student → Individual), Elena (Individual → Family), Tom (Individual → Family). These support "users who changed plans" and cohort queries.

---

### 4.17 payments

| Column | Type | Description |
|---|---|---|
| payment_id | INT UNSIGNED PK | Auto-incremented identifier |
| subscription_id | INT UNSIGNED FK | References subscriptions |
| user_id | INT UNSIGNED FK | References users |
| amount | DECIMAL(8,2) | Payment amount |
| payment_date | DATE | Date of transaction |
| payment_method | ENUM | 'card', 'paypal', 'crypto', 'voucher' |
| **payment_status** | ENUM | **'completed', 'failed', 'refunded', 'pending' — value matching** |
| currency | CHAR(3) | ISO-4217 currency code |

> Includes 1 failed payment (user 16), 1 refunded payment (user 12), and 1 pending. These test `WHERE payment_status = 'completed'` value filtering.

---

### 4.18 play_events (polymorphic)

| Column | Type | Description |
|---|---|---|
| event_id | BIGINT UNSIGNED PK | Auto-incremented identifier |
| user_id | INT UNSIGNED FK | References users |
| track_id | INT UNSIGNED FK | References tracks |
| **playlist_id** | INT UNSIGNED FK NULLABLE | **NULL = played outside any playlist** |
| **event_type** | ENUM | **'play', 'skip', 'save', 'share' — discriminator column** |
| played_at | DATETIME | Event timestamp (spans 2023-01 to 2025-01) |
| **trk_position_ms** | INT UNSIGNED | **Abbreviated: ms into track when event was recorded** |
| duration_ms | INT UNSIGNED | Actual listen duration (0 for non-play events) |
| **country_code** | CHAR(2) | **Event country — distinct from users.country (user may use VPN or travel)** |
| device_type | ENUM | 'mobile', 'desktop', 'tablet', 'smart_tv', 'other' |

> This is the richest table. A naive `COUNT(*) FROM play_events` counts all events (plays + skips + saves + shares). "How many songs were played?" must filter `event_type = 'play'`.

---

### 4.19 daily_artist_metrics (pre-aggregated)

| Column | Type | Description |
|---|---|---|
| **artist_id** | INT UNSIGNED PK | References artists — part of composite PK |
| **metric_date** | DATE PK | Date — part of composite PK |
| **country_code** | CHAR(2) PK | Country — part of composite PK |
| **stream_count** | INT UNSIGNED | **Intentionally ~5% above raw play_events counts (ETL inflation)** |
| skip_count | INT UNSIGNED | Skip events that day |
| save_count | INT UNSIGNED | Save events that day |
| unique_listeners | INT UNSIGNED | Distinct user count |
| avg_listen_pct | DECIMAL(5,2) | Average percentage of track listened |

> Composite PK `(artist_id, metric_date, country_code)` tests GROUP BY completeness. Using this table AND `play_events` for the same aggregate causes ~5% discrepancy — simulates real ETL pipeline inflation.

---

## 5. Key Relationships Diagram (text)

```
subscription_plans ──< pricing_history
subscription_plans ──< subscriptions ──< payments
                        subscriptions ──< subscription_periods
users >── subscriptions
users >── user_follows_artists ──< artists
users >── user_liked_tracks ──< tracks
users >── play_events
users >── playlists ──< playlist_tracks ──< tracks
users >── users (referred_by_user_id, self-ref)

artists ──< albums ──< tracks
artists ──< track_artists >── tracks
artists ──< artist_genres >── genres
tracks ──< track_genres >── genres
tracks ──< play_events
playlists >── playlists (forked_from_id, self-ref)
genres >── genres (parent_genre_id, self-ref)
```

---

## 6. Embedded NL2SQL Stress Patterns Summary

| Code | Pattern | Tables Affected | Why It Breaks NL2SQL |
|---|---|---|---|
| EC-01 | Ambiguous column names | `name` in 5 tables; `title`, `release_date`, `country`, `status` in 2 tables each | Schema linker selects the wrong table |
| EC-02 | Coded/enumerated values | `plan_type`, `status`, `usr_acq_src`, `event_type` | System must decode integers/strings without human-readable context |
| EC-03 | Nullable foreign keys | `tracks.album_id`, `users.referred_by_user_id`, `play_events.playlist_id` | `= NULL` always returns 0 rows; `IS NULL` required |
| EC-04 | Self-referential tables | `genres.parent_genre_id`, `users.referred_by_user_id`, `playlists.forked_from_id` | Multi-level self-join rarely generated correctly |
| EC-05 | Abbreviated column names | `trk_dur_ms`, `is_exp`, `is_prim`, `usr_acq_src`, `trk_position_ms` | Schema linker cannot resolve natural language to abbreviated names |
| EC-06 | Temporal SCD | `pricing_history`, `subscription_periods`, `subscriptions` | Current record requires `IS NULL` filter, not a simple lookup |
| EC-07 | Pre-agg vs raw ambiguity | `daily_artist_metrics`, `tracks.total_plays`, `artists.monthly_listeners_cached` | Two valid sources give different numbers; both answers are "correct" |
| EC-08 | Multi-hop junction chains | `playlist_tracks`, `track_artists`, `artist_genres`, `user_follows_artists` | Model must traverse 4–5 tables the user never mentions |

---

## 7. Seed Data Snapshot

| Table | Rows | Notable data points |
|---|---|---|
| subscription_plans | 4 | Free, Student, Individual, Family |
| pricing_history | 8 | 2–3 historical prices per plan |
| genres | 18 | 8 root genres, 10 sub-genres (depth = 2) |
| artists | 12 | 10 countries; 1 artist from Colombia (Karol G) |
| albums | 15 | 13 studio albums, 2 compilations |
| tracks | 30 | 25 on albums + 5 standalone singles (album_id IS NULL) |
| users | 20 | 15 organic + 5 referred; 3 inactive/banned; 3 with zero play events |
| playlists | 18 | 15 original + 3 forked; 2 private playlists |
| track_artists | 32 | 1 track with 2 artists (multi-artist test) |
| artist_genres | 24 | Each artist has 2–3 genres; is_prim flags set |
| track_genres | 44 | Each track has 1–2 genres |
| playlist_tracks | 44 | 9 tracks appear in no playlist (anti-join targets) |
| user_follows_artists | 27 | User 7 follows Kendrick with zero Kendrick plays |
| user_liked_tracks | 25 | Partial overlap with play_events save events |
| subscriptions | 20 | 17 active + 2 expired + 1 suspended |
| subscription_periods | 12 | 4 users have multiple rows (plan upgrades) |
| payments | 20 | 1 failed + 1 refunded + 1 pending |
| play_events | ~150 | Spans 2023-01 to 2025-01; users 7, 8, 12 have zero rows |
| daily_artist_metrics | 31 | stream_count ~5% above raw play_events per day |

---

## 8. Temporal Coverage

Play events span **January 2023 to January 2025**, providing:

- 8 full quarters for YoY and QoQ comparisons
- A visible stream spike in Q3 2024 for Billie Eilish (album launch simulation)
- Users 7, 8, and 12 with zero events at any time (anti-join targets)
- Pricing changes in 2023 and 2024 for all paid plans

---

## 9. How to Deploy

```sql
-- Run in order:
source 01_soundwave_schema.sql
source 02_soundwave_data.sql

-- Optional: run analytical views (included in edge cases file)
source 03_soundwave_edge_cases.sql
```

Or as a single command in the VSCode terminal:

```
mysql -u root -p < 01_soundwave_schema.sql
mysql -u root -p soundwave_db < 02_soundwave_data.sql
mysql -u root -p soundwave_db < 03_soundwave_edge_cases.sql
```

---

*Soundwave DB — designed for the IDI (Intelligent Database Interface) thesis project, Universidad Nacional de Colombia, 2026.*
