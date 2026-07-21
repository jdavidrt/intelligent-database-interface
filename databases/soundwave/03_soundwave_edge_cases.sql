-- ============================================================
--  SOUNDWAVE DB  |  Edge Case Queries (Runnable SQL)
--  NL2SQL Test Database for IDI Project
--  Universidad Nacional de Colombia  |  2026
-- ============================================================
--
--  Run AFTER: 01_soundwave_schema.sql + 02_soundwave_data.sql
--
--  30 queries covering 18 NL2SQL failure categories (EC-01..EC-18).
--  Each block contains:
--    -- [QXX] EC-XX  Difficulty: Easy/Medium/Hard/Extra Hard
--    -- NL: "The natural language question a manager would ask"
--    -- WHY HARD: The specific NL2SQL failure mode triggered
--    -- COMMON WRONG VERSION (where applicable): the typical mistake
-- ============================================================

USE soundwave_db;

-- ============================================================
--  TIER 1 — EASY / MEDIUM  (Spider baseline)
-- ============================================================

-- [Q01]  EC-01  Difficulty: Easy
-- NL: "Show me all artists from Colombia."
-- WHY HARD: 'country' exists in both artists and users.
--           The model must link to artists.country, not users.country.
SELECT
    artist_id,
    name,
    country,
    monthly_listeners_cached
FROM artists
WHERE country = 'CO';


-- [Q02]  EC-02  Difficulty: Easy
-- NL: "Which subscription plans include high-fidelity audio?"
-- WHY HARD: "high-fidelity audio" must map to has_hifi = 1 (integer flag).
--           No natural language synonym is stored in the schema.
SELECT
    name,
    monthly_price,
    plan_type,
    max_devices
FROM subscription_plans
WHERE has_hifi = 1;


-- [Q03]  EC-03  Difficulty: Easy
-- NL: "How many tracks have been released as standalone singles?"
-- WHY HARD: Requires IS NULL, not = NULL.
--           WHERE album_id = NULL always returns 0 in MySQL.
-- COMMON WRONG VERSION: SELECT COUNT(*) FROM tracks WHERE album_id = NULL;
SELECT COUNT(*) AS total_singles
FROM tracks
WHERE album_id IS NULL;


-- [Q04]  EC-17  Difficulty: Easy
-- NL: "How many times was each track played in 2024?"
-- WHY HARD: "played" must map to event_type = 'play'.
--           COUNT(*) from play_events without the filter includes
--           skips, saves, and shares — a wrong result that passes silently.
-- COMMON WRONG VERSION: SELECT track_id, COUNT(*) ... (no event_type filter)
SELECT
    t.title,
    COUNT(*) AS play_count
FROM play_events pe
JOIN tracks t ON pe.track_id = t.track_id
WHERE pe.event_type = 'play'
  AND YEAR(pe.played_at) = 2024
GROUP BY t.track_id, t.title
ORDER BY play_count DESC;


-- [Q05]  EC-01  Difficulty: Easy
-- NL: "List all albums released after 2022."
-- WHY HARD: 'title' exists in both albums and tracks.
--           'release_date' also exists in both.
--           The model must resolve to the albums table.
SELECT
    title,
    release_date,
    album_type
FROM albums
WHERE release_date > '2022-12-31'
ORDER BY release_date;


-- [Q06]  EC-06  Difficulty: Medium
-- NL: "What is the current monthly price for each subscription plan?"
-- WHY HARD: Requires pricing_history.effective_to IS NULL.
--           A naive JOIN to subscription_plans.monthly_price
--           returns the current listed price but ignores historical records.
--           The temporal SCD table is the authoritative source.
SELECT
    sp.name          AS plan_name,
    ph.monthly_price AS current_price,
    ph.effective_from
FROM subscription_plans sp
JOIN pricing_history ph ON sp.plan_id = ph.plan_id
WHERE ph.effective_to IS NULL
ORDER BY ph.monthly_price;


-- [Q07]  EC-08  Difficulty: Medium
-- NL: "Which users have listened to tracks by The Weeknd?"
-- WHY HARD: 4-table implicit join chain. The user never mentions
--           play_events or track_artists — both must be inferred.
SELECT DISTINCT
    u.display_name,
    u.country
FROM users u
JOIN play_events   pe ON u.user_id    = pe.user_id
JOIN track_artists ta ON pe.track_id  = ta.track_id
JOIN artists        a ON ta.artist_id = a.artist_id
WHERE a.name       = 'The Weeknd'
  AND pe.event_type = 'play';


-- [Q08]  EC-06  Difficulty: Medium
-- NL: "What subscription plan is each user currently on?"
-- WHY HARD: "currently" maps to subscription_periods.period_end IS NULL.
--           A model that queries subscriptions.status = 1 misses users
--           who are on a different plan period (e.g., post-upgrade).
SELECT
    u.display_name,
    p.name       AS plan_name,
    sp.monthly_fee,
    sp.period_start,
    DATEDIFF(CURDATE(), sp.period_start) AS days_on_plan
FROM subscription_periods sp
JOIN users              u ON sp.user_id = u.user_id
JOIN subscription_plans p ON sp.plan_id = p.plan_id
WHERE sp.period_end IS NULL
ORDER BY u.display_name;


-- [Q09]  EC-15  Difficulty: Medium
-- NL: "How many unique artists does each country's listeners follow?"
-- WHY HARD: Requires COUNT(DISTINCT artist_id), not COUNT(*).
--           A multi-artist track (track 10) means COUNT(*) overcounts.
SELECT
    u.country,
    COUNT(DISTINCT ufa.artist_id) AS unique_artists_followed
FROM users u
JOIN user_follows_artists ufa ON u.user_id = ufa.user_id
GROUP BY u.country
ORDER BY unique_artists_followed DESC;


-- [Q10]  EC-06 + EC-17  Difficulty: Medium
-- NL: "How much revenue did each plan generate in Q2 2023?"
-- WHY HARD: Temporal range filter + value matching.
--           Must filter payment_status = 'completed' to exclude
--           failed and refunded transactions.
SELECT
    sp.name          AS plan_name,
    SUM(pay.amount)  AS q2_2023_revenue,
    COUNT(*)         AS payment_count
FROM payments pay
JOIN subscriptions      s  ON pay.subscription_id = s.subscription_id
JOIN subscription_plans sp ON s.plan_id           = sp.plan_id
WHERE pay.payment_date   BETWEEN '2023-04-01' AND '2023-06-30'
  AND pay.payment_status = 'completed'
GROUP BY sp.plan_id, sp.name
ORDER BY q2_2023_revenue DESC;


-- ============================================================
--  TIER 2 — HARD  (Spider Hard)
-- ============================================================

-- [Q11]  EC-06 + EC-HAVING  Difficulty: Hard
-- NL: "Which artists had more than 5 distinct listeners per month in 2024?"
-- WHY HARD: HAVING clause confusion — "more than 5 distinct listeners"
--           must filter on an aggregated result (HAVING), not on raw rows (WHERE).
--           Also requires COUNT(DISTINCT) not COUNT(*).
SELECT
    a.name                                     AS artist_name,
    DATE_FORMAT(pe.played_at, '%Y-%m')         AS stream_month,
    COUNT(DISTINCT pe.user_id)                 AS unique_listeners
FROM artists        a
JOIN track_artists ta ON a.artist_id = ta.artist_id
JOIN play_events   pe ON ta.track_id = pe.track_id
WHERE YEAR(pe.played_at)  = 2024
  AND pe.event_type       = 'play'
GROUP BY a.artist_id, a.name, stream_month
HAVING COUNT(DISTINCT pe.user_id) > 5
ORDER BY stream_month, unique_listeners DESC;


-- [Q12]  EC-14  Difficulty: Hard
-- NL: "Find users who follow at least one artist but have never
--      listened to any music by those specific artists."
-- WHY HARD: Anti-join with a correlated condition.
--           NOT EXISTS must be correlated on BOTH user_id AND artist_id.
--           A flat NOT IN would not capture the per-artist relationship.
--           Seed: user 7 follows Kendrick (artist 6) with zero Kendrick plays.
SELECT DISTINCT
    u.display_name,
    u.country
FROM users u
JOIN user_follows_artists ufa ON u.user_id = ufa.user_id
WHERE NOT EXISTS (
    SELECT 1
    FROM play_events   pe
    JOIN track_artists ta ON pe.track_id  = ta.track_id
    WHERE pe.user_id   = u.user_id
      AND ta.artist_id = ufa.artist_id
);


-- [Q13]  EC-09  Difficulty: Hard
-- NL: "Show each referred user alongside the display name of
--      who referred them."
-- WHY HARD: Self-join on users.referred_by_user_id.
--           Model must alias the same table twice.
SELECT
    u.display_name   AS referred_user,
    u.country        AS referred_country,
    r.display_name   AS referred_by,
    u.joined_at
FROM users u
JOIN users r ON u.referred_by_user_id = r.user_id
ORDER BY u.joined_at;


-- [Q14]  EC-04  Difficulty: Hard
-- NL: "List all genres that are sub-genres of Rock."
-- WHY HARD: Requires a self-join on genres.parent_genre_id.
--           The model must recognize that genre hierarchy
--           is stored in the same table, not a separate lookup.
SELECT
    child.name  AS subgenre,
    parent.name AS parent_genre
FROM genres child
JOIN genres parent ON child.parent_genre_id = parent.genre_id
WHERE parent.name = 'Rock';


-- [Q15]  EC-10  Difficulty: Hard
-- NL: "Which tracks have more plays than the average for their genre?"
-- WHY HARD: Correlated subquery. The average must be computed
--           per genre (inner query references outer genre_id).
--           A non-correlated version computes the global average —
--           syntactically identical but semantically wrong.
SELECT
    t.title,
    g.name      AS genre_name,
    t.total_plays
FROM tracks       t
JOIN track_genres tg ON t.track_id  = tg.track_id
JOIN genres        g ON tg.genre_id = g.genre_id
WHERE t.total_plays > (
    SELECT AVG(t2.total_plays)
    FROM tracks        t2
    JOIN track_genres tg2 ON t2.track_id  = tg2.track_id
    WHERE tg2.genre_id = tg.genre_id     -- correlated reference
)
ORDER BY g.name, t.total_plays DESC;


-- [Q16]  EC-01 + EC-02  Difficulty: Hard
-- NL: "How many users signed up through each acquisition channel in 2023?"
-- WHY HARD: usr_acq_src is an abbreviated column name AND an integer code.
--           The model must map the column AND decode the values.
--           The CASE statement requires knowing all four codes.
SELECT
    CASE u.usr_acq_src
        WHEN 1 THEN 'Organic'
        WHEN 2 THEN 'Social Media'
        WHEN 3 THEN 'Referral'
        WHEN 4 THEN 'Ad Campaign'
        ELSE 'Unknown'
    END          AS acquisition_channel,
    COUNT(*)     AS new_users_2023
FROM users u
WHERE YEAR(u.joined_at) = 2023
GROUP BY u.usr_acq_src
ORDER BY new_users_2023 DESC;


-- [Q17]  EC-01  Difficulty: Hard
-- NL: "Which playlists contain tracks that are NOT in any album
--      (standalone singles)?"
-- WHY HARD: EC-03 IS NULL filter must be applied mid-join.
--           EC-08 multi-hop join required.
--           Misidentifying tracks.album_id = NULL as albums.album_id
--           is a schema-linking error.
SELECT DISTINCT
    pl.name           AS playlist_name,
    pl.playlist_type,
    t.title           AS single_title
FROM playlists       pl
JOIN playlist_tracks pt ON pl.playlist_id = pt.playlist_id
JOIN tracks           t ON pt.track_id    = t.track_id
WHERE t.album_id IS NULL
ORDER BY pl.name;


-- ============================================================
--  TIER 3 — EXTRA HARD  (Spider Extra Hard)
-- ============================================================

-- [Q18]  EC-08 + WINDOW  Difficulty: Extra Hard
-- NL: "Rank each artist by total streams within their primary genre."
-- WHY HARD: 5-table join chain + WINDOW function + is_prim flag.
--           is_prim is abbreviated (EC-05) and must equal 1
--           to filter only the primary genre.
SELECT
    a.name                                     AS artist_name,
    g.name                                     AS primary_genre,
    COUNT(pe.event_id)                         AS total_streams,
    RANK() OVER (
        PARTITION BY g.genre_id
        ORDER BY COUNT(pe.event_id) DESC
    )                                          AS genre_rank
FROM artists        a
JOIN artist_genres ag ON a.artist_id = ag.artist_id AND ag.is_prim = 1
JOIN genres         g ON ag.genre_id  = g.genre_id
JOIN track_artists ta ON a.artist_id  = ta.artist_id
JOIN play_events   pe ON ta.track_id  = pe.track_id
WHERE pe.event_type = 'play'
GROUP BY a.artist_id, a.name, g.genre_id, g.name;


-- [Q19]  EC-01 + NESTED AGG  Difficulty: Extra Hard
-- NL: "What is the average number of monthly plays per artist
--      across all months on record?"
-- WHY HARD: Nested aggregation — SUM per month per artist (inner),
--           then AVG across months (outer).
--           A flat AVG(COUNT(*)) is invalid SQL without subquery.
SELECT
    artist_name,
    AVG(monthly_plays) AS avg_monthly_plays
FROM (
    SELECT
        a.name                              AS artist_name,
        DATE_FORMAT(pe.played_at, '%Y-%m') AS ym,
        COUNT(*)                            AS monthly_plays
    FROM artists        a
    JOIN track_artists ta ON a.artist_id = ta.artist_id
    JOIN play_events   pe ON ta.track_id = pe.track_id
    WHERE pe.event_type = 'play'
    GROUP BY a.artist_id, a.name, ym
) monthly_totals
GROUP BY artist_name
ORDER BY avg_monthly_plays DESC;


-- [Q20]  EC-07  Difficulty: Extra Hard
-- NL: "Compare total stream counts from the analytics table vs
--      raw play events for Karol G in 2024."
-- WHY HARD: Two valid sources give different numbers — by a factor of roughly
--           290,000 to 1,070,000, not the "~5% gap" this comment claimed until
--           2026-07-21. Both answers are "correct" depending on the source.
--           This exposes the pre-aggregated vs raw ambiguity.
--           Expected result: metrics_table > raw_play_events.
SELECT 'metrics_table'   AS source,
       SUM(dam.stream_count) AS total_streams
FROM daily_artist_metrics dam
JOIN artists a ON dam.artist_id = a.artist_id
WHERE a.name = 'Karol G'
  AND YEAR(dam.metric_date) = 2024

UNION ALL

SELECT 'raw_play_events' AS source,
       COUNT(*)              AS total_streams
FROM play_events   pe
JOIN track_artists ta ON pe.track_id  = ta.track_id
JOIN artists        a ON ta.artist_id = a.artist_id
WHERE a.name         = 'Karol G'
  AND pe.event_type  = 'play'
  AND YEAR(pe.played_at) = 2024;


-- [Q21]  EC-02 + YoY  Difficulty: Extra Hard
-- NL: "Which artists grew their total streams by more than 20%
--      from 2023 to 2024?"
-- WHY HARD: YoY comparison requires two separate aggregations
--           joined on artist_id — a temporal self-join pattern.
--           Division by zero must be avoided if 2023 has 0 streams.
SELECT
    curr.artist_name,
    prev.total_streams                  AS streams_2023,
    curr.total_streams                  AS streams_2024,
    ROUND(
        (curr.total_streams - prev.total_streams)
        / prev.total_streams * 100, 2
    )                                   AS yoy_growth_pct
FROM (
    SELECT a.artist_id,
           a.name AS artist_name,
           COUNT(*) AS total_streams
    FROM artists        a
    JOIN track_artists ta ON a.artist_id = ta.artist_id
    JOIN play_events   pe ON ta.track_id  = pe.track_id
    WHERE pe.event_type = 'play'
      AND YEAR(pe.played_at) = 2024
    GROUP BY a.artist_id, a.name
) curr
JOIN (
    SELECT a.artist_id,
           COUNT(*) AS total_streams
    FROM artists        a
    JOIN track_artists ta ON a.artist_id = ta.artist_id
    JOIN play_events   pe ON ta.track_id  = pe.track_id
    WHERE pe.event_type = 'play'
      AND YEAR(pe.played_at) = 2023
    GROUP BY a.artist_id
) prev ON curr.artist_id = prev.artist_id
WHERE (curr.total_streams - prev.total_streams) / prev.total_streams > 0.20
ORDER BY yoy_growth_pct DESC;


-- [Q22]  EC-11 + EC-03  Difficulty: Extra Hard
-- NL: "What percentage of all tracks have never been played?"
-- WHY HARD: LEFT JOIN + IS NULL anti-join pattern.
--           Must also filter event_type = 'play' inside the LEFT JOIN
--           condition, not in WHERE — otherwise the outer join collapses.
--           Second trap, and the reason this query was corrected on
--           2026-07-21: the LEFT JOIN fans out to one row per play event, so
--           a bare COUNT(*) counts events (963), not tracks (48). Every
--           track-level figure must therefore be COUNT(DISTINCT track_id).
--           The percentage happens to survive the bug only because the
--           numerator is currently 0 — a wrong query that looks right is
--           exactly the failure class this suite exists to catch.
SELECT
    COUNT(DISTINCT t.track_id)                                       AS total_tracks,
    COUNT(DISTINCT CASE WHEN pe.event_id IS NULL THEN t.track_id END) AS never_played,
    ROUND(
        COUNT(DISTINCT CASE WHEN pe.event_id IS NULL THEN t.track_id END) * 100.0
        / COUNT(DISTINCT t.track_id), 2
    )                                                                AS pct_never_played
FROM tracks t
LEFT JOIN play_events pe
    ON t.track_id = pe.track_id AND pe.event_type = 'play';


-- [Q23]  EC-04 + EC-01  Difficulty: Extra Hard
-- NL: "How many plays did tracks in the Latin genre and all
--      its sub-genres receive in 2024?"
-- WHY HARD: Genre hierarchy (EC-04) must be traversed.
--           'Latin' is a root genre; sub-genres Reggaeton and Salsa
--           must be included. The model must join genres to itself.
SELECT
    g.name             AS genre_or_subgenre,
    COUNT(pe.event_id) AS plays_2024
FROM genres        g
JOIN track_genres tg ON g.genre_id  = tg.genre_id
JOIN play_events  pe ON tg.track_id = pe.track_id
WHERE pe.event_type = 'play'
  AND YEAR(pe.played_at) = 2024
  AND (
      g.genre_id = (SELECT genre_id FROM genres WHERE name = 'Latin')
      OR g.parent_genre_id = (SELECT genre_id FROM genres WHERE name = 'Latin')
  )
GROUP BY g.genre_id, g.name
ORDER BY plays_2024 DESC;


-- [Q24]  EC-06  Difficulty: Extra Hard
-- NL: "What subscription plan was each user on during Q3 2023?"
-- WHY HARD: Temporal overlap logic — the SCD period must
--           overlap with the query range, not just start before it.
--           IS NULL must be handled in the range condition.
SELECT
    u.display_name,
    p.name                                   AS plan_name,
    sp.period_start,
    COALESCE(CAST(sp.period_end AS CHAR), 'ongoing') AS period_end,
    sp.monthly_fee
FROM subscription_periods sp
JOIN users              u ON sp.user_id = u.user_id
JOIN subscription_plans p ON sp.plan_id = p.plan_id
WHERE sp.period_start <= '2023-09-30'
  AND (sp.period_end IS NULL OR sp.period_end >= '2023-07-01')
ORDER BY u.display_name;


-- [Q25]  EC-15 + EC-13  Difficulty: Extra Hard
-- NL: "Which genres have a skip rate above 10% of total interactions?"
-- WHY HARD: Conditional aggregation + HAVING + percentage calculation.
--           DISTINCT user counting vs raw event counting both valid
--           depending on interpretation of "rate."
SELECT
    g.name                                                             AS genre_name,
    COUNT(*)                                                           AS total_events,
    SUM(CASE WHEN pe.event_type = 'skip' THEN 1 ELSE 0 END)           AS skip_count,
    ROUND(
        SUM(CASE WHEN pe.event_type = 'skip' THEN 1 ELSE 0 END) * 100.0
        / COUNT(*), 2
    )                                                                  AS skip_rate_pct
FROM genres         g
JOIN track_genres  tg ON g.genre_id  = tg.genre_id
JOIN play_events   pe ON tg.track_id = pe.track_id
GROUP BY g.genre_id, g.name
HAVING SUM(CASE WHEN pe.event_type = 'skip' THEN 1 ELSE 0 END) * 100.0
       / COUNT(*) > 10.0
ORDER BY skip_rate_pct DESC;


-- [Q26]  EC-08  Difficulty: Extra Hard
-- NL: "Which curated playlists contain songs by artists from Colombia?"
-- WHY HARD: 5-table join chain traversed fully.
--           playlist_type = 'curated' is a value-matching filter (EC-02).
--           artists.country = 'CO' shares the column name with users.country (EC-01).
SELECT DISTINCT
    pl.name           AS playlist_name,
    a.name            AS artist_name,
    a.country         AS artist_country
FROM playlists      pl
JOIN playlist_tracks pt ON pl.playlist_id = pt.playlist_id
JOIN tracks          t  ON pt.track_id    = t.track_id
JOIN track_artists   ta ON t.track_id     = ta.track_id
JOIN artists          a ON ta.artist_id   = a.artist_id
WHERE pl.playlist_type = 'curated'
  AND a.country        = 'CO'
ORDER BY pl.name;


-- [Q27]  EC-04  Difficulty: Extra Hard
-- NL: "Which forked playlists contain tracks that are not in
--      their original source playlist?"
-- WHY HARD: Self-join on playlists.forked_from_id (EC-04)
--           combined with a correlated NOT EXISTS anti-join (EC-14).
--           Requires understanding playlist lineage and set difference.
SELECT
    fp.name            AS forked_playlist,
    t.title            AS track_not_in_original,
    op.name            AS original_playlist
FROM playlists         fp
JOIN playlists         op  ON fp.forked_from_id = op.playlist_id
JOIN playlist_tracks   fpt ON fp.playlist_id    = fpt.playlist_id
JOIN tracks             t  ON fpt.track_id      = t.track_id
WHERE NOT EXISTS (
    SELECT 1
    FROM playlist_tracks opt
    WHERE opt.playlist_id = op.playlist_id
      AND opt.track_id    = fpt.track_id
)
ORDER BY fp.name;


-- [Q28]  EC-02 + WINDOW  Difficulty: Extra Hard
-- NL: "For each user acquisition channel, which artist was
--      streamed most in 2024?"
-- WHY HARD: Decoding usr_acq_src integer codes (EC-02) +
--           RANK() window function within partition +
--           5-table multi-hop chain.
SELECT
    acq_label,
    artist_name,
    stream_count
FROM (
    SELECT
        CASE u.usr_acq_src
            WHEN 1 THEN 'Organic'
            WHEN 2 THEN 'Social Media'
            WHEN 3 THEN 'Referral'
            WHEN 4 THEN 'Ad Campaign'
        END                    AS acq_label,
        a.name                 AS artist_name,
        COUNT(*)               AS stream_count,
        RANK() OVER (
            PARTITION BY u.usr_acq_src
            ORDER BY COUNT(*) DESC
        )                      AS rnk
    FROM users         u
    JOIN play_events   pe ON u.user_id    = pe.user_id
    JOIN track_artists ta ON pe.track_id  = ta.track_id
    JOIN artists        a ON ta.artist_id = a.artist_id
    WHERE pe.event_type   = 'play'
      AND YEAR(pe.played_at) = 2024
    GROUP BY u.usr_acq_src, a.artist_id, a.name
) ranked
WHERE rnk = 1
ORDER BY acq_label;


-- [Q29]  EC-12  Difficulty: Extra Hard
-- NL: "What is the second most-streamed genre in 2024?"
-- WHY HARD: Ordinal reference ("second") requires DENSE_RANK.
--           LIMIT 1 OFFSET 1 misses ties.
--           Returning the wrong ordinal (e.g., 3rd instead of 2nd)
--           is a silent semantic error.
SELECT
    genre_name,
    total_streams
FROM (
    SELECT
        g.name                  AS genre_name,
        COUNT(*)                AS total_streams,
        DENSE_RANK() OVER (ORDER BY COUNT(*) DESC) AS rnk
    FROM genres        g
    JOIN track_genres tg ON g.genre_id  = tg.genre_id
    JOIN play_events  pe ON tg.track_id = pe.track_id
    WHERE pe.event_type    = 'play'
      AND YEAR(pe.played_at) = 2024
    GROUP BY g.genre_id, g.name
) ranked
WHERE rnk = 2;


-- [Q30]  EC-18  Difficulty: Extra Hard  (Compositional maximum)
-- NL: "Find artists whose unique monthly listeners grew more than 30%
--      from Q3 2023 to Q3 2024, excluding artists with fewer than
--      3 total events in Q3 2023, ranked by growth rate."
-- WHY HARD: Combines EC-08 (multi-hop), EC-15 (COUNT DISTINCT),
--           EC-06 (HAVING filter), EC-05 (comparative threshold),
--           EC-18 (novel composition not seen in training).
--           Four separate complexity patterns in one query.
SELECT
    curr.artist_name,
    prev.q3_listeners       AS listeners_q3_2023,
    curr.q3_listeners       AS listeners_q3_2024,
    ROUND(
        (curr.q3_listeners - prev.q3_listeners)
        / prev.q3_listeners * 100, 2
    )                       AS growth_pct
FROM (
    SELECT
        a.artist_id,
        a.name                         AS artist_name,
        COUNT(DISTINCT pe.user_id)     AS q3_listeners
    FROM artists        a
    JOIN track_artists ta ON a.artist_id = ta.artist_id
    JOIN play_events   pe ON ta.track_id  = pe.track_id
    WHERE pe.event_type  = 'play'
      AND pe.played_at BETWEEN '2024-07-01' AND '2024-09-30'
    GROUP BY a.artist_id, a.name
) curr
JOIN (
    SELECT
        a.artist_id,
        COUNT(DISTINCT pe.user_id) AS q3_listeners
    FROM artists        a
    JOIN track_artists ta ON a.artist_id = ta.artist_id
    JOIN play_events   pe ON ta.track_id  = pe.track_id
    WHERE pe.event_type  = 'play'
      AND pe.played_at BETWEEN '2023-07-01' AND '2023-09-30'
    GROUP BY a.artist_id
    HAVING COUNT(*) >= 3                  -- exclude low-volume artists
) prev ON curr.artist_id = prev.artist_id
WHERE (curr.q3_listeners - prev.q3_listeners)
      / prev.q3_listeners > 0.30
ORDER BY growth_pct DESC;
