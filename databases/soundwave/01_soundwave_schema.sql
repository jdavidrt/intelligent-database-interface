-- ============================================================
--  SOUNDWAVE DB  |  Schema Definition (DDL only)
--  NL2SQL Test Database for IDI Project
--  Universidad Nacional de Colombia  |  2026
-- ============================================================
--
--  Domain   : Music Streaming Service
--  Engine   : MySQL 8.0+  (InnoDB, utf8mb4)
--  Tables   : 19
--  Purpose  : Stress-test a multi-agent NL2SQL system across
--             18 documented failure categories from Spider,
--             BIRD, Dr. Spider, KaggleDBQA, NL2SQL-BUGs.
--
--  NL2SQL STRESS PATTERNS EMBEDDED IN THIS SCHEMA:
--
--  [EC-01] Ambiguous column names across tables
--          name         -> subscription_plans, genres, artists, users, playlists
--          title        -> albums, tracks
--          release_date -> albums, tracks
--          status       -> users, subscriptions
--          country      -> users, artists
--
--  [EC-02] Coded / enumerated values (no human-readable fallback)
--          subscription_plans.plan_type : 1=free 2=student 3=individual 4=family
--          subscriptions.status         : 0=inactive 1=active 2=suspended
--          users.status                 : 0=inactive 1=active 2=banned
--          users.usr_acq_src            : 1=organic 2=social 3=referral 4=ad
--          play_events.event_type       : 'play' | 'skip' | 'save' | 'share'
--
--  [EC-03] Nullable foreign keys (IS NULL != = NULL)
--          tracks.album_id              -> NULL = standalone single
--          users.referred_by_user_id    -> NULL = organic signup
--          play_events.playlist_id      -> NULL = played outside a playlist
--
--  [EC-04] Self-referential relationships
--          genres.parent_genre_id       -> genre hierarchy (Rock -> Indie Rock)
--          users.referred_by_user_id    -> user referral chain
--          playlists.forked_from_id     -> playlist lineage
--
--  [EC-05] Mixed / abbreviated naming conventions
--          trk_dur_ms    = track duration in milliseconds
--          is_exp        = is_explicit flag
--          is_prim       = is_primary flag (in bridge tables)
--          usr_acq_src   = user acquisition source
--          trk_position_ms = position in track when event fired
--
--  [EC-06] Temporal SCD tables (Slowly Changing Dimensions)
--          pricing_history.effective_to     -> NULL = current price
--          subscription_periods.period_end  -> NULL = currently running
--          subscriptions.end_date           -> NULL = currently active
--
--  [EC-07] Pre-aggregated vs raw event table ambiguity
--          daily_artist_metrics.stream_count  290,000x - 1,070,000x COUNT(play_events)
--          tracks.total_plays                 479x - 200,000,000x raw events
--          artists.monthly_listeners_cached   2.4M x - 9.1M x raw distinct listeners
--
--          CORRECTED 2026-07-21. Every line above previously read "~5% higher"
--          or "may drift". That was the design intent, and it was never true of
--          the generated data: the cached and pre-aggregated columns are seeded
--          at production scale (millions to billions) while play_events is a
--          ~1,000-row teaching sample, so the two sources disagree by five to
--          eight orders of magnitude, not by 5%. Ratios above were measured
--          against the seeded data, per artist and per track, not estimated.
--          The trap is real either way, but its size matters: a benchmark item
--          that accepts both sources as correct is unfalsifiable at this
--          spread, which is why EVALUATION_PROTOCOL.md §9 quirk 2 now requires
--          every EC-07 item to name its source instead.
--
--  [EC-08] Many-to-many junction tables (multi-hop join chains)
--          playlists -> playlist_tracks -> tracks -> track_artists -> artists
--          users -> user_follows_artists -> artists -> artist_genres -> genres
--
-- ============================================================

DROP DATABASE IF EXISTS soundwave_db;
CREATE DATABASE soundwave_db
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE soundwave_db;

SET FOREIGN_KEY_CHECKS = 0;

-- ============================================================
--  TABLE 01: subscription_plans
--  Stress patterns: EC-01 (name), EC-02 (plan_type integer code)
-- ============================================================
CREATE TABLE subscription_plans (
    plan_id        INT UNSIGNED   NOT NULL AUTO_INCREMENT,
    name           VARCHAR(50)    NOT NULL,                     -- [EC-01] also in artists, users, genres
    plan_type      TINYINT        NOT NULL,                     -- [EC-02] 1=free 2=student 3=individual 4=family
    monthly_price  DECIMAL(6,2)   NOT NULL DEFAULT 0.00,
    max_devices    TINYINT        NOT NULL DEFAULT 1,
    has_downloads  TINYINT(1)     NOT NULL DEFAULT 0,
    has_hifi       TINYINT(1)     NOT NULL DEFAULT 0,
    created_at     DATETIME       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (plan_id),
    UNIQUE KEY uq_plan_type (plan_type)
) ENGINE=InnoDB
  COMMENT='Subscription tier catalog. plan_type codes: 1=free, 2=student, 3=individual, 4=family. [EC-01, EC-02]';


-- ============================================================
--  TABLE 02: pricing_history
--  Stress patterns: EC-06 (effective_to IS NULL = current price)
--  NL challenge: "What was the price of Individual in Q2 2023?"
--  requires temporal overlap logic, not a simple equality lookup.
-- ============================================================
CREATE TABLE pricing_history (
    price_id       INT UNSIGNED   NOT NULL AUTO_INCREMENT,
    plan_id        INT UNSIGNED   NOT NULL,
    monthly_price  DECIMAL(6,2)   NOT NULL,
    effective_from DATE           NOT NULL,
    effective_to   DATE           NULL,                         -- [EC-06] NULL = currently active price
    changed_reason VARCHAR(100)   NULL,
    PRIMARY KEY (price_id),
    KEY idx_ph_plan_dates (plan_id, effective_from),
    CONSTRAINT fk_ph_plan FOREIGN KEY (plan_id)
        REFERENCES subscription_plans (plan_id)
) ENGINE=InnoDB
  COMMENT='Price history per plan. effective_to IS NULL = current price. Temporal overlap queries. [EC-06]';


-- ============================================================
--  TABLE 03: genres
--  Stress patterns: EC-01 (name), EC-04 (parent_genre_id self-ref)
--  NL challenge: "Find all sub-genres under Rock" requires
--  recursive or multi-level self-join on the same table.
-- ============================================================
CREATE TABLE genres (
    genre_id        INT UNSIGNED   NOT NULL AUTO_INCREMENT,
    name            VARCHAR(80)    NOT NULL,                    -- [EC-01] also in artists, users, plans
    parent_genre_id INT UNSIGNED   NULL,                        -- [EC-04] NULL = root genre
    description     TEXT           NULL,
    PRIMARY KEY (genre_id),
    UNIQUE KEY uq_genre_name (name),
    KEY idx_genre_parent (parent_genre_id),
    CONSTRAINT fk_genre_parent FOREIGN KEY (parent_genre_id)
        REFERENCES genres (genre_id)
) ENGINE=InnoDB
  COMMENT='Genre catalog with hierarchy. parent_genre_id IS NULL = root. [EC-01, EC-04 self-ref]';


-- ============================================================
--  TABLE 04: artists
--  Stress patterns: EC-01 (name, country), EC-07 (cached counter)
--  monthly_listeners_cached diverges from raw play_events by 2.4M x - 9.1M x
--  (measured 2026-07-21; the "~5%" this line used to claim was never true).
-- ============================================================
CREATE TABLE artists (
    artist_id                INT UNSIGNED   NOT NULL AUTO_INCREMENT,
    name                     VARCHAR(150)   NOT NULL,           -- [EC-01] also in users, genres, plans
    country                  CHAR(2)        NOT NULL,           -- [EC-01] also in users; ISO-3166 alpha-2
    bio                      TEXT           NULL,
    verified                 TINYINT(1)     NOT NULL DEFAULT 0,
    monthly_listeners_cached INT UNSIGNED   NOT NULL DEFAULT 0, -- [EC-07] 2.4M x - 9.1M x raw
    debut_year               YEAR           NULL,
    label                    VARCHAR(100)   NULL,
    created_at               DATETIME       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (artist_id),
    KEY idx_artist_country (country)
) ENGINE=InnoDB
  COMMENT='Artist catalog. monthly_listeners_cached is seeded at production scale and exceeds raw play_events by millions of times, not by 5%. [EC-01, EC-07]';


-- ============================================================
--  TABLE 05: albums
--  Stress patterns: EC-01 (title, release_date mirrored in tracks)
-- ============================================================
CREATE TABLE albums (
    album_id      INT UNSIGNED   NOT NULL AUTO_INCREMENT,
    title         VARCHAR(200)   NOT NULL,                      -- [EC-01] also in tracks
    artist_id     INT UNSIGNED   NOT NULL,
    release_date  DATE           NOT NULL,                      -- [EC-01] also in tracks
    album_type    ENUM('album','ep','compilation') NOT NULL DEFAULT 'album',
    label         VARCHAR(100)   NULL,
    total_tracks  TINYINT        NOT NULL DEFAULT 0,
    cover_url     VARCHAR(500)   NULL,
    PRIMARY KEY (album_id),
    KEY idx_album_artist  (artist_id),
    KEY idx_album_release (release_date),
    CONSTRAINT fk_album_artist FOREIGN KEY (artist_id)
        REFERENCES artists (artist_id)
) ENGINE=InnoDB
  COMMENT='Album catalog. title and release_date intentionally mirror tracks for schema-linking confusion. [EC-01]';


-- ============================================================
--  TABLE 06: tracks
--  Stress patterns:
--    EC-01 (title, release_date shared with albums)
--    EC-03 (album_id IS NULL = standalone single)
--    EC-05 (trk_dur_ms, is_exp — abbreviated columns)
--    EC-07 (total_plays cached; may diverge from raw events)
-- ============================================================
CREATE TABLE tracks (
    track_id      INT UNSIGNED   NOT NULL AUTO_INCREMENT,
    title         VARCHAR(200)   NOT NULL,                      -- [EC-01] also in albums
    album_id      INT UNSIGNED   NULL,                          -- [EC-03] NULL = standalone single
    trk_dur_ms    INT UNSIGNED   NOT NULL,                      -- [EC-05] duration in milliseconds
    release_date  DATE           NOT NULL,                      -- [EC-01] also in albums
    is_exp        TINYINT(1)     NOT NULL DEFAULT 0,            -- [EC-05] is_explicit (abbreviated)
    isrc          CHAR(12)       NULL,
    track_number  TINYINT        NULL,                          -- NULL if standalone single
    total_plays   BIGINT UNSIGNED NOT NULL DEFAULT 0,           -- [EC-07] 479x - 2e8 x raw
    PRIMARY KEY (track_id),
    KEY idx_track_album   (album_id),
    KEY idx_track_release (release_date),
    CONSTRAINT fk_track_album FOREIGN KEY (album_id)
        REFERENCES albums (album_id)
) ENGINE=InnoDB
  COMMENT='Track catalog. album_id IS NULL = single. trk_dur_ms/is_exp are abbreviated. [EC-01, EC-03, EC-05, EC-07]';


-- ============================================================
--  TABLE 07: users
--  Stress patterns:
--    EC-01 (name, country, status shared with other tables)
--    EC-02 (status 0/1/2 coded; usr_acq_src 1/2/3/4 coded)
--    EC-03 (referred_by_user_id IS NULL = organic signup)
--    EC-04 (self-referential referral chain)
--    EC-05 (usr_acq_src abbreviated)
-- ============================================================
CREATE TABLE users (
    user_id             INT UNSIGNED   NOT NULL AUTO_INCREMENT,
    name                VARCHAR(120)   NOT NULL,                -- [EC-01] also in artists, genres, plans
    display_name        VARCHAR(80)    NOT NULL,
    email               VARCHAR(255)   NOT NULL,
    country             CHAR(2)        NOT NULL,                -- [EC-01] also in artists
    birth_date          DATE           NULL,
    status              TINYINT        NOT NULL DEFAULT 1,      -- [EC-01, EC-02] 0=inactive 1=active 2=banned
    usr_acq_src         TINYINT        NOT NULL DEFAULT 1,      -- [EC-02, EC-05] 1=organic 2=social 3=referral 4=ad
    referred_by_user_id INT UNSIGNED   NULL,                    -- [EC-03, EC-04] NULL = organic
    joined_at           DATETIME       NOT NULL,
    last_login          DATETIME       NULL,
    PRIMARY KEY (user_id),
    UNIQUE KEY uq_user_email (email),
    KEY idx_user_country  (country),
    KEY idx_user_referral (referred_by_user_id),
    CONSTRAINT fk_user_referrer FOREIGN KEY (referred_by_user_id)
        REFERENCES users (user_id)
) ENGINE=InnoDB
  COMMENT='App users. referred_by_user_id IS NULL = organic. status and usr_acq_src are integer codes. [EC-01..EC-05]';


-- ============================================================
--  TABLE 08: playlists
--  Stress patterns:
--    EC-01 (name shared with artists, users, genres)
--    EC-02 (playlist_type enum — value matching)
--    EC-04 (forked_from_id self-referential)
-- ============================================================
CREATE TABLE playlists (
    playlist_id    INT UNSIGNED   NOT NULL AUTO_INCREMENT,
    name           VARCHAR(200)   NOT NULL,                     -- [EC-01] also in artists, users, genres
    user_id        INT UNSIGNED   NOT NULL,
    playlist_type  ENUM('user','curated','algorithmic') NOT NULL DEFAULT 'user', -- [EC-02]
    is_public      TINYINT(1)     NOT NULL DEFAULT 1,
    forked_from_id INT UNSIGNED   NULL,                         -- [EC-04] NULL = original; self-ref
    created_at     DATETIME       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at     DATETIME       NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    follower_count INT UNSIGNED   NOT NULL DEFAULT 0,
    PRIMARY KEY (playlist_id),
    KEY idx_pl_user (user_id),
    KEY idx_pl_fork (forked_from_id),
    CONSTRAINT fk_pl_user FOREIGN KEY (user_id)
        REFERENCES users (user_id),
    CONSTRAINT fk_pl_fork FOREIGN KEY (forked_from_id)
        REFERENCES playlists (playlist_id)
) ENGINE=InnoDB
  COMMENT='Playlists. forked_from_id IS NULL = original. playlist_type enum needs value mapping. [EC-01, EC-02, EC-04]';


-- ============================================================
--  TABLE 09: track_artists  (bridge: tracks <-> artists)
--  Stress patterns: EC-05 (is_prim abbreviated), EC-08 (multi-hop)
--  Multi-hop chain anchor:
--  playlists -> playlist_tracks -> tracks -> track_artists -> artists
-- ============================================================
CREATE TABLE track_artists (
    track_id   INT UNSIGNED   NOT NULL,
    artist_id  INT UNSIGNED   NOT NULL,
    is_prim    TINYINT(1)     NOT NULL DEFAULT 1,               -- [EC-05] is_primary (abbreviated)
    role       ENUM('main','featured','producer') NOT NULL DEFAULT 'main',
    PRIMARY KEY (track_id, artist_id),
    KEY idx_ta_artist (artist_id),
    CONSTRAINT fk_ta_track  FOREIGN KEY (track_id)  REFERENCES tracks  (track_id),
    CONSTRAINT fk_ta_artist FOREIGN KEY (artist_id) REFERENCES artists (artist_id)
) ENGINE=InnoDB
  COMMENT='Track-Artist bridge. is_prim abbreviated. Anchor of 5-table multi-hop chain. [EC-05, EC-08]';


-- ============================================================
--  TABLE 10: artist_genres  (bridge: artists <-> genres)
--  Stress patterns: EC-05 (is_prim abbreviated)
--  Note: track_genres exists as a separate table. Having BOTH
--  creates schema-linking ambiguity: "genre of track" vs "genre
--  of artist" — two different paths, both valid. [EC-01, EC-08]
-- ============================================================
CREATE TABLE artist_genres (
    artist_id  INT UNSIGNED   NOT NULL,
    genre_id   INT UNSIGNED   NOT NULL,
    is_prim    TINYINT(1)     NOT NULL DEFAULT 0,               -- [EC-05] is_primary (abbreviated)
    PRIMARY KEY (artist_id, genre_id),
    KEY idx_ag_genre (genre_id),
    CONSTRAINT fk_ag_artist FOREIGN KEY (artist_id) REFERENCES artists (artist_id),
    CONSTRAINT fk_ag_genre  FOREIGN KEY (genre_id)  REFERENCES genres  (genre_id)
) ENGINE=InnoDB
  COMMENT='Artist-Genre bridge. is_prim=1 = primary genre. Distinct from track_genres. [EC-05, EC-08]';


-- ============================================================
--  TABLE 11: track_genres  (bridge: tracks <-> genres)
--  Deliberately separate from artist_genres. A track may belong
--  to a genre different from its artist (e.g. rapper releases pop).
--  This is a deliberate EC-01 ambiguity source: "What genre is
--  this track?" vs "What genre is this artist?" are different joins.
-- ============================================================
CREATE TABLE track_genres (
    track_id   INT UNSIGNED   NOT NULL,
    genre_id   INT UNSIGNED   NOT NULL,
    PRIMARY KEY (track_id, genre_id),
    KEY idx_tg_genre (genre_id),
    CONSTRAINT fk_tg_track FOREIGN KEY (track_id)  REFERENCES tracks (track_id),
    CONSTRAINT fk_tg_genre FOREIGN KEY (genre_id)  REFERENCES genres (genre_id)
) ENGINE=InnoDB
  COMMENT='Track-Genre bridge. Separate from artist_genres to create intentional schema-linking ambiguity. [EC-01]';


-- ============================================================
--  TABLE 12: playlist_tracks  (bridge: playlists <-> tracks)
--  added_at enables temporal queries.
--  position enables ordinal queries ("first track of each playlist").
-- ============================================================
CREATE TABLE playlist_tracks (
    playlist_id INT UNSIGNED   NOT NULL,
    track_id    INT UNSIGNED   NOT NULL,
    position    SMALLINT       NOT NULL DEFAULT 1,
    added_at    DATETIME       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    added_by    INT UNSIGNED   NULL,                            -- NULL = added by the system
    PRIMARY KEY (playlist_id, track_id),
    KEY idx_pt_track (track_id),
    KEY idx_pt_added (added_at),
    CONSTRAINT fk_pt_playlist FOREIGN KEY (playlist_id) REFERENCES playlists (playlist_id),
    CONSTRAINT fk_pt_track    FOREIGN KEY (track_id)    REFERENCES tracks    (track_id)
) ENGINE=InnoDB
  COMMENT='Playlist-Track bridge. position and added_at support ordinal and temporal queries. [EC-08]';


-- ============================================================
--  TABLE 13: user_follows_artists  (bridge: users <-> artists)
--  Enables anti-join EC-14 test:
--  "Users who follow an artist but have NEVER listened to them."
-- ============================================================
CREATE TABLE user_follows_artists (
    user_id     INT UNSIGNED   NOT NULL,
    artist_id   INT UNSIGNED   NOT NULL,
    followed_at DATETIME       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, artist_id),
    KEY idx_ufa_artist (artist_id),
    CONSTRAINT fk_ufa_user   FOREIGN KEY (user_id)   REFERENCES users   (user_id),
    CONSTRAINT fk_ufa_artist FOREIGN KEY (artist_id) REFERENCES artists (artist_id)
) ENGINE=InnoDB
  COMMENT='User-Artist follow bridge. followed_at enables cohort analysis. [EC-14 anti-join target]';


-- ============================================================
--  TABLE 14: user_liked_tracks  (bridge: users <-> tracks)
--  Deliberately overlaps with play_events.event_type = 'save'.
--  "How many tracks did users save?" is ambiguous: it could mean
--  liked_tracks rows OR play_events WHERE event_type = 'save'.
--  This is an intentional value-matching ambiguity [EC-17].
-- ============================================================
CREATE TABLE user_liked_tracks (
    user_id  INT UNSIGNED   NOT NULL,
    track_id INT UNSIGNED   NOT NULL,
    liked_at DATETIME       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, track_id),
    KEY idx_ult_track (track_id),
    CONSTRAINT fk_ult_user  FOREIGN KEY (user_id)  REFERENCES users  (user_id),
    CONSTRAINT fk_ult_track FOREIGN KEY (track_id) REFERENCES tracks (track_id)
) ENGINE=InnoDB
  COMMENT='User-Track likes. Intentionally overlaps with play_events event_type=save for ambiguity. [EC-17]';


-- ============================================================
--  TABLE 15: subscriptions
--  Stress patterns:
--    EC-01 (status also in users)
--    EC-02 (status coded 0/1/2)
--    EC-03 (end_date IS NULL = currently active)
--    EC-06 (temporal SCD: current record = end_date IS NULL)
-- ============================================================
CREATE TABLE subscriptions (
    subscription_id INT UNSIGNED   NOT NULL AUTO_INCREMENT,
    user_id         INT UNSIGNED   NOT NULL,
    plan_id         INT UNSIGNED   NOT NULL,
    status          TINYINT        NOT NULL DEFAULT 1,          -- [EC-01, EC-02] 0=inactive 1=active 2=suspended
    start_date      DATE           NOT NULL,
    end_date        DATE           NULL,                        -- [EC-03, EC-06] NULL = currently active
    auto_renew      TINYINT(1)     NOT NULL DEFAULT 1,
    created_at      DATETIME       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (subscription_id),
    KEY idx_sub_user  (user_id),
    KEY idx_sub_plan  (plan_id),
    KEY idx_sub_dates (start_date, end_date),
    CONSTRAINT fk_sub_user FOREIGN KEY (user_id)  REFERENCES users              (user_id),
    CONSTRAINT fk_sub_plan FOREIGN KEY (plan_id)  REFERENCES subscription_plans (plan_id)
) ENGINE=InnoDB
  COMMENT='Subscription records. end_date IS NULL = active. status coded 0/1/2. [EC-01, EC-02, EC-03, EC-06]';


-- ============================================================
--  TABLE 16: subscription_periods  (Temporal SCD)
--  Stress patterns: EC-06
--  Tracks every plan interval for each user separately.
--  Enables: "What plan was user X on in Q3 2023?" (date overlap)
--           "Which users downgraded and resubscribed within 60 days?"
--  period_end IS NULL = the period is still running.
-- ============================================================
CREATE TABLE subscription_periods (
    period_id    INT UNSIGNED   NOT NULL AUTO_INCREMENT,
    user_id      INT UNSIGNED   NOT NULL,
    plan_id      INT UNSIGNED   NOT NULL,
    period_start DATE           NOT NULL,
    period_end   DATE           NULL,                           -- [EC-06] NULL = currently running
    monthly_fee  DECIMAL(6,2)   NOT NULL,                      -- fee locked at signup time
    PRIMARY KEY (period_id),
    KEY idx_sp_user  (user_id),
    KEY idx_sp_dates (period_start, period_end),
    CONSTRAINT fk_sp_user FOREIGN KEY (user_id)  REFERENCES users              (user_id),
    CONSTRAINT fk_sp_plan FOREIGN KEY (plan_id)  REFERENCES subscription_plans (plan_id)
) ENGINE=InnoDB
  COMMENT='SCD subscription periods. period_end IS NULL = currently running period. [EC-06 temporal SCD]';


-- ============================================================
--  TABLE 17: payments
--  payment_status string enum tests value matching [EC-17].
--  Multi-hop to plan: payments -> subscriptions -> subscription_plans
-- ============================================================
CREATE TABLE payments (
    payment_id      INT UNSIGNED   NOT NULL AUTO_INCREMENT,
    subscription_id INT UNSIGNED   NOT NULL,
    user_id         INT UNSIGNED   NOT NULL,
    amount          DECIMAL(8,2)   NOT NULL,
    payment_date    DATE           NOT NULL,
    payment_method  ENUM('card','paypal','crypto','voucher') NOT NULL DEFAULT 'card',
    payment_status  ENUM('completed','failed','refunded','pending') NOT NULL DEFAULT 'completed', -- [EC-17]
    currency        CHAR(3)        NOT NULL DEFAULT 'USD',
    PRIMARY KEY (payment_id),
    KEY idx_pay_user  (user_id),
    KEY idx_pay_sub   (subscription_id),
    KEY idx_pay_date  (payment_date),
    CONSTRAINT fk_pay_sub  FOREIGN KEY (subscription_id) REFERENCES subscriptions (subscription_id),
    CONSTRAINT fk_pay_user FOREIGN KEY (user_id)         REFERENCES users         (user_id)
) ENGINE=InnoDB
  COMMENT='Payment records. payment_status enum tests value matching. [EC-17]';


-- ============================================================
--  TABLE 18: play_events  (Polymorphic event log)
--  Stress patterns:
--    EC-02 (event_type string discriminator — value mapping required)
--    EC-03 (playlist_id IS NULL = played outside any playlist)
--    EC-05 (trk_position_ms abbreviated)
--    EC-07 (raw source; conflicts with daily_artist_metrics)
--    EC-08 (central hub of multi-hop join chains)
--
--  event_type values:
--    'play'  = user played a track (full or partial)
--    'skip'  = user skipped within first 30 seconds
--    'save'  = user bookmarked the track
--    'share' = user shared the track externally
--
--  NL "How many songs were played?" must map "played" to
--  event_type = 'play', not COUNT(*) on this table.
-- ============================================================
CREATE TABLE play_events (
    event_id        BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    user_id         INT UNSIGNED   NOT NULL,
    track_id        INT UNSIGNED   NOT NULL,
    playlist_id     INT UNSIGNED   NULL,                        -- [EC-03] NULL = outside playlist
    event_type      ENUM('play','skip','save','share') NOT NULL DEFAULT 'play', -- [EC-02]
    played_at       DATETIME       NOT NULL,
    trk_position_ms INT UNSIGNED   NOT NULL DEFAULT 0,          -- [EC-05] ms into track when event fired
    duration_ms     INT UNSIGNED   NOT NULL DEFAULT 0,          -- how long user actually listened
    country_code    CHAR(2)        NOT NULL,                    -- [EC-01] distinct from users.country (VPN/travel)
    device_type     ENUM('mobile','desktop','tablet','smart_tv','other') NOT NULL DEFAULT 'mobile',
    PRIMARY KEY (event_id),
    KEY idx_pe_user     (user_id),
    KEY idx_pe_track    (track_id),
    KEY idx_pe_playlist (playlist_id),
    KEY idx_pe_date     (played_at),
    KEY idx_pe_type     (event_type),
    KEY idx_pe_country  (country_code),
    CONSTRAINT fk_pe_user     FOREIGN KEY (user_id)     REFERENCES users      (user_id),
    CONSTRAINT fk_pe_track    FOREIGN KEY (track_id)    REFERENCES tracks     (track_id),
    CONSTRAINT fk_pe_playlist FOREIGN KEY (playlist_id) REFERENCES playlists  (playlist_id)
) ENGINE=InnoDB
  COMMENT='Polymorphic event log. event_type discriminator. playlist_id IS NULL = outside playlist. [EC-02, EC-03, EC-05, EC-07, EC-08]';


-- ============================================================
--  TABLE 19: daily_artist_metrics  (Pre-aggregated analytics)
--  Stress patterns:
--    EC-07 (stream_count 290,000x - 1,070,000x COUNT(play_events) — see the
--          header note; the intended "~5% ETL inflation" was never generated)
--    EC-16 (composite PK: artist_id + metric_date + country_code)
--
--  Composite PK tests GROUP BY completeness: queries on this table
--  must include all three key columns or produce wrong results.
--  Using BOTH this table AND play_events for the same question
--  causes double-counting — intentional ambiguity.
-- ============================================================
CREATE TABLE daily_artist_metrics (
    artist_id        INT UNSIGNED   NOT NULL,
    metric_date      DATE           NOT NULL,
    country_code     CHAR(2)        NOT NULL,
    stream_count     INT UNSIGNED   NOT NULL DEFAULT 0,         -- [EC-07] ~3e5 - 1e6 x raw
    skip_count       INT UNSIGNED   NOT NULL DEFAULT 0,
    save_count       INT UNSIGNED   NOT NULL DEFAULT 0,
    unique_listeners INT UNSIGNED   NOT NULL DEFAULT 0,
    avg_listen_pct   DECIMAL(5,2)   NOT NULL DEFAULT 0.00,
    PRIMARY KEY (artist_id, metric_date, country_code),         -- [EC-16] composite PK
    KEY idx_dam_date    (metric_date),
    KEY idx_dam_country (country_code),
    CONSTRAINT fk_dam_artist FOREIGN KEY (artist_id) REFERENCES artists (artist_id)
) ENGINE=InnoDB
  COMMENT='Pre-aggregated daily stats seeded at production scale; stream_count exceeds raw play_events by five to six orders of magnitude, not by 5%. Composite PK. [EC-07, EC-16]';


SET FOREIGN_KEY_CHECKS = 1;
