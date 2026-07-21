"""Build data/benchmarks/corpora/idi_exec_75.jsonl (75 items).

EVALUATION_PROTOCOL.md §2.1 fixes the category distribution from Chapter 1 §1.5:

    Ranking / Top-N 10 | Aggregations / KPIs 15 | Temporal / Trends 15 |
    Comparisons 10 | Filtering / Segmentation 10 | Relational / Multi-table 5 |
    Complex Analysis 5 | Deliberate Ambiguity 5

and the difficulty split 20% low / 40% medium / 40% high, i.e. 15 / 30 / 30.

VOICE. This corpus is the only one written the way a manager actually talks:
contractions, business shorthand, no schema vocabulary ("what's our churn
looking like", not "count subscriptions where end_date IS NOT NULL"). §2.1's
domain note applies — Ch1 illustrates the categories with retail examples but
all four corpora execute against SoundWave, so these are authored in the
music-streaming domain with Ch1's category definitions and counts honoured
exactly.

DIFFICULTY IS COMPUTED. See `hardness.EXEC_FROM_SPIDER` for why low/medium/high
is derived from the computed Spider tier rather than declared, and what that
costs.

THE FIVE AMBIGUITY ITEMS carry `expected_behaviour="clarify"` and deliberately
have **no** reference SQL: §3.6 scores them on whether the pipeline asks instead
of guessing, so a reference result set would be meaningless. Each one is
ambiguous for a reason that exists in this schema — "best" and "popular" straddle
the cached counters and the raw log, "top playlists" hits the deliberately
unresolved playlists<->tracks bridge, and "active" has three defensible
definitions in three different tables.

Usage:  python -m evaluation.authoring.build_idi_exec_75
"""

from __future__ import annotations

from evaluation.corpus import CorpusItem, write_corpus

RANKING = "Ranking / Top-N"
AGGREGATION = "Aggregations / KPIs"
TEMPORAL = "Temporal / Trends"
COMPARISON = "Comparisons"
FILTERING = "Filtering / Segmentation"
RELATIONAL = "Relational / Multi-table"
COMPLEX = "Complex Analysis"
AMBIGUOUS = "Deliberate Ambiguity"

# (n, category, nl, sql|None, intended_level, ec_tags, order_matters, notes)
ITEMS: list[tuple[int, str, str, str | None, str, list[str], bool, str]] = [
    # ---------------- Aggregations / KPIs : 8 low, 5 medium, 2 high -------
    (
        1,
        AGGREGATION,
        "How many users do we have?",
        "SELECT COUNT(*) FROM users",
        "low",
        [],
        False,
        "",
    ),
    (
        2,
        AGGREGATION,
        "How many tracks are in the catalogue?",
        "SELECT COUNT(*) FROM tracks",
        "low",
        [],
        False,
        "",
    ),
    (
        3,
        AGGREGATION,
        "What's our total revenue to date?",
        "SELECT SUM(amount) FROM payments WHERE payment_status = 'completed'",
        "low",
        ["EC-17"],
        False,
        "Revenue excludes failed and refunded payments.",
    ),
    (
        4,
        AGGREGATION,
        "How many artists do we carry?",
        "SELECT COUNT(*) FROM artists",
        "low",
        [],
        False,
        "",
    ),
    (
        5,
        AGGREGATION,
        "How many plays have we served all time?",
        "SELECT COUNT(*) FROM play_events WHERE event_type = 'play'",
        "low",
        ["EC-17"],
        False,
        "",
    ),
    (
        6,
        AGGREGATION,
        "What's the average track length in minutes?",
        "SELECT AVG(trk_dur_ms) / 60000.0 FROM tracks",
        "low",
        ["EC-05"],
        False,
        "",
    ),
    (
        7,
        AGGREGATION,
        "How many playlists are there?",
        "SELECT COUNT(*) FROM playlists",
        "low",
        [],
        False,
        "",
    ),
    (
        8,
        AGGREGATION,
        "How many active subscriptions do we have?",
        "SELECT COUNT(*) FROM subscriptions WHERE status = 1",
        "low",
        ["EC-02"],
        False,
        "",
    ),
    (
        9,
        AGGREGATION,
        "What's our average payment size by method?",
        "SELECT payment_method, AVG(amount) AS avg_amount FROM payments "
        "WHERE payment_status = 'completed' GROUP BY payment_method",
        "medium",
        ["EC-17"],
        False,
        "",
    ),
    (
        10,
        AGGREGATION,
        "How do plays break down by device?",
        "SELECT device_type, COUNT(*) AS plays FROM play_events GROUP BY device_type",
        "medium",
        [],
        False,
        "",
    ),
    (
        11,
        AGGREGATION,
        "What's the split of our users by acquisition channel?",
        "SELECT usr_acq_src, COUNT(*) AS users FROM users GROUP BY usr_acq_src",
        "medium",
        ["EC-02", "EC-05"],
        False,
        "",
    ),
    (
        12,
        AGGREGATION,
        "How many subscriptions sit on each plan?",
        "SELECT plan_id, COUNT(*) AS subs FROM subscriptions GROUP BY plan_id",
        "medium",
        [],
        False,
        "",
    ),
    (
        13,
        AGGREGATION,
        "How many listening hours does each device account for?",
        "SELECT device_type, SUM(duration_ms) / 3600000.0 AS hours FROM play_events "
        "WHERE event_type = 'play' GROUP BY device_type",
        "medium",
        ["EC-05", "EC-17"],
        False,
        "",
    ),
    (
        14,
        AGGREGATION,
        "What's our revenue by plan?",
        "SELECT p.name, SUM(pay.amount) AS revenue FROM payments pay "
        "JOIN subscriptions s ON pay.subscription_id = s.subscription_id "
        "JOIN subscription_plans p ON s.plan_id = p.plan_id "
        "WHERE pay.payment_status = 'completed' GROUP BY p.name",
        "high",
        ["EC-17", "EC-08"],
        False,
        "",
    ),
    (
        15,
        AGGREGATION,
        "How many distinct listeners does each artist pull in?",
        "SELECT ta.artist_id, COUNT(DISTINCT pe.user_id) AS listeners FROM track_artists ta "
        "JOIN play_events pe ON ta.track_id = pe.track_id "
        "WHERE pe.event_type = 'play' GROUP BY ta.artist_id",
        "high",
        ["EC-15", "EC-17"],
        False,
        "",
    ),
    # ---------------- Ranking / Top-N : 3 medium, 7 high ------------------
    (
        16,
        RANKING,
        "What are our ten biggest tracks by the play counter?",
        "SELECT title, total_plays FROM tracks ORDER BY total_plays DESC LIMIT 10",
        "medium",
        ["EC-07"],
        True,
        "Names the cached counter as its source, so the raw log is not an alternative.",
    ),
    (
        17,
        RANKING,
        "Which playlists have the biggest followings?",
        "SELECT name, follower_count FROM playlists ORDER BY follower_count DESC LIMIT 10",
        "medium",
        [],
        True,
        "",
    ),
    (
        18,
        RANKING,
        "Which plans cost the most?",
        "SELECT name, monthly_price FROM subscription_plans ORDER BY monthly_price DESC",
        "medium",
        [],
        True,
        "",
    ),
    (
        19,
        RANKING,
        "Who are our top five artists by listener reach?",
        "SELECT a.name, COUNT(DISTINCT pe.user_id) AS listeners FROM artists a "
        "JOIN track_artists ta ON a.artist_id = ta.artist_id "
        "JOIN play_events pe ON ta.track_id = pe.track_id "
        "WHERE pe.event_type = 'play' GROUP BY a.name ORDER BY listeners DESC LIMIT 5",
        "high",
        ["EC-08", "EC-15"],
        True,
        "",
    ),
    (
        20,
        RANKING,
        "Which genres are we biggest in?",
        "SELECT g.name, COUNT(*) AS plays FROM genres g "
        "JOIN track_genres tg ON g.genre_id = tg.genre_id "
        "JOIN play_events pe ON tg.track_id = pe.track_id "
        "WHERE pe.event_type = 'play' GROUP BY g.name ORDER BY plays DESC",
        "high",
        ["EC-08"],
        True,
        "",
    ),
    (
        21,
        RANKING,
        "Who are our most engaged listeners this year?",
        "SELECT u.display_name, COUNT(*) AS plays FROM users u "
        "JOIN play_events pe ON u.user_id = pe.user_id "
        "WHERE pe.event_type = 'play' AND pe.played_at >= '2026-01-01' "
        "GROUP BY u.display_name ORDER BY plays DESC LIMIT 10",
        "high",
        ["EC-17"],
        True,
        "'This year' resolves to 2026 under the frozen clock.",
    ),
    (
        22,
        RANKING,
        "Which tracks get skipped the most?",
        "SELECT t.title, COUNT(*) AS skips FROM tracks t "
        "JOIN play_events pe ON t.track_id = pe.track_id "
        "WHERE pe.event_type = 'skip' GROUP BY t.title ORDER BY skips DESC LIMIT 10",
        "high",
        ["EC-17"],
        True,
        "",
    ),
    (
        23,
        RANKING,
        "Which countries give us the most listening?",
        "SELECT country_code, COUNT(*) AS plays FROM play_events "
        "WHERE event_type = 'play' GROUP BY country_code ORDER BY plays DESC LIMIT 10",
        "high",
        ["EC-01"],
        True,
        "play_events.country_code is where the event fired, not the user's home country.",
    ),
    (
        24,
        RANKING,
        "According to the analytics table, who were our biggest artists in 2026?",
        "SELECT a.name, SUM(dam.stream_count) AS streams FROM daily_artist_metrics dam "
        "JOIN artists a ON dam.artist_id = a.artist_id "
        "WHERE YEAR(dam.metric_date) = 2026 GROUP BY a.name ORDER BY streams DESC LIMIT 5",
        "high",
        ["EC-07"],
        True,
        "Names the analytics table explicitly; the raw log is a different question.",
    ),
    (
        25,
        RANKING,
        "Which labels have the most artists on our roster?",
        "SELECT label, COUNT(*) AS artists FROM artists WHERE label IS NOT NULL "
        "GROUP BY label ORDER BY artists DESC LIMIT 5",
        "high",
        [],
        True,
        "",
    ),
    # ---------------- Temporal / Trends : 4 low, 8 medium, 3 high ---------
    (
        26,
        TEMPORAL,
        "How many people joined this year?",
        "SELECT COUNT(*) FROM users WHERE YEAR(joined_at) = 2026",
        "low",
        [],
        False,
        "",
    ),
    (
        27,
        TEMPORAL,
        "How many albums came out in 2025?",
        "SELECT COUNT(*) FROM albums WHERE YEAR(release_date) = 2025",
        "low",
        ["EC-01"],
        False,
        "",
    ),
    (
        28,
        TEMPORAL,
        "When did we last log a play?",
        "SELECT MAX(played_at) FROM play_events",
        "low",
        [],
        False,
        "",
    ),
    (
        29,
        TEMPORAL,
        "How many payments did we take in 2026?",
        "SELECT COUNT(*) FROM payments WHERE YEAR(payment_date) = 2026",
        "low",
        [],
        False,
        "",
    ),
    (
        30,
        TEMPORAL,
        "How many plays did we serve last month?",
        "SELECT COUNT(*) AS plays FROM play_events WHERE event_type = 'play' "
        "AND played_at >= '2026-06-01' AND played_at < '2026-07-01'",
        "medium",
        ["EC-17"],
        False,
        "'Last month' resolves to June 2026 under the frozen clock.",
    ),
    (
        31,
        TEMPORAL,
        "How are plays trending month by month?",
        "SELECT DATE_FORMAT(played_at, '%Y-%m') AS ym, COUNT(*) AS plays FROM play_events "
        "WHERE event_type = 'play' GROUP BY ym",
        "medium",
        ["EC-17"],
        False,
        "",
    ),
    (
        32,
        TEMPORAL,
        "How many new users did we get each year?",
        "SELECT YEAR(joined_at) AS yr, COUNT(*) AS users FROM users GROUP BY yr",
        "medium",
        [],
        False,
        "",
    ),
    (
        33,
        TEMPORAL,
        "What did revenue look like month by month?",
        "SELECT DATE_FORMAT(payment_date, '%Y-%m') AS ym, SUM(amount) AS revenue "
        "FROM payments WHERE payment_status = 'completed' GROUP BY ym",
        "medium",
        ["EC-17"],
        False,
        "",
    ),
    (
        34,
        TEMPORAL,
        "How many albums did we put out each year?",
        "SELECT YEAR(release_date) AS yr, COUNT(*) AS albums FROM albums GROUP BY yr",
        "medium",
        [],
        False,
        "",
    ),
    (
        35,
        TEMPORAL,
        "How much did we take in over the last twelve months?",
        "SELECT SUM(amount) AS revenue FROM payments WHERE payment_status = 'completed' "
        "AND payment_date >= '2025-07-17'",
        "medium",
        ["EC-17"],
        False,
        "Trailing twelve months from the frozen clock instant.",
    ),
    (
        36,
        TEMPORAL,
        "What kinds of activity did we see this year?",
        "SELECT event_type, COUNT(*) AS events FROM play_events "
        "WHERE played_at >= '2026-01-01' GROUP BY event_type",
        "medium",
        ["EC-02"],
        False,
        "",
    ),
    (
        37,
        TEMPORAL,
        "When did each plan's current price kick in?",
        "SELECT plan_id, effective_from FROM pricing_history WHERE effective_to IS NULL",
        "medium",
        ["EC-06"],
        False,
        "",
    ),
    (
        38,
        TEMPORAL,
        "How is listening trending across the months of this year?",
        "SELECT DATE_FORMAT(pe.played_at, '%Y-%m') AS ym, COUNT(*) AS plays "
        "FROM play_events pe WHERE pe.event_type = 'play' "
        "AND pe.played_at >= '2026-01-01' GROUP BY ym ORDER BY ym",
        "high",
        ["EC-17"],
        True,
        "",
    ),
    (
        39,
        TEMPORAL,
        "Which artists are pulling the biggest audiences this year?",
        "SELECT a.name, COUNT(DISTINCT pe.user_id) AS listeners FROM artists a "
        "JOIN track_artists ta ON a.artist_id = ta.artist_id "
        "JOIN play_events pe ON ta.track_id = pe.track_id "
        "WHERE pe.event_type = 'play' AND pe.played_at >= '2026-01-01' "
        "GROUP BY a.name ORDER BY listeners DESC",
        "high",
        ["EC-08", "EC-15"],
        True,
        "",
    ),
    (
        40,
        TEMPORAL,
        "How does each month of this year compare on unique listeners?",
        "SELECT DATE_FORMAT(played_at, '%Y-%m') AS ym, COUNT(DISTINCT user_id) AS listeners "
        "FROM play_events WHERE event_type = 'play' AND played_at >= '2026-01-01' "
        "GROUP BY ym ORDER BY ym",
        "high",
        ["EC-15"],
        True,
        "",
    ),
    # ---------------- Comparisons : 1 low, 5 medium, 4 high ---------------
    (
        41,
        COMPARISON,
        "How many of our plans are paid rather than free?",
        "SELECT COUNT(*) FROM subscription_plans WHERE monthly_price > 0",
        "low",
        [],
        False,
        "",
    ),
    (
        42,
        COMPARISON,
        "How do our plans stack up on price?",
        "SELECT name, monthly_price FROM subscription_plans ORDER BY monthly_price",
        "medium",
        [],
        True,
        "",
    ),
    (
        43,
        COMPARISON,
        "How do our countries compare on user numbers?",
        "SELECT country, COUNT(*) AS users FROM users GROUP BY country",
        "medium",
        ["EC-01"],
        False,
        "",
    ),
    (
        44,
        COMPARISON,
        "How do devices compare on listening hours?",
        "SELECT device_type, SUM(duration_ms) / 3600000.0 AS hours FROM play_events "
        "WHERE event_type = 'play' GROUP BY device_type",
        "medium",
        ["EC-05"],
        False,
        "",
    ),
    (
        45,
        COMPARISON,
        "How do payment methods compare on volume?",
        "SELECT payment_method, COUNT(*) AS payments FROM payments GROUP BY payment_method",
        "medium",
        [],
        False,
        "",
    ),
    (
        46,
        COMPARISON,
        "Is more of our catalogue explicit or clean?",
        "SELECT is_exp, COUNT(*) AS tracks FROM tracks GROUP BY is_exp",
        "medium",
        ["EC-05"],
        False,
        "",
    ),
    (
        47,
        COMPARISON,
        "How does this year's listening compare with last year's?",
        "SELECT YEAR(played_at) AS yr, COUNT(*) AS plays FROM play_events "
        "WHERE event_type = 'play' AND played_at >= '2025-01-01' GROUP BY yr ORDER BY yr",
        "high",
        ["EC-17"],
        True,
        "",
    ),
    (
        48,
        COMPARISON,
        "Does the analytics table agree with the raw log for 2026?",
        "SELECT 'analytics' AS source, SUM(stream_count) AS total "
        "FROM daily_artist_metrics WHERE YEAR(metric_date) = 2026 "
        "UNION ALL "
        "SELECT 'raw_log', COUNT(*) FROM play_events "
        "WHERE event_type = 'play' AND YEAR(played_at) = 2026",
        "high",
        ["EC-07"],
        False,
        "The comparison itself is the question, so naming both sources is correct here "
        "and accepted_alternatives stays empty.",
    ),
    (
        49,
        COMPARISON,
        "How do our acquisition channels compare on how many people actually listen?",
        "SELECT u.usr_acq_src, COUNT(DISTINCT pe.user_id) AS listeners FROM users u "
        "JOIN play_events pe ON u.user_id = pe.user_id "
        "WHERE pe.event_type = 'play' GROUP BY u.usr_acq_src ORDER BY listeners DESC",
        "high",
        ["EC-02", "EC-15"],
        True,
        "",
    ),
    (
        50,
        COMPARISON,
        "How do curated playlists compare with the rest on followers?",
        "SELECT playlist_type, AVG(follower_count) AS avg_followers, COUNT(*) AS playlists "
        "FROM playlists GROUP BY playlist_type ORDER BY avg_followers DESC",
        "high",
        ["EC-02"],
        True,
        "",
    ),
    # ---------------- Filtering / Segmentation : 2 low, 6 medium, 2 high --
    (
        51,
        FILTERING,
        "Who's on our Colombian roster?",
        "SELECT name FROM artists WHERE country = 'CO'",
        "low",
        ["EC-01"],
        False,
        "",
    ),
    (
        52,
        FILTERING,
        "Which plans come with hi-fi?",
        "SELECT name FROM subscription_plans WHERE has_hifi = 1",
        "low",
        ["EC-02"],
        False,
        "",
    ),
    (
        53,
        FILTERING,
        "Who are our users in Colombia?",
        "SELECT display_name, country FROM users WHERE country = 'CO'",
        "medium",
        ["EC-01"],
        False,
        "",
    ),
    (
        54,
        FILTERING,
        "Which tracks are explicit and run over four minutes?",
        "SELECT title FROM tracks WHERE is_exp = 1 AND trk_dur_ms > 240000",
        "medium",
        ["EC-05"],
        False,
        "",
    ),
    (
        55,
        FILTERING,
        "Which users came in through referrals?",
        "SELECT display_name, joined_at FROM users WHERE usr_acq_src = 3",
        "medium",
        ["EC-02"],
        False,
        "",
    ),
    (
        56,
        FILTERING,
        "Show me the curated playlists and how many followers they have.",
        "SELECT name, follower_count FROM playlists WHERE playlist_type = 'curated'",
        "medium",
        ["EC-02"],
        False,
        "",
    ),
    (
        57,
        FILTERING,
        "Which artists debuted in the last fifteen years?",
        "SELECT name, debut_year FROM artists WHERE debut_year >= 2011",
        "medium",
        [],
        False,
        "",
    ),
    (
        58,
        FILTERING,
        "Which subscriptions are set to auto-renew?",
        "SELECT subscription_id, plan_id FROM subscriptions WHERE auto_renew = 1",
        "medium",
        [],
        False,
        "",
    ),
    (
        59,
        FILTERING,
        "Which of our active Colombian users have actually listened to something?",
        "SELECT display_name FROM users WHERE country = 'CO' AND status = 1 "
        "AND user_id IN (SELECT user_id FROM play_events WHERE event_type = 'play')",
        "high",
        ["EC-02", "EC-17"],
        False,
        "",
    ),
    (
        60,
        FILTERING,
        "Which explicit tracks actually sit on an album, alphabetically?",
        "SELECT title FROM tracks WHERE album_id IN (SELECT album_id FROM albums) "
        "AND is_exp = 1 ORDER BY title",
        "high",
        ["EC-03", "EC-05"],
        True,
        "",
    ),
    # ---------------- Relational / Multi-table : 2 medium, 3 high ---------
    (
        61,
        RELATIONAL,
        "Show me each album with the artist behind it.",
        "SELECT a.name, al.title FROM artists a JOIN albums al ON a.artist_id = al.artist_id",
        "medium",
        ["EC-01"],
        False,
        "",
    ),
    (
        62,
        RELATIONAL,
        "Which tracks sit on which playlists?",
        "SELECT p.name, t.title FROM playlists p "
        "JOIN playlist_tracks pt ON p.playlist_id = pt.playlist_id "
        "JOIN tracks t ON pt.track_id = t.track_id",
        "medium",
        ["EC-08"],
        False,
        "",
    ),
    (
        63,
        RELATIONAL,
        "Which of our users follow Colombian artists?",
        "SELECT DISTINCT u.display_name FROM users u "
        "JOIN user_follows_artists ufa ON u.user_id = ufa.user_id "
        "JOIN artists a ON ufa.artist_id = a.artist_id WHERE a.country = 'CO'",
        "high",
        ["EC-08", "EC-01"],
        False,
        "",
    ),
    (
        64,
        RELATIONAL,
        "Which curated playlists feature Colombian artists?",
        "SELECT DISTINCT pl.name FROM playlists pl "
        "JOIN playlist_tracks pt ON pl.playlist_id = pt.playlist_id "
        "JOIN tracks t ON pt.track_id = t.track_id "
        "JOIN track_artists ta ON t.track_id = ta.track_id "
        "JOIN artists a ON ta.artist_id = a.artist_id "
        "WHERE pl.playlist_type = 'curated' AND a.country = 'CO'",
        "high",
        ["EC-08", "EC-01"],
        False,
        "",
    ),
    (
        65,
        RELATIONAL,
        "What plan is each of our people on right now?",
        "SELECT u.display_name, p.name FROM subscription_periods sp "
        "JOIN users u ON sp.user_id = u.user_id "
        "JOIN subscription_plans p ON sp.plan_id = p.plan_id "
        "WHERE sp.period_end IS NULL",
        "high",
        ["EC-06", "EC-01"],
        False,
        "",
    ),
    # ---------------- Complex Analysis : 1 medium, 4 high -----------------
    (
        66,
        COMPLEX,
        "What share of the catalogue is explicit?",
        "SELECT COUNT(*) AS total_tracks, SUM(is_exp) AS explicit_tracks FROM tracks",
        "medium",
        ["EC-05"],
        False,
        "",
    ),
    (
        67,
        COMPLEX,
        "Which tracks outperform the average for their genre?",
        "SELECT t.title FROM tracks t "
        "JOIN track_genres tg ON t.track_id = tg.track_id "
        "WHERE t.total_plays > (SELECT AVG(t2.total_plays) FROM tracks t2 "
        "JOIN track_genres tg2 ON t2.track_id = tg2.track_id "
        "WHERE tg2.genre_id = tg.genre_id)",
        "high",
        ["EC-07", "EC-10"],
        False,
        "Compares the cached counter against itself, so it stays internally consistent.",
    ),
    (
        68,
        COMPLEX,
        "What's our skip rate by genre?",
        "SELECT g.name, ROUND(SUM(CASE WHEN pe.event_type = 'skip' THEN 1 ELSE 0 END) "
        "* 100.0 / COUNT(*), 2) AS skip_rate FROM genres g "
        "JOIN track_genres tg ON g.genre_id = tg.genre_id "
        "JOIN play_events pe ON tg.track_id = pe.track_id "
        "GROUP BY g.name ORDER BY skip_rate DESC",
        "high",
        ["EC-08", "EC-13"],
        True,
        "",
    ),
    (
        69,
        COMPLEX,
        "How much of the catalogue has nobody ever played?",
        "SELECT COUNT(*) FROM tracks WHERE track_id NOT IN "
        "(SELECT track_id FROM play_events WHERE event_type = 'play')",
        "high",
        ["EC-11", "EC-17"],
        False,
        "",
    ),
    (
        70,
        COMPLEX,
        "Which users follow an artist they've never actually listened to?",
        "SELECT DISTINCT u.display_name FROM users u "
        "JOIN user_follows_artists ufa ON u.user_id = ufa.user_id "
        "WHERE NOT EXISTS (SELECT 1 FROM play_events pe "
        "JOIN track_artists ta ON pe.track_id = ta.track_id "
        "WHERE pe.user_id = u.user_id AND ta.artist_id = ufa.artist_id)",
        "high",
        ["EC-14", "EC-08"],
        False,
        "",
    ),
    # ---------------- Deliberate Ambiguity : 5, all clarify ---------------
    (
        71,
        AMBIGUOUS,
        "Show me our best artists.",
        None,
        "high",
        ["EC-07"],
        False,
        "'Best' is undefined across at least four defensible metrics: raw play count, "
        "distinct listeners, daily_artist_metrics.stream_count and the cached "
        "monthly_listeners_cached — which disagree by orders of magnitude.",
    ),
    (
        72,
        AMBIGUOUS,
        "How are we doing this quarter?",
        None,
        "high",
        [],
        False,
        "No metric named at all. Revenue, plays, new users and churn are all plausible, "
        "and 'this quarter' itself needs pinning to a calendar.",
    ),
    (
        73,
        AMBIGUOUS,
        "Which tracks are popular?",
        None,
        "high",
        ["EC-07"],
        False,
        "'Popular' straddles tracks.total_plays (cached, billions) and COUNT(play_events) "
        "(raw, hundreds), with likes and saves as further readings.",
    ),
    (
        74,
        AMBIGUOUS,
        "Give me the top playlists.",
        None,
        "high",
        ["EC-08"],
        False,
        "Ambiguous twice over: 'top' by followers, track count or plays, and the "
        "playlists<->tracks route is the bridge the survey deliberately leaves "
        "unresolved between playlist_tracks and play_events.",
    ),
    (
        75,
        AMBIGUOUS,
        "How many active users do we have?",
        None,
        "high",
        ["EC-02", "EC-06"],
        False,
        "'Active' has three definitions in three tables: users.status = 1, a subscription "
        "period with period_end IS NULL, and recent play activity.",
    ),
]


def build() -> list[CorpusItem]:
    return [
        CorpusItem(
            id=f"EXEC-{number:03d}",
            corpus="idi_exec_75",
            category=category,
            difficulty=level,
            nl=nl,
            reference_sql=sql,
            order_matters=order_matters,
            expected_behaviour="clarify" if sql is None else "answer",
            ec_tags=ec_tags,
            evidence=None,
            accepted_alternatives=[],
            notes=notes,
        )
        for number, category, nl, sql, level, ec_tags, order_matters, notes in ITEMS
    ]


def main() -> None:
    from collections import Counter

    from evaluation.corpus import EXEC_CATEGORIES, EXEC_DIFFICULTY, execute
    from evaluation.hardness import EXEC_FROM_SPIDER, components, eval_hardness

    items = build()
    mismatches, failures = [], []
    for item in items:
        if item.reference_sql is None:
            continue
        computed = EXEC_FROM_SPIDER[eval_hardness(item.reference_sql)]
        if computed != item.difficulty:
            mismatches.append(
                f"  {item.id}: intended {item.difficulty!r}, computed {computed!r} "
                f"(spider={eval_hardness(item.reference_sql)}, "
                f"components={components(item.reference_sql)})  {item.nl[:40]}"
            )
        _, error = execute(item.reference_sql)
        if error:
            failures.append(f"  {item.id}: {error[:110]}")

    categories = Counter(i.category for i in items)
    difficulties = Counter(i.difficulty for i in items)
    print(f"items: {len(items)}  (clarify: {sum(1 for i in items if i.reference_sql is None)})")
    print(f"categories   : {dict(categories)}")
    print(f"target       : {EXEC_CATEGORIES}")
    print(f"difficulties : {dict(difficulties)}")
    print(f"target       : {EXEC_DIFFICULTY}")
    if mismatches:
        print(f"\ntier mismatches ({len(mismatches)}) — rewrite the SQL, do not relabel:")
        print("\n".join(mismatches))
    if failures:
        print(f"\nexecution failures ({len(failures)}):")
        print("\n".join(failures))
    if not mismatches and not failures:
        write_corpus("idi_exec_75", items)
        print("\nwrote data/benchmarks/corpora/idi_exec_75.jsonl")


if __name__ == "__main__":
    main()
