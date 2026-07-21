# Soundwave DB — Edge Case Query Catalog
## NL2SQL Failure Mode Reference for IDI Project
**Universidad Nacional de Colombia — Computer and Systems Engineering Thesis — 2026**

---

## How to Read This Document

Each query entry contains:

| Field | Description |
|---|---|
| **ID** | Query identifier (Q01–Q30) |
| **EC** | Edge case code(s) from the failure taxonomy |
| **Tier** | Spider difficulty tier (Easy / Medium / Hard / Extra Hard) |
| **NL Question** | The natural language question a manager would ask |
| **Why Hard** | The specific NL2SQL failure mode triggered |
| **Common Wrong Version** | The syntactically valid but semantically wrong SQL a model typically generates |
| **Correct SQL** | The ground-truth query |

The runnable versions of all queries are in `03_soundwave_edge_cases.sql`.

---

## Edge Case Code Reference

| Code | Failure Category | Primary Tables |
|---|---|---|
| EC-01 | Ambiguous column names across tables | `name` (5 tables), `title`, `release_date`, `country`, `status` |
| EC-02 | Coded / enumerated values | `plan_type`, `status`, `usr_acq_src`, `event_type` |
| EC-03 | Nullable foreign keys | `tracks.album_id`, `users.referred_by_user_id`, `play_events.playlist_id` |
| EC-04 | Self-referential relationships | `genres.parent_genre_id`, `users.referred_by_user_id`, `playlists.forked_from_id` |
| EC-05 | Abbreviated column names | `trk_dur_ms`, `is_exp`, `is_prim`, `usr_acq_src`, `trk_position_ms` |
| EC-06 | Temporal SCD (Slowly Changing Dimensions) | `pricing_history`, `subscription_periods`, `subscriptions` |
| EC-07 | Pre-aggregated vs raw ambiguity | `daily_artist_metrics` vs `play_events`; `tracks.total_plays` vs COUNT |
| EC-08 | Multi-hop / implicit junction joins | 5-table chain: playlists→playlist_tracks→tracks→track_artists→artists |
| EC-09 | Self-joins | Temporal YoY comparison; user referral chain |
| EC-10 | Correlated subqueries | Per-group averages; per-artist comparisons |
| EC-11 | NULL handling in aggregations | LEFT JOIN + IS NULL anti-join; COUNT(*) vs COUNT(col) |
| EC-12 | Ordinal references | "Second most," "top 3," DENSE_RANK vs LIMIT OFFSET |
| EC-13 | Superlative queries | "Most popular," "highest," tie-handling |
| EC-14 | Negation / anti-join | NOT EXISTS, NOT IN, LEFT JOIN IS NULL |
| EC-15 | COUNT DISTINCT vs COUNT | Multi-artist tracks; unique vs total |
| EC-16 | GROUP BY correctness | Composite PK `daily_artist_metrics`; non-aggregated columns |
| EC-17 | Value matching / string filtering | `payment_status`, `playlist_type`, `event_type` enum values |
| EC-18 | Compositional generalization | Multiple patterns combined in novel configurations |

---

## Tier 1 — Easy / Medium

---

### Q01 — Schema Linking Ambiguity

| | |
|---|---|
| **EC** | EC-01 |
| **Tier** | Easy |
| **NL** | "Show me all artists from Colombia." |
| **Why Hard** | The column `country` exists in both `artists` and `users`. A schema linker must resolve to `artists.country`, not `users.country`. On a database with many tables sharing the same column name, this is the #1 source of errors (27–68% of failures per Spider 2.0). |
| **Common Wrong Version** | `SELECT * FROM users WHERE country = 'CO'` (wrong table) |

**Correct SQL:**
```sql
SELECT artist_id, name, country, monthly_listeners_cached
FROM artists
WHERE country = 'CO';
```

---

### Q02 — Coded Value Mapping

| | |
|---|---|
| **EC** | EC-02 |
| **Tier** | Easy |
| **NL** | "Which subscription plans include high-fidelity audio?" |
| **Why Hard** | "High-fidelity audio" must map to `has_hifi = 1`. No synonym is stored in the schema. The model must reason about domain meaning without textual anchors in the data. |
| **Common Wrong Version** | `WHERE plan_type = 'hifi'` or `WHERE name LIKE '%hi-fi%'` (both return empty or error) |

**Correct SQL:**
```sql
SELECT name, monthly_price, plan_type, max_devices
FROM subscription_plans
WHERE has_hifi = 1;
```

---

### Q03 — NULL Handling (IS NULL vs = NULL)

| | |
|---|---|
| **EC** | EC-03 |
| **Tier** | Easy |
| **NL** | "How many tracks have been released as standalone singles?" |
| **Why Hard** | Requires `IS NULL`, not `= NULL`. In MySQL, `column = NULL` always evaluates to UNKNOWN (never TRUE), so the wrong version always returns 0. This is a silent error — no syntax warning, just a wrong count. |
| **Common Wrong Version** | `SELECT COUNT(*) FROM tracks WHERE album_id = NULL` → **always returns 0** |

**Correct SQL:**
```sql
SELECT COUNT(*) AS total_singles
FROM tracks
WHERE album_id IS NULL;
```

---

### Q04 — Polymorphic Event Type (Value Mapping)

| | |
|---|---|
| **EC** | EC-17 |
| **Tier** | Easy |
| **NL** | "How many times was each track played in 2024?" |
| **Why Hard** | `play_events` is a polymorphic table with `event_type` as a discriminator. `COUNT(*)` without the `event_type = 'play'` filter counts skips, saves, and shares too — inflating the result silently. |
| **Common Wrong Version** | `SELECT track_id, COUNT(*) FROM play_events WHERE YEAR(played_at) = 2024 GROUP BY track_id` (overcounts by ~15%) |

**Correct SQL:**
```sql
SELECT t.title, COUNT(*) AS play_count
FROM play_events pe
JOIN tracks t ON pe.track_id = t.track_id
WHERE pe.event_type = 'play'
  AND YEAR(pe.played_at) = 2024
GROUP BY t.track_id, t.title
ORDER BY play_count DESC;
```

---

### Q05 — Column Name Collision (title + release_date)

| | |
|---|---|
| **EC** | EC-01 |
| **Tier** | Easy |
| **NL** | "List all albums released after 2022." |
| **Why Hard** | `title` and `release_date` exist in both `albums` and `tracks`. The model must resolve to the `albums` table. Without context, schema linkers often pick the first table in alphabetical order. |
| **Common Wrong Version** | `SELECT title, release_date FROM tracks WHERE release_date > '2022-12-31'` (wrong table) |

**Correct SQL:**
```sql
SELECT title, release_date, album_type
FROM albums
WHERE release_date > '2022-12-31'
ORDER BY release_date;
```

---

### Q06 — Temporal SCD (Current Price)

| | |
|---|---|
| **EC** | EC-06 |
| **Tier** | Medium |
| **NL** | "What is the current monthly price for each subscription plan?" |
| **Why Hard** | The `subscription_plans.monthly_price` column holds the current listed price, but the authoritative source is `pricing_history` where `effective_to IS NULL`. A model that reads only from `subscription_plans` gets the right answer today, but a model that must reason about temporal SCD must use the history table. This tests whether the system understands "current" means `effective_to IS NULL`. |
| **Common Wrong Version** | `SELECT name, monthly_price FROM subscription_plans` (ignores price history table entirely) |

**Correct SQL:**
```sql
SELECT sp.name AS plan_name, ph.monthly_price AS current_price, ph.effective_from
FROM subscription_plans sp
JOIN pricing_history ph ON sp.plan_id = ph.plan_id
WHERE ph.effective_to IS NULL
ORDER BY ph.monthly_price;
```

---

### Q07 — 4-Table Implicit Multi-Hop Join

| | |
|---|---|
| **EC** | EC-08 |
| **Tier** | Medium |
| **NL** | "Which users have listened to tracks by The Weeknd?" |
| **Why Hard** | The join chain `users → play_events → track_artists → artists` must be traversed without any table being named in the question. The model must infer all three bridge tables from semantic understanding of the schema. |
| **Common Wrong Version** | Missing `track_artists` or joining `albums` instead — both produce either errors or incomplete results |

**Correct SQL:**
```sql
SELECT DISTINCT u.display_name, u.country
FROM users         u
JOIN play_events   pe ON u.user_id    = pe.user_id
JOIN track_artists ta ON pe.track_id  = ta.track_id
JOIN artists        a ON ta.artist_id = a.artist_id
WHERE a.name        = 'The Weeknd'
  AND pe.event_type = 'play';
```

---

### Q08 — Current Subscription via SCD

| | |
|---|---|
| **EC** | EC-06 |
| **Tier** | Medium |
| **NL** | "What subscription plan is each user currently on?" |
| **Why Hard** | "Currently" maps to `subscription_periods.period_end IS NULL`. A model querying `subscriptions.status = 1` may work for simple cases but misses users who changed plans — since `subscription_periods` is the SCD table tracking all plan intervals. |
| **Common Wrong Version** | `SELECT u.name, sp.name FROM users u JOIN subscriptions s ... WHERE s.status = 1` (misses plan changes) |

**Correct SQL:**
```sql
SELECT u.display_name, p.name AS plan_name, sp.monthly_fee, sp.period_start,
       DATEDIFF(CURDATE(), sp.period_start) AS days_on_plan
FROM subscription_periods  sp
JOIN users              u ON sp.user_id = u.user_id
JOIN subscription_plans p ON sp.plan_id = p.plan_id
WHERE sp.period_end IS NULL
ORDER BY u.display_name;
```

---

### Q09 — COUNT DISTINCT vs COUNT

| | |
|---|---|
| **EC** | EC-15 |
| **Tier** | Medium |
| **NL** | "How many unique artists does each country's listeners follow?" |
| **Why Hard** | `COUNT(*)` would count follow relationships (rows), not distinct artists. If a user from US follows the same artist twice (data anomaly) or the model joins incorrectly, the count inflates. The word "unique" signals `COUNT(DISTINCT)` — but NL2SQL models often drop the DISTINCT keyword. |
| **Common Wrong Version** | `COUNT(ufa.artist_id)` instead of `COUNT(DISTINCT ufa.artist_id)` |

**Correct SQL:**
```sql
SELECT u.country, COUNT(DISTINCT ufa.artist_id) AS unique_artists_followed
FROM users u
JOIN user_follows_artists ufa ON u.user_id = ufa.user_id
GROUP BY u.country
ORDER BY unique_artists_followed DESC;
```

---

### Q10 — Temporal + Value Filter (Revenue by Plan per Quarter)

| | |
|---|---|
| **EC** | EC-06 + EC-17 |
| **Tier** | Medium |
| **NL** | "How much revenue did each plan generate in Q2 2023?" |
| **Why Hard** | Two hard patterns combined: date range filter + `payment_status = 'completed'` value matching. Omitting the status filter includes failed and refunded payments in the revenue total. |
| **Common Wrong Version** | `SUM(amount)` without filtering `payment_status = 'completed'` — inflates revenue by ~5–10% |

**Correct SQL:**
```sql
SELECT sp.name AS plan_name, SUM(pay.amount) AS q2_2023_revenue
FROM payments pay
JOIN subscriptions      s  ON pay.subscription_id = s.subscription_id
JOIN subscription_plans sp ON s.plan_id           = sp.plan_id
WHERE pay.payment_date   BETWEEN '2023-04-01' AND '2023-06-30'
  AND pay.payment_status = 'completed'
GROUP BY sp.plan_id, sp.name
ORDER BY q2_2023_revenue DESC;
```

---

## Tier 2 — Hard

---

### Q11 — HAVING vs WHERE Confusion

| | |
|---|---|
| **EC** | EC-HAVING + EC-15 |
| **Tier** | Hard |
| **NL** | "Which artists had more than 5 distinct listeners per month in 2024?" |
| **Why Hard** | The filter "more than 5 distinct listeners" must apply to an aggregated result (HAVING), not to individual rows (WHERE). Models frequently generate `WHERE COUNT(DISTINCT pe.user_id) > 5` which is invalid SQL, or they use `WHERE user_id > 5` which is a semantic error. |
| **Common Wrong Version** | `WHERE COUNT(DISTINCT pe.user_id) > 5` — syntax error; or `HAVING COUNT(*) > 5` — overcounts (non-distinct) |

**Correct SQL:**
```sql
SELECT a.name AS artist_name,
       DATE_FORMAT(pe.played_at, '%Y-%m') AS stream_month,
       COUNT(DISTINCT pe.user_id) AS unique_listeners
FROM artists a
JOIN track_artists ta ON a.artist_id = ta.artist_id
JOIN play_events   pe ON ta.track_id = pe.track_id
WHERE YEAR(pe.played_at) = 2024 AND pe.event_type = 'play'
GROUP BY a.artist_id, a.name, stream_month
HAVING COUNT(DISTINCT pe.user_id) > 5
ORDER BY stream_month, unique_listeners DESC;
```

---

### Q12 — Correlated Anti-Join (Negation + Multi-Hop)

| | |
|---|---|
| **EC** | EC-14 |
| **Tier** | Hard |
| **NL** | "Find users who follow at least one artist but have never listened to any music by those specific artists." |
| **Why Hard** | The NOT EXISTS must be correlated on BOTH `user_id` AND `artist_id`. A flat `NOT IN (SELECT user_id FROM play_events)` would find users with zero plays total — a completely different (wrong) result. Canonical seed row: user 7 (Nina) follows Kendrick Lamar but has zero Kendrick plays. |
| **Common Wrong Version** | `WHERE user_id NOT IN (SELECT user_id FROM play_events)` — finds only users with zero plays at all |

**Correct SQL:**
```sql
SELECT DISTINCT u.display_name, u.country
FROM users u
JOIN user_follows_artists ufa ON u.user_id = ufa.user_id
WHERE NOT EXISTS (
    SELECT 1
    FROM play_events   pe
    JOIN track_artists ta ON pe.track_id  = ta.track_id
    WHERE pe.user_id   = u.user_id
      AND ta.artist_id = ufa.artist_id
);
```

---

### Q13 — Self-Join (User Referral Chain)

| | |
|---|---|
| **EC** | EC-09 |
| **Tier** | Hard |
| **NL** | "Show each referred user alongside the display name of who referred them." |
| **Why Hard** | Self-join on `users.referred_by_user_id`. The model must alias the same table as two different roles and never produces this pattern for a table with a single semantic name ("users"). |
| **Common Wrong Version** | Joining a non-existent `referrers` table; or joining `users` to itself with matching `user_id = user_id` (wrong condition) |

**Correct SQL:**
```sql
SELECT u.display_name AS referred_user, u.country AS referred_country,
       r.display_name AS referred_by, u.joined_at
FROM users u
JOIN users r ON u.referred_by_user_id = r.user_id
ORDER BY u.joined_at;
```

---

### Q14 — Hierarchical Self-Join (Genre Taxonomy)

| | |
|---|---|
| **EC** | EC-04 |
| **Tier** | Hard |
| **NL** | "List all genres that are sub-genres of Rock." |
| **Why Hard** | Requires a self-join on `genres.parent_genre_id`. The model must recognize that the hierarchy is stored in the same table. Models rarely generate self-joins spontaneously, and depth-2 or recursive traversal is even less common. |
| **Common Wrong Version** | `WHERE genre_id IN (SELECT genre_id FROM genres WHERE name = 'Rock')` — returns only Rock itself, not its children |

**Correct SQL:**
```sql
SELECT child.name AS subgenre, parent.name AS parent_genre
FROM genres child
JOIN genres parent ON child.parent_genre_id = parent.genre_id
WHERE parent.name = 'Rock';
```

---

### Q15 — Correlated Subquery (Per-Genre Average)

| | |
|---|---|
| **EC** | EC-10 |
| **Tier** | Hard |
| **NL** | "Which tracks have more plays than the average for their genre?" |
| **Why Hard** | The average must be computed per-genre (inner query references outer `genre_id`). A non-correlated subquery computes the global average instead — same syntax, completely different semantics. This is undetectable without running the query. |
| **Common Wrong Version** | `WHERE total_plays > (SELECT AVG(total_plays) FROM tracks)` — computes global average, not per-genre |

**Correct SQL:**
```sql
SELECT t.title, g.name AS genre_name, t.total_plays
FROM tracks t
JOIN track_genres tg ON t.track_id  = tg.track_id
JOIN genres        g ON tg.genre_id = g.genre_id
WHERE t.total_plays > (
    SELECT AVG(t2.total_plays)
    FROM tracks t2
    JOIN track_genres tg2 ON t2.track_id = tg2.track_id
    WHERE tg2.genre_id = tg.genre_id   -- correlated reference
)
ORDER BY g.name, t.total_plays DESC;
```

---

### Q16 — Abbreviated + Coded Column Decoding

| | |
|---|---|
| **EC** | EC-01 + EC-02 |
| **Tier** | Hard |
| **NL** | "How many users signed up through each acquisition channel in 2023?" |
| **Why Hard** | `usr_acq_src` is both abbreviated (EC-05) and integer-coded (EC-02). The model must resolve the column name AND know that 1=organic, 2=social, 3=referral, 4=ad. Neither fact is present in the schema text — it requires column descriptions (external knowledge per BIRD benchmark). |
| **Common Wrong Version** | `GROUP BY usr_acq_src` without decoding — returns integers instead of labels; or fails to find the column due to the abbreviation |

**Correct SQL:**
```sql
SELECT CASE u.usr_acq_src WHEN 1 THEN 'Organic' WHEN 2 THEN 'Social Media'
                           WHEN 3 THEN 'Referral' WHEN 4 THEN 'Ad Campaign' END AS channel,
       COUNT(*) AS new_users_2023
FROM users u
WHERE YEAR(u.joined_at) = 2023
GROUP BY u.usr_acq_src
ORDER BY new_users_2023 DESC;
```

---

### Q17 — NULL in Mid-Join + Multi-Hop

| | |
|---|---|
| **EC** | EC-01 + EC-03 + EC-08 |
| **Tier** | Hard |
| **NL** | "Which playlists contain tracks that are not part of any album (standalone singles)?" |
| **Why Hard** | EC-03 IS NULL filter must be placed mid-join on `tracks.album_id`. EC-08 multi-hop join traverses three tables. EC-01: `tracks.title` and `albums.title` both exist and could confuse schema linking. |
| **Common Wrong Version** | Filtering on `albums.album_id IS NULL` after a LEFT JOIN to albums — incorrect table reference |

**Correct SQL:**
```sql
SELECT DISTINCT pl.name AS playlist_name, pl.playlist_type, t.title AS single_title
FROM playlists       pl
JOIN playlist_tracks pt ON pl.playlist_id = pt.playlist_id
JOIN tracks           t ON pt.track_id    = t.track_id
WHERE t.album_id IS NULL
ORDER BY pl.name;
```

---

## Tier 3 — Extra Hard

---

### Q18 — Window Function + 5-Table Chain + Abbreviated FK

| | |
|---|---|
| **EC** | EC-08 + EC-05 + WINDOW |
| **Tier** | Extra Hard |
| **NL** | "Rank each artist by total streams within their primary genre." |
| **Why Hard** | Requires `RANK() OVER (PARTITION BY)` which models rarely generate correctly from NL. Also requires `ag.is_prim = 1` — an abbreviated column that must equal 1 to filter only the primary genre. Without this filter, artists appear in all their genres, skewing the rank. |
| **Common Wrong Version** | Missing `AND ag.is_prim = 1` — counts streams across all genres, not just primary; or using `ORDER BY` instead of `RANK() OVER` |

**Correct SQL:**
```sql
SELECT a.name AS artist_name, g.name AS primary_genre,
       COUNT(pe.event_id) AS total_streams,
       RANK() OVER (PARTITION BY g.genre_id ORDER BY COUNT(pe.event_id) DESC) AS genre_rank
FROM artists a
JOIN artist_genres ag ON a.artist_id = ag.artist_id AND ag.is_prim = 1
JOIN genres         g ON ag.genre_id  = g.genre_id
JOIN track_artists ta ON a.artist_id  = ta.artist_id
JOIN play_events   pe ON ta.track_id  = pe.track_id
WHERE pe.event_type = 'play'
GROUP BY a.artist_id, a.name, g.genre_id, g.name;
```

---

### Q19 — Nested Aggregation (AVG of COUNTs)

| | |
|---|---|
| **EC** | EC-01 + NESTED AGG |
| **Tier** | Extra Hard |
| **NL** | "What is the average number of monthly plays per artist across all months on record?" |
| **Why Hard** | The inner aggregation sums plays per artist per month; the outer aggregation averages those monthly totals. `AVG(COUNT(*))` is not valid without a subquery. NL2SQL systems frequently flatten this to a single aggregation, returning the overall average rather than the average of monthly averages. |
| **Common Wrong Version** | `SELECT a.name, AVG(COUNT(*)) FROM ...` — invalid SQL; or `SELECT a.name, COUNT(*) / COUNT(DISTINCT month) FROM ...` — different semantic |

**Correct SQL:**
```sql
SELECT artist_name, AVG(monthly_plays) AS avg_monthly_plays
FROM (
    SELECT a.name AS artist_name, DATE_FORMAT(pe.played_at, '%Y-%m') AS ym, COUNT(*) AS monthly_plays
    FROM artists a
    JOIN track_artists ta ON a.artist_id = ta.artist_id
    JOIN play_events   pe ON ta.track_id  = pe.track_id
    WHERE pe.event_type = 'play'
    GROUP BY a.artist_id, a.name, ym
) monthly_totals
GROUP BY artist_name
ORDER BY avg_monthly_plays DESC;
```

---

### Q20 — Pre-Aggregated vs Raw Source Ambiguity

| | |
|---|---|
| **EC** | EC-07 |
| **Tier** | Extra Hard |
| **NL** | "Compare total stream counts from the analytics table vs raw play events for Karol G in 2024." |
| **Why Hard** | Two valid data sources give different counts — `daily_artist_metrics.stream_count` sits **290,000×–1,070,000×** above raw `play_events` (corrected 2026-07-21; this row previously said "~5%", which was the design intent and never the seeded reality). Both answers are "correct" depending on business definition. The model must use both without conflating them into a single query. Expected result: `metrics_table > raw_play_events`. Because the gap is this large, benchmark items derived from EC-07 must name their source — see `docs/EVALUATION_PROTOCOL.md` §9 quirk 2. |
| **Common Wrong Version** | JOIN both tables without UNION ALL — causes double-counting; or selecting only one source without explaining the discrepancy |

**Correct SQL:**
```sql
SELECT 'metrics_table' AS source, SUM(dam.stream_count) AS total_streams
FROM daily_artist_metrics dam JOIN artists a ON dam.artist_id = a.artist_id
WHERE a.name = 'Karol G' AND YEAR(dam.metric_date) = 2024
UNION ALL
SELECT 'raw_play_events' AS source, COUNT(*) AS total_streams
FROM play_events pe JOIN track_artists ta ON pe.track_id = ta.track_id
JOIN artists a ON ta.artist_id = a.artist_id
WHERE a.name = 'Karol G' AND pe.event_type = 'play' AND YEAR(pe.played_at) = 2024;
```

---

### Q21 — Year-over-Year Comparison (Temporal Self-Join)

| | |
|---|---|
| **EC** | EC-09 + EC-02 |
| **Tier** | Extra Hard |
| **NL** | "Which artists grew their total streams by more than 20% from 2023 to 2024?" |
| **Why Hard** | Requires two separate aggregation subqueries for different years, joined on `artist_id`. The percentage threshold `> 0.20` must be computed as a ratio, not as a constant. Division by zero (artist with 0 streams in 2023) must be handled. |
| **Common Wrong Version** | Single-pass `WHERE YEAR IN (2023, 2024) GROUP BY year` — cannot compare across years in one pass |

**Correct SQL:**
```sql
SELECT curr.artist_name,
       prev.total_streams AS streams_2023, curr.total_streams AS streams_2024,
       ROUND((curr.total_streams - prev.total_streams) / prev.total_streams * 100, 2) AS yoy_growth_pct
FROM (SELECT a.artist_id, a.name AS artist_name, COUNT(*) AS total_streams
      FROM artists a JOIN track_artists ta ON a.artist_id = ta.artist_id
      JOIN play_events pe ON ta.track_id = pe.track_id
      WHERE pe.event_type = 'play' AND YEAR(pe.played_at) = 2024
      GROUP BY a.artist_id, a.name) curr
JOIN (SELECT a.artist_id, COUNT(*) AS total_streams
      FROM artists a JOIN track_artists ta ON a.artist_id = ta.artist_id
      JOIN play_events pe ON ta.track_id = pe.track_id
      WHERE pe.event_type = 'play' AND YEAR(pe.played_at) = 2023
      GROUP BY a.artist_id) prev ON curr.artist_id = prev.artist_id
WHERE (curr.total_streams - prev.total_streams) / prev.total_streams > 0.20
ORDER BY yoy_growth_pct DESC;
```

---

### Q22 — Percentage of Catalog Never Played (NULL Aggregation)

| | |
|---|---|
| **EC** | EC-11 + EC-03 |
| **Tier** | Extra Hard |
| **NL** | "What percentage of all tracks have never been played?" |
| **Why Hard** | LEFT JOIN with IS NULL check inside a CASE WHEN aggregate. The `event_type = 'play'` filter must be in the JOIN condition, not in the WHERE clause — otherwise the outer join collapses and no track appears as "never played." |
| **Common Wrong Version** | `LEFT JOIN play_events pe ON ... WHERE pe.event_id IS NULL` — the WHERE clause eliminates the outer join, returning 0 never-played tracks |

**Correct SQL:**
```sql
SELECT COUNT(*) AS total_tracks,
       SUM(CASE WHEN pe.event_id IS NULL THEN 1 ELSE 0 END) AS never_played,
       ROUND(SUM(CASE WHEN pe.event_id IS NULL THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS pct_never_played
FROM tracks t
LEFT JOIN play_events pe ON t.track_id = pe.track_id AND pe.event_type = 'play';
```

---

### Q23 — Genre Hierarchy Traversal + Schema Linking Ambiguity

| | |
|---|---|
| **EC** | EC-04 + EC-01 |
| **Tier** | Extra Hard |
| **NL** | "How many plays did tracks in the Latin genre and all its sub-genres receive in 2024?" |
| **Why Hard** | Must traverse the genre hierarchy (EC-04) to include Reggaeton and Salsa as children of Latin. Schema linking ambiguity: "genre of track" could map to either `track_genres` or `artist_genres` (EC-01). The model must choose `track_genres` for this question. |
| **Common Wrong Version** | `WHERE g.name = 'Latin'` — excludes Reggaeton and Salsa (sub-genres); or joining through `artist_genres` instead of `track_genres` |

**Correct SQL:**
```sql
SELECT g.name AS genre_or_subgenre, COUNT(pe.event_id) AS plays_2024
FROM genres g
JOIN track_genres tg ON g.genre_id  = tg.genre_id
JOIN play_events  pe ON tg.track_id = pe.track_id
WHERE pe.event_type = 'play' AND YEAR(pe.played_at) = 2024
  AND (g.genre_id = (SELECT genre_id FROM genres WHERE name = 'Latin')
       OR g.parent_genre_id = (SELECT genre_id FROM genres WHERE name = 'Latin'))
GROUP BY g.genre_id, g.name
ORDER BY plays_2024 DESC;
```

---

### Q24 — Temporal Overlap Query (SCD Period Lookup)

| | |
|---|---|
| **EC** | EC-06 |
| **Tier** | Extra Hard |
| **NL** | "What subscription plan was each user on during Q3 2023?" |
| **Why Hard** | The period must overlap with July–September 2023, not just start before it. IS NULL must be handled in the range condition: `period_end IS NULL OR period_end >= '2023-07-01'`. A model that uses `BETWEEN` naively misses ongoing periods. |
| **Common Wrong Version** | `WHERE period_start BETWEEN '2023-07-01' AND '2023-09-30'` — misses users whose period started before July but was still active during Q3 |

**Correct SQL:**
```sql
SELECT u.display_name, p.name AS plan_name, sp.period_start,
       COALESCE(CAST(sp.period_end AS CHAR), 'ongoing') AS period_end, sp.monthly_fee
FROM subscription_periods sp
JOIN users              u ON sp.user_id = u.user_id
JOIN subscription_plans p ON sp.plan_id = p.plan_id
WHERE sp.period_start <= '2023-09-30'
  AND (sp.period_end IS NULL OR sp.period_end >= '2023-07-01')
ORDER BY u.display_name;
```

---

### Q25 — Conditional Aggregation + HAVING + Skip Rate

| | |
|---|---|
| **EC** | EC-15 + EC-13 |
| **Tier** | Extra Hard |
| **NL** | "Which genres have a skip rate above 10% of total interactions?" |
| **Why Hard** | Requires a CASE WHEN inside SUM to count only skip events, then HAVING to filter on the ratio. Both the numerator and denominator reference the same table in different ways. The percentage threshold must be applied post-aggregation. |
| **Common Wrong Version** | `WHERE event_type = 'skip'` in the WHERE clause — filters out all non-skip events before aggregation, making the denominator wrong |

**Correct SQL:**
```sql
SELECT g.name AS genre_name, COUNT(*) AS total_events,
       SUM(CASE WHEN pe.event_type = 'skip' THEN 1 ELSE 0 END) AS skip_count,
       ROUND(SUM(CASE WHEN pe.event_type = 'skip' THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS skip_rate_pct
FROM genres g
JOIN track_genres tg ON g.genre_id  = tg.genre_id
JOIN play_events  pe ON tg.track_id = pe.track_id
GROUP BY g.genre_id, g.name
HAVING SUM(CASE WHEN pe.event_type = 'skip' THEN 1 ELSE 0 END) * 100.0 / COUNT(*) > 10.0
ORDER BY skip_rate_pct DESC;
```

---

### Q26 — 5-Table Implicit Chain + Double Ambiguity

| | |
|---|---|
| **EC** | EC-08 + EC-01 + EC-02 |
| **Tier** | Extra Hard |
| **NL** | "Which curated playlists contain songs by artists from Colombia?" |
| **Why Hard** | Full 5-table chain traversal. `playlist_type = 'curated'` requires value matching (EC-02). `artists.country = 'CO'` must be distinguished from `users.country = 'CO'` (EC-01). All three error types present simultaneously. |
| **Common Wrong Version** | Joining `users.country` instead of `artists.country`; or omitting `playlist_type = 'curated'` filter |

**Correct SQL:**
```sql
SELECT DISTINCT pl.name AS playlist_name, a.name AS artist_name, a.country
FROM playlists pl
JOIN playlist_tracks pt ON pl.playlist_id = pt.playlist_id
JOIN tracks          t  ON pt.track_id    = t.track_id
JOIN track_artists   ta ON t.track_id     = ta.track_id
JOIN artists          a ON ta.artist_id   = a.artist_id
WHERE pl.playlist_type = 'curated' AND a.country = 'CO'
ORDER BY pl.name;
```

---

### Q27 — Forked Playlist Set Difference (Self-Join + Anti-Join)

| | |
|---|---|
| **EC** | EC-04 + EC-14 |
| **Tier** | Extra Hard |
| **NL** | "Which forked playlists contain tracks that are not in their original source playlist?" |
| **Why Hard** | Self-join on `playlists.forked_from_id` (EC-04) to retrieve both the fork and its origin. Correlated NOT EXISTS checks per-track membership in the original (EC-14). Both patterns must be combined correctly. |
| **Common Wrong Version** | Using EXCEPT without proper correlation — returns tracks not in any original playlist, not just the specific source |

**Correct SQL:**
```sql
SELECT fp.name AS forked_playlist, t.title AS track_not_in_original, op.name AS original_playlist
FROM playlists fp
JOIN playlists         op  ON fp.forked_from_id = op.playlist_id
JOIN playlist_tracks   fpt ON fp.playlist_id    = fpt.playlist_id
JOIN tracks             t  ON fpt.track_id      = t.track_id
WHERE NOT EXISTS (
    SELECT 1 FROM playlist_tracks opt
    WHERE opt.playlist_id = op.playlist_id AND opt.track_id = fpt.track_id
)
ORDER BY fp.name;
```

---

### Q28 — Windowed Top-N Per Group + Code Decoding

| | |
|---|---|
| **EC** | EC-02 + WINDOW + EC-08 |
| **Tier** | Extra Hard |
| **NL** | "For each user acquisition channel, which artist was streamed most in 2024?" |
| **Why Hard** | Requires decoding `usr_acq_src` integer codes inside a CASE statement, then computing `RANK() OVER (PARTITION BY usr_acq_src)` and filtering `WHERE rnk = 1`. Three patterns — code decoding, window function, top-N per group — must all be correct simultaneously. |
| **Common Wrong Version** | `GROUP BY usr_acq_src ORDER BY COUNT(*) DESC LIMIT 1` — returns global top artist, not one per channel |

**Correct SQL:**
```sql
SELECT acq_label, artist_name, stream_count
FROM (
    SELECT CASE u.usr_acq_src WHEN 1 THEN 'Organic' WHEN 2 THEN 'Social Media'
                               WHEN 3 THEN 'Referral' WHEN 4 THEN 'Ad Campaign' END AS acq_label,
           a.name AS artist_name, COUNT(*) AS stream_count,
           RANK() OVER (PARTITION BY u.usr_acq_src ORDER BY COUNT(*) DESC) AS rnk
    FROM users u
    JOIN play_events pe ON u.user_id = pe.user_id
    JOIN track_artists ta ON pe.track_id = ta.track_id
    JOIN artists a ON ta.artist_id = a.artist_id
    WHERE pe.event_type = 'play' AND YEAR(pe.played_at) = 2024
    GROUP BY u.usr_acq_src, a.artist_id, a.name
) ranked WHERE rnk = 1 ORDER BY acq_label;
```

---

### Q29 — Ordinal Reference (Second Most)

| | |
|---|---|
| **EC** | EC-12 |
| **Tier** | Extra Hard |
| **NL** | "What is the second most-streamed genre in 2024?" |
| **Why Hard** | `LIMIT 1 OFFSET 1` misses ties (two genres with identical stream counts). `DENSE_RANK()` must be used. The ordinal number "second" maps to `WHERE rnk = 2`, requiring understanding of rank semantics. ASC/DESC confusion also produces the wrong ordinal silently. |
| **Common Wrong Version** | `ORDER BY COUNT(*) DESC LIMIT 1 OFFSET 1` — skips ties; `ORDER BY COUNT(*) ASC` — returns the least-streamed genre |

**Correct SQL:**
```sql
SELECT genre_name, total_streams
FROM (
    SELECT g.name AS genre_name, COUNT(*) AS total_streams,
           DENSE_RANK() OVER (ORDER BY COUNT(*) DESC) AS rnk
    FROM genres g
    JOIN track_genres tg ON g.genre_id  = tg.genre_id
    JOIN play_events  pe ON tg.track_id = pe.track_id
    WHERE pe.event_type = 'play' AND YEAR(pe.played_at) = 2024
    GROUP BY g.genre_id, g.name
) ranked WHERE rnk = 2;
```

---

### Q30 — Maximum Composition (4 Patterns Combined)

| | |
|---|---|
| **EC** | EC-18 + EC-08 + EC-15 + EC-HAVING |
| **Tier** | Extra Hard |
| **NL** | "Find artists whose unique monthly listeners grew more than 30% from Q3 2023 to Q3 2024, excluding those with fewer than 3 total events in Q3 2023, ranked by growth rate." |
| **Why Hard** | This is the compositional generalization test (EC-18). It combines four independent patterns in a novel configuration that is unlikely to have been seen in training: (1) COUNT DISTINCT for unique listeners, (2) HAVING filter to exclude low-volume artists, (3) percentage growth threshold as a WHERE condition on a derived ratio, (4) multi-hop join chain throughout both subqueries. Each pattern alone is Hard; their combination is Extra Hard. |
| **Common Wrong Version** | Any partial solution — e.g., correct growth calculation but missing the HAVING exclusion filter, or using COUNT(*) instead of COUNT(DISTINCT user_id) |

**Correct SQL:**
```sql
SELECT curr.artist_name,
       prev.q3_listeners AS listeners_q3_2023, curr.q3_listeners AS listeners_q3_2024,
       ROUND((curr.q3_listeners - prev.q3_listeners) / prev.q3_listeners * 100, 2) AS growth_pct
FROM (
    SELECT a.artist_id, a.name AS artist_name, COUNT(DISTINCT pe.user_id) AS q3_listeners
    FROM artists a JOIN track_artists ta ON a.artist_id = ta.artist_id
    JOIN play_events pe ON ta.track_id = pe.track_id
    WHERE pe.event_type = 'play' AND pe.played_at BETWEEN '2024-07-01' AND '2024-09-30'
    GROUP BY a.artist_id, a.name
) curr
JOIN (
    SELECT a.artist_id, COUNT(DISTINCT pe.user_id) AS q3_listeners
    FROM artists a JOIN track_artists ta ON a.artist_id = ta.artist_id
    JOIN play_events pe ON ta.track_id = pe.track_id
    WHERE pe.event_type = 'play' AND pe.played_at BETWEEN '2023-07-01' AND '2023-09-30'
    GROUP BY a.artist_id
    HAVING COUNT(*) >= 3
) prev ON curr.artist_id = prev.artist_id
WHERE (curr.q3_listeners - prev.q3_listeners) / prev.q3_listeners > 0.30
ORDER BY growth_pct DESC;
```

---

## Query Coverage Matrix

| Query | EC-01 | EC-02 | EC-03 | EC-04 | EC-05 | EC-06 | EC-07 | EC-08 | EC-09 | EC-10 | EC-11 | EC-12 | EC-13 | EC-14 | EC-15 | EC-16 | EC-17 | EC-18 |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| Q01 | X | | | | | | | | | | | | | | | | | |
| Q02 | | X | | | | | | | | | | | | | | | | |
| Q03 | | | X | | | | | | | | | | | | | | | |
| Q04 | | | | | | | | | | | | | | | | | X | |
| Q05 | X | | | | | | | | | | | | | | | | | |
| Q06 | | | | | | X | | | | | | | | | | | | |
| Q07 | | | | | | | | X | | | | | | | | | | |
| Q08 | | | | | | X | | | | | | | | | | | | |
| Q09 | | | | | | | | | | | | | | | X | | | |
| Q10 | | | | | | X | | | | | | | | | | | X | |
| Q11 | | | | | | | | | | | | | | | X | | | |
| Q12 | | | | | | | | | | | | | | X | | | | |
| Q13 | | | | | | | | | X | | | | | | | | | |
| Q14 | | | | X | | | | | | | | | | | | | | |
| Q15 | | | | | | | | | | X | | | | | | | | |
| Q16 | X | X | | | | | | | | | | | | | | | | |
| Q17 | X | | X | | | | | X | | | | | | | | | | |
| Q18 | | | | | X | | | X | | | | | | | | | | |
| Q19 | X | | | | | | | | | | | | | | | | | |
| Q20 | | | | | | | X | | | | | | | | | | | |
| Q21 | | X | | | | | | | X | | | | | | | | | |
| Q22 | | | X | | | | | | | | X | | | | | | | |
| Q23 | X | | | X | | | | | | | | | | | | | | |
| Q24 | | | | | | X | | | | | | | | | | | | |
| Q25 | | | | | | | | | | | | | X | | X | | | |
| Q26 | X | X | | | | | | X | | | | | | | | | | |
| Q27 | | | | X | | | | | | | | | | X | | | | |
| Q28 | | X | | | | | | X | | | | | | | | | | |
| Q29 | | | | | | | | | | | | X | | | | | | |
| Q30 | | | | | | | | X | | | | | | | X | | | X |

---

*Soundwave DB Edge Case Catalog — IDI Project, Universidad Nacional de Colombia, 2026.*
