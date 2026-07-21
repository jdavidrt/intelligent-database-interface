"""Build data/benchmarks/corpora/bird_style.jsonl (60 items).

EVALUATION_PROTOCOL.md §2.1: replicates BIRD's dirty-data and external-knowledge
pattern. Target histogram, fixed by the protocol:

    simple 30 (50%) | moderate 21 (35%) | challenging 9 (15%)

TIERS ARE COMPUTED, NOT ASSERTED — but BIRD's own labels are human-assigned by
its annotators, so there is no BIRD equivalent of Spider's `eval_hardness` to
port. §2.1's "computed, not asserted" rule is honoured here by deriving the BIRD
label from the computed Spider tier through the fixed mapping in
`hardness.BIRD_FROM_SPIDER` (easy/medium -> simple, hard -> moderate, extra ->
challenging). The mapping is part of the freeze; an item whose computed label
disagrees with its intent gets rewritten, never relabelled.

EVIDENCE. Every item carries BIRD's `evidence` device: a domain fact that cannot
be read off the schema. Without it several of these questions have no single
right answer, which is the point — BIRD measures whether external knowledge is
applied, not just whether SQL parses.

EC-07 AND THE CACHED COUNTERS. §9 quirk 2 (as amended v1.2) forbids
`accepted_alternatives` on these items. The pre-aggregated and raw sources do not
differ by the "~5%" the schema header long claimed — measured against the
seeded data they differ by roughly five orders of magnitude (The Weeknd: 225 raw
plays vs 65,314,971 in `daily_artist_metrics`). An item that accepts both is
therefore unfalsifiable, so each one names its source in the question or the
evidence and exactly one answer is correct.

Usage:  python -m evaluation.authoring.build_bird_style
"""

from __future__ import annotations

from evaluation.corpus import CorpusItem, write_corpus

# (n, nl, sql, intended_bird_tier, evidence, ec_tags, order_matters)
ITEMS: list[tuple[int, str, str, str, str, list[str], bool]] = [
    # ================= simple (Spider easy/medium) =======================
    (
        1,
        "How many payments actually went through?",
        "SELECT COUNT(*) FROM payments WHERE payment_status = 'completed'",
        "simple",
        "'Went through' means payment_status = 'completed'. The payments table also "
        "holds failed, refunded and pending rows, so an unfiltered COUNT overstates it.",
        ["EC-17"],
        False,
    ),
    (
        2,
        "How many times has a track actually been played?",
        "SELECT COUNT(*) FROM play_events WHERE event_type = 'play'",
        "simple",
        "'Played' means event_type = 'play', not any row of play_events — the table also "
        "records skip, save and share events.",
        ["EC-17"],
        False,
    ),
    (
        3,
        "How long is the average track in minutes?",
        "SELECT AVG(trk_dur_ms) / 60000.0 FROM tracks",
        "simple",
        "trk_dur_ms is an abbreviated column holding milliseconds; minutes require "
        "dividing by 60000.",
        ["EC-05"],
        False,
    ),
    (
        4,
        "How many users signed up organically?",
        "SELECT COUNT(*) FROM users WHERE usr_acq_src = 1",
        "simple",
        "usr_acq_src is an integer code: 1=organic, 2=social, 3=referral, 4=ad. "
        "The word 'organic' appears nowhere in the data.",
        ["EC-02", "EC-05"],
        False,
    ),
    (
        5,
        "How many standalone singles are in the catalogue?",
        "SELECT COUNT(*) FROM tracks WHERE album_id IS NULL",
        "simple",
        "A standalone single is a track with album_id IS NULL. Writing `album_id = NULL` "
        "returns zero rows in both MySQL and SQLite.",
        ["EC-03"],
        False,
    ),
    (
        6,
        "What is the current price of each subscription plan?",
        "SELECT plan_id, monthly_price FROM pricing_history WHERE effective_to IS NULL",
        "simple",
        "pricing_history is a slowly-changing dimension: effective_to IS NULL marks the "
        "row currently in force. subscription_plans.monthly_price is a denormalised copy.",
        ["EC-06"],
        False,
    ),
    (
        7,
        "How many users were brought in by another user?",
        "SELECT COUNT(*) FROM users WHERE referred_by_user_id IS NOT NULL",
        "simple",
        "referred_by_user_id IS NOT NULL identifies a referred signup. usr_acq_src = 3 is "
        "the self-reported channel and the two do not agree row for row.",
        ["EC-03", "EC-04"],
        False,
    ),
    (
        8,
        "How many banned users are there?",
        "SELECT COUNT(*) FROM users WHERE status = 2",
        "simple",
        "users.status is coded 0=inactive, 1=active, 2=banned. It is a different code set "
        "from subscriptions.status, which uses 2 for suspended.",
        ["EC-02", "EC-01"],
        False,
    ),
    (
        9,
        "How many tracks carry an explicit-content warning?",
        "SELECT COUNT(*) FROM tracks WHERE is_exp = 1",
        "simple",
        "is_exp is the abbreviated explicit-content flag, 1 = explicit.",
        ["EC-05"],
        False,
    ),
    (
        10,
        "How many plays happened outside of any playlist?",
        "SELECT COUNT(*) FROM play_events WHERE playlist_id IS NULL AND event_type = 'play'",
        "simple",
        "play_events.playlist_id is a nullable FK: NULL means the track was played outside "
        "a playlist context.",
        ["EC-03", "EC-17"],
        False,
    ),
    (
        11,
        "How much money have we actually collected?",
        "SELECT SUM(amount) FROM payments WHERE payment_status = 'completed'",
        "simple",
        "Only completed payments are revenue; failed and refunded rows must be excluded.",
        ["EC-17"],
        False,
    ),
    (
        12,
        "How many tracks has each user added to their likes?",
        "SELECT user_id, COUNT(*) FROM user_liked_tracks GROUP BY user_id",
        "simple",
        "The like list is user_liked_tracks. play_events with event_type = 'save' is a "
        "different action and the two sets only partly overlap.",
        ["EC-17"],
        False,
    ),
    (
        13,
        "How many skips are recorded?",
        "SELECT COUNT(*) FROM play_events WHERE event_type = 'skip'",
        "simple",
        "event_type is a string enum: play, skip, save, share.",
        ["EC-02"],
        False,
    ),
    (
        14,
        "Which subscriptions are still running?",
        "SELECT subscription_id FROM subscriptions WHERE end_date IS NULL",
        "simple",
        "end_date IS NULL means the subscription has not ended. status = 1 is a separate "
        "flag and can disagree with it.",
        ["EC-06", "EC-03"],
        False,
    ),
    (
        15,
        "How many payments were refunded?",
        "SELECT COUNT(*) FROM payments WHERE payment_status = 'refunded'",
        "simple",
        "payment_status enumerates completed, failed, refunded and pending.",
        ["EC-02", "EC-17"],
        False,
    ),
    (
        16,
        "What total stream count does the analytics table report?",
        "SELECT SUM(stream_count) FROM daily_artist_metrics",
        "simple",
        "daily_artist_metrics is the pre-aggregated ETL table and reports figures roughly "
        "five orders of magnitude above the raw event log. This question asks for the "
        "analytics figure specifically, so counting play_events is wrong here.",
        ["EC-07"],
        False,
    ),
    (
        17,
        "How many subscriptions are on the free tier?",
        "SELECT COUNT(*) FROM subscriptions s "
        "JOIN subscription_plans p ON s.plan_id = p.plan_id WHERE p.plan_type = 1",
        "simple",
        "plan_type is coded 1=free, 2=student, 3=individual, 4=family. The plan's name "
        "column happens to read 'Free' but the code is the reliable key.",
        ["EC-02"],
        False,
    ),
    (
        18,
        "How many hours of listening does the event log hold?",
        "SELECT SUM(duration_ms) / 3600000.0 FROM play_events WHERE event_type = 'play'",
        "simple",
        "duration_ms is milliseconds actually listened; an hour is 3600000 of them. "
        "trk_dur_ms on tracks is the full track length and is a different quantity.",
        ["EC-05", "EC-17"],
        False,
    ),
    (
        19,
        "Which playlists are copies of another playlist?",
        "SELECT name FROM playlists WHERE forked_from_id IS NOT NULL",
        "simple",
        "forked_from_id is a self-referencing nullable FK: non-NULL means this playlist "
        "was forked from the referenced one.",
        ["EC-04", "EC-03"],
        False,
    ),
    (
        20,
        "How many users are currently on a paid plan?",
        "SELECT COUNT(*) FROM subscription_periods " "WHERE period_end IS NULL AND monthly_fee > 0",
        "simple",
        "period_end IS NULL marks the currently running period; monthly_fee > 0 excludes "
        "the free tier, whose fee is 0.00.",
        ["EC-06", "EC-03"],
        False,
    ),
    (
        21,
        "What monthly listener figure is cached against each artist?",
        "SELECT name, monthly_listeners_cached FROM artists",
        "simple",
        "monthly_listeners_cached is a cached counter that drifts far from the raw event "
        "log — it reads in the tens of millions while the log holds hundreds of events. "
        "This question asks for the cached value as stored.",
        ["EC-07"],
        False,
    ),
    (
        22,
        "How many shares are recorded?",
        "SELECT COUNT(*) FROM play_events WHERE event_type = 'share'",
        "simple",
        "event_type = 'share' is one of the four values in the play_events enum.",
        ["EC-02"],
        False,
    ),
    (
        23,
        "Which tracks run longer than four minutes?",
        "SELECT title FROM tracks WHERE trk_dur_ms > 240000",
        "simple",
        "trk_dur_ms is milliseconds, so four minutes is 240000.",
        ["EC-05"],
        False,
    ),
    (
        24,
        "How many payments failed?",
        "SELECT COUNT(*) FROM payments WHERE payment_status = 'failed'",
        "simple",
        "payment_status = 'failed'; refunded is a separate outcome and must not be pooled "
        "with it unless the question asks for both.",
        ["EC-17"],
        False,
    ),
    (
        25,
        "How many distinct users have actually listened to something?",
        "SELECT COUNT(DISTINCT user_id) FROM play_events WHERE event_type = 'play'",
        "simple",
        "'Listened' is event_type = 'play'. Counting distinct users over all event types "
        "would include people who only skipped or shared.",
        ["EC-17"],
        False,
    ),
    (
        26,
        "Which artists are signed to Interscope?",
        "SELECT name FROM artists WHERE label LIKE '%Interscope%'",
        "simple",
        "artists.label is free text and one artist is stored under the joint imprint "
        "'PGLang / Interscope', so an equality test on 'Interscope Records' misses them.",
        ["EC-17"],
        False,
    ),
    (
        27,
        "How many subscriptions are suspended?",
        "SELECT COUNT(*) FROM subscriptions WHERE status = 2",
        "simple",
        "subscriptions.status is coded 0=inactive, 1=active, 2=suspended — note that the "
        "same integer means 'banned' in users.status.",
        ["EC-02", "EC-01"],
        False,
    ),
    (
        28,
        "Which genre is each artist's primary one?",
        "SELECT artist_id, genre_id FROM artist_genres WHERE is_prim = 1",
        "simple",
        "is_prim is the abbreviated primary-link flag. Artists carry several genre rows "
        "and only the flagged one is primary.",
        ["EC-05"],
        False,
    ),
    (
        29,
        "How many save events are in the log?",
        "SELECT COUNT(*) FROM play_events WHERE event_type = 'save'",
        "simple",
        "This is the event-log save action, which is distinct from the user_liked_tracks "
        "table; only a handful of rows appear in both.",
        ["EC-17"],
        False,
    ),
    (
        30,
        "What is the total cached play count across the catalogue?",
        "SELECT SUM(total_plays) FROM tracks",
        "simple",
        "tracks.total_plays is a cached counter, not the event log, and reads in the "
        "billions against a log of a few hundred plays. This question asks for the cached "
        "figure as stored.",
        ["EC-07"],
        False,
    ),
    # ================= moderate (Spider hard) ============================
    (
        31,
        "Which users have ever actually played something?",
        "SELECT display_name FROM users WHERE user_id IN "
        "(SELECT user_id FROM play_events WHERE event_type = 'play')",
        "moderate",
        "'Played' is event_type = 'play'; a user who only skipped tracks must not appear.",
        ["EC-17"],
        False,
    ),
    (
        32,
        "Which tracks has nobody ever liked?",
        "SELECT title FROM tracks WHERE track_id NOT IN "
        "(SELECT track_id FROM user_liked_tracks)",
        "moderate",
        "The like list is user_liked_tracks, not the save events in play_events.",
        ["EC-17"],
        False,
    ),
    (
        33,
        "How much revenue did each plan actually bring in?",
        "SELECT s.plan_id, SUM(pay.amount) AS revenue FROM payments pay "
        "JOIN subscriptions s ON pay.subscription_id = s.subscription_id "
        "WHERE pay.payment_status = 'completed' GROUP BY s.plan_id",
        "moderate",
        "Revenue counts completed payments only. The plan is reached through the "
        "subscription, since payments does not carry plan_id.",
        ["EC-17", "EC-08"],
        False,
    ),
    (
        34,
        "How many plays did each track get in 2026?",
        "SELECT t.title, COUNT(*) AS plays FROM tracks t "
        "JOIN play_events pe ON t.track_id = pe.track_id "
        "WHERE pe.event_type = 'play' AND YEAR(pe.played_at) = 2026 GROUP BY t.title",
        "moderate",
        "'Plays' excludes skips, saves and shares.",
        ["EC-17"],
        False,
    ),
    (
        35,
        "For active users, how many are there per country and how many distinct "
        "acquisition channels does each country show?",
        "SELECT country, COUNT(*) AS users, COUNT(DISTINCT usr_acq_src) AS channels "
        "FROM users WHERE status = 1 AND country IS NOT NULL GROUP BY country",
        "moderate",
        "users.status = 1 means active. usr_acq_src is the coded acquisition channel.",
        ["EC-02", "EC-05"],
        False,
    ),
    (
        36,
        # Authored first as "artists with no rows in the analytics table", which
        # is true of nobody in the seeded data. An item whose ground truth is
        # empty passes for any executable query that also returns nothing, so it
        # discriminates almost nothing — replaced with an anti-join of the same
        # shape and tier that actually has an answer.
        "Which users have never liked a single track?",
        "SELECT display_name FROM users WHERE user_id NOT IN "
        "(SELECT user_id FROM user_liked_tracks)",
        "moderate",
        "The like list is user_liked_tracks. A user who fired save events in play_events "
        "but never added a track to their likes still counts as never having liked one.",
        ["EC-17"],
        False,
    ),
    (
        37,
        "What does each plan currently cost, cheapest first?",
        "SELECT p.name, ph.monthly_price FROM pricing_history ph "
        "JOIN subscription_plans p ON ph.plan_id = p.plan_id "
        "WHERE ph.effective_to IS NULL ORDER BY ph.monthly_price",
        "moderate",
        "The authoritative current price is the pricing_history row with effective_to "
        "IS NULL, not subscription_plans.monthly_price.",
        ["EC-06"],
        True,
    ),
    (
        38,
        "Which users have referred at least one other user?",
        "SELECT display_name FROM users WHERE user_id IN "
        "(SELECT referred_by_user_id FROM users WHERE referred_by_user_id IS NOT NULL)",
        "moderate",
        "referred_by_user_id is a self-reference on users: the referrer is a user row "
        "reached through the same table.",
        ["EC-04"],
        False,
    ),
    (
        39,
        "How many completed payments did each user make in 2025?",
        "SELECT user_id, COUNT(*) AS payments FROM payments "
        "WHERE payment_status = 'completed' AND YEAR(payment_date) = 2025 "
        "GROUP BY user_id ORDER BY user_id",
        "moderate",
        "Only completed payments count; the year comes from payment_date.",
        ["EC-17"],
        True,
    ),
    (
        40,
        # Same correction as BIRD-036: every track in the seeded data has been
        # played at least once, so "never played" had an empty ground truth.
        # "Never skipped" exercises the same event_type discrimination and has
        # five real rows.
        "Which tracks has nobody ever skipped?",
        "SELECT title FROM tracks WHERE track_id NOT IN "
        "(SELECT track_id FROM play_events WHERE event_type = 'skip')",
        "moderate",
        "Skips are event_type = 'skip'. A track that was played and saved but never "
        "skipped belongs in this answer, so filtering on play_events without the "
        "event_type predicate returns nothing.",
        ["EC-17"],
        False,
    ),
    (
        41,
        "Which playlists contain at least one explicit track?",
        "SELECT name FROM playlists WHERE playlist_id IN "
        "(SELECT pt.playlist_id FROM playlist_tracks pt "
        "JOIN tracks t ON pt.track_id = t.track_id WHERE t.is_exp = 1)",
        "moderate",
        "is_exp is the explicit flag. Playlists reach tracks only through the "
        "playlist_tracks junction table.",
        ["EC-05", "EC-08"],
        False,
    ),
    (
        42,
        "Show the plan name and fee for every subscription period still running, "
        "cheapest first.",
        "SELECT p.name, sp.monthly_fee FROM subscription_periods sp "
        "JOIN subscription_plans p ON sp.plan_id = p.plan_id "
        "WHERE sp.period_end IS NULL ORDER BY sp.monthly_fee",
        "moderate",
        "period_end IS NULL marks the running period. monthly_fee is the fee actually "
        "charged for that period and can differ from the plan's list price.",
        ["EC-06"],
        True,
    ),
    (
        43,
        "For 2026, how many events of each type are there and how many distinct users "
        "produced them?",
        "SELECT event_type, COUNT(*) AS events, COUNT(DISTINCT user_id) AS users "
        "FROM play_events WHERE played_at >= '2026-01-01' AND played_at < '2027-01-01' "
        "GROUP BY event_type",
        "moderate",
        "event_type enumerates play, skip, save and share. Counting events and counting "
        "the users behind them are different questions and both are asked here.",
        ["EC-02"],
        False,
    ),
    (
        44,
        "Which artists have a track in the Reggaeton genre?",
        "SELECT name FROM artists WHERE artist_id IN "
        "(SELECT ta.artist_id FROM track_artists ta "
        "JOIN track_genres tg ON ta.track_id = tg.track_id "
        "JOIN genres g ON tg.genre_id = g.genre_id WHERE g.name = 'Reggaeton')",
        "moderate",
        "Genre attaches to tracks, not to artists directly, so the link runs "
        "artists -> track_artists -> track_genres -> genres.",
        ["EC-08"],
        False,
    ),
    (
        45,
        "How many distinct listeners does each artist have?",
        "SELECT ta.artist_id, COUNT(DISTINCT pe.user_id) AS listeners FROM track_artists ta "
        "JOIN play_events pe ON ta.track_id = pe.track_id "
        "WHERE pe.event_type = 'play' GROUP BY ta.artist_id",
        "moderate",
        "Distinct listeners means COUNT(DISTINCT user_id), not a row count — one listener "
        "generates many play events.",
        ["EC-15", "EC-17"],
        False,
    ),
    (
        46,
        "For active auto-renewing subscriptions, how many are there per plan and how "
        "many distinct users do they cover?",
        "SELECT plan_id, COUNT(*) AS subs, COUNT(DISTINCT user_id) AS users "
        "FROM subscriptions WHERE status = 1 AND auto_renew = 1 GROUP BY plan_id",
        "moderate",
        "subscriptions.status = 1 is active. A user can hold more than one subscription "
        "row, so the subscription count and the user count differ.",
        ["EC-02", "EC-15"],
        False,
    ),
    (
        47,
        "Which genres have no tracks assigned to them?",
        "SELECT name FROM genres WHERE genre_id NOT IN (SELECT genre_id FROM track_genres)",
        "moderate",
        "track_genres is the junction table; a genre absent from it has no tracks even "
        "though it may still be some other genre's parent.",
        ["EC-08"],
        False,
    ),
    (
        48,
        "List albums released after 2023 with their artist's name, newest first.",
        "SELECT a.name, al.title FROM albums al "
        "JOIN artists a ON al.artist_id = a.artist_id "
        "WHERE al.release_date > '2023-12-31' ORDER BY al.release_date DESC",
        "moderate",
        "Both albums and tracks carry title and release_date; this question is about " "albums.",
        ["EC-01"],
        True,
    ),
    (
        49,
        "Which users have never made a completed payment?",
        "SELECT display_name FROM users WHERE user_id NOT IN "
        "(SELECT user_id FROM payments WHERE payment_status = 'completed')",
        "moderate",
        "A user whose only payments failed or were refunded has never paid successfully.",
        ["EC-17"],
        False,
    ),
    (
        50,
        "Which device types generate the most plays?",
        "SELECT device_type, COUNT(*) AS plays FROM play_events "
        "WHERE event_type = 'play' GROUP BY device_type ORDER BY plays DESC",
        "moderate",
        "'Plays' excludes the other three event types.",
        ["EC-17"],
        True,
    ),
    (
        51,
        "Which tracks appear on at least one curated playlist?",
        "SELECT title FROM tracks WHERE track_id IN "
        "(SELECT pt.track_id FROM playlist_tracks pt "
        "JOIN playlists p ON pt.playlist_id = p.playlist_id "
        "WHERE p.playlist_type = 'curated')",
        "moderate",
        "playlist_type distinguishes curated, algorithmic and user playlists.",
        ["EC-02", "EC-08"],
        False,
    ),
    # ================= challenging (Spider extra) ========================
    (
        52,
        "How many completed payments did each user make during 2025?",
        "SELECT user_id, COUNT(*) AS payments FROM payments "
        "WHERE payment_status = 'completed' AND YEAR(payment_date) = 2025 GROUP BY user_id",
        "challenging",
        "Only completed payments count as payments made.",
        ["EC-17"],
        False,
    ),
    (
        53,
        "How many distinct listeners does each artist have, by name?",
        "SELECT a.name, COUNT(DISTINCT pe.user_id) AS listeners FROM artists a "
        "JOIN track_artists ta ON a.artist_id = ta.artist_id "
        "JOIN play_events pe ON ta.track_id = pe.track_id "
        "WHERE pe.event_type = 'play' GROUP BY a.name",
        "challenging",
        "Artists reach play events only through track_artists. Distinct listeners is "
        "COUNT(DISTINCT user_id), and only 'play' events count.",
        ["EC-08", "EC-15", "EC-17"],
        False,
    ),
    (
        54,
        "Which genres get played the most?",
        "SELECT g.name, COUNT(*) AS plays FROM genres g "
        "JOIN track_genres tg ON g.genre_id = tg.genre_id "
        "JOIN play_events pe ON tg.track_id = pe.track_id "
        "WHERE pe.event_type = 'play' GROUP BY g.name ORDER BY plays DESC",
        "challenging",
        "Genre attaches to tracks through track_genres; a track in two genres counts "
        "toward both. Only 'play' events count.",
        ["EC-08", "EC-17"],
        True,
    ),
    (
        55,
        "List, alphabetically, the tracks that have been played at least once.",
        "SELECT title FROM tracks WHERE track_id IN "
        "(SELECT track_id FROM play_events WHERE event_type = 'play') ORDER BY title",
        "challenging",
        "A track with only skip or save events has not been played.",
        ["EC-17"],
        True,
    ),
    (
        56,
        "Which tracks have a cached play count above the catalogue average, highest first?",
        "SELECT t.title FROM tracks t "
        "WHERE t.total_plays > (SELECT AVG(t2.total_plays) FROM tracks t2) "
        "ORDER BY t.total_plays DESC",
        "challenging",
        "total_plays is the cached counter and is the figure this question asks about; "
        "it drifts from the event log by several orders of magnitude, so recomputing "
        "from play_events answers a different question.",
        ["EC-07"],
        True,
    ),
    (
        57,
        "According to the analytics table, which artists streamed most in 2026?",
        "SELECT a.name, SUM(dam.stream_count) AS streams FROM daily_artist_metrics dam "
        "JOIN artists a ON dam.artist_id = a.artist_id "
        "WHERE YEAR(dam.metric_date) = 2026 GROUP BY a.name ORDER BY streams DESC",
        "challenging",
        "The question names daily_artist_metrics as its source. Counting play_events "
        "instead gives a number about five orders of magnitude smaller and is wrong here.",
        ["EC-07"],
        True,
    ),
    (
        58,
        "For each plan, how many completed payments were there and what did they total?",
        "SELECT p.name, COUNT(*) AS payments, SUM(pay.amount) AS total FROM payments pay "
        "JOIN subscriptions s ON pay.subscription_id = s.subscription_id "
        "JOIN subscription_plans p ON s.plan_id = p.plan_id "
        "WHERE pay.payment_status = 'completed' GROUP BY p.name",
        "challenging",
        "Revenue is completed payments only, and the plan is two joins away from the "
        "payment row.",
        ["EC-17", "EC-08"],
        False,
    ),
    (
        59,
        "Who are our ten most active listeners so far in 2026?",
        "SELECT u.display_name, COUNT(*) AS plays FROM users u "
        "JOIN play_events pe ON u.user_id = pe.user_id "
        "WHERE pe.event_type = 'play' AND pe.played_at >= '2026-01-01' "
        "GROUP BY u.display_name ORDER BY plays DESC LIMIT 10",
        "challenging",
        "Activity means play events, not skips or shares.",
        ["EC-17"],
        True,
    ),
    (
        60,
        "Which American artists are the main credited artist on at least one track, "
        "alphabetically?",
        "SELECT name FROM artists WHERE artist_id IN "
        "(SELECT artist_id FROM track_artists WHERE is_prim = 1) "
        "AND country = 'US' ORDER BY name",
        "challenging",
        "is_prim = 1 marks the main credit as opposed to a feature. artists.country and "
        "users.country are different columns holding the same kind of code.",
        ["EC-05", "EC-01"],
        True,
    ),
]


def build() -> list[CorpusItem]:
    return [
        CorpusItem(
            id=f"BIRD-{number:03d}",
            corpus="bird_style",
            category="Dirty data / external knowledge",
            difficulty=tier,
            nl=nl,
            reference_sql=sql,
            order_matters=order_matters,
            expected_behaviour="answer",
            ec_tags=ec_tags,
            evidence=evidence,
            accepted_alternatives=[],
            notes="",
        )
        for number, nl, sql, tier, evidence, ec_tags, order_matters in ITEMS
    ]


def main() -> None:
    from collections import Counter

    from evaluation.corpus import execute
    from evaluation.hardness import BIRD_FROM_SPIDER, components, eval_hardness

    items = build()
    mismatches, failures = [], []
    for item in items:
        computed = BIRD_FROM_SPIDER[eval_hardness(item.reference_sql)]
        if computed != item.difficulty:
            mismatches.append(
                f"  {item.id}: intended {item.difficulty!r}, computed {computed!r} "
                f"(spider={eval_hardness(item.reference_sql)}, "
                f"components={components(item.reference_sql)})  {item.nl[:44]}"
            )
        _, error = execute(item.reference_sql)
        if error:
            failures.append(f"  {item.id}: {error[:100]}")

    histogram = Counter(BIRD_FROM_SPIDER[eval_hardness(i.reference_sql)] for i in items)
    trapped = sum(1 for i in items if i.ec_tags)
    print(f"items: {len(items)}   with dirty-data traps: {trapped} (need >= 40)")
    print(f"computed histogram: {dict(histogram)}")
    print("target histogram:   {'simple': 30, 'moderate': 21, 'challenging': 9}")
    if mismatches:
        print(f"\ntier mismatches ({len(mismatches)}) — rewrite the SQL, do not relabel:")
        print("\n".join(mismatches))
    if failures:
        print(f"\nexecution failures ({len(failures)}):")
        print("\n".join(failures))
    if not mismatches and not failures:
        write_corpus("bird_style", items)
        print("\nwrote data/benchmarks/corpora/bird_style.jsonl")


if __name__ == "__main__":
    main()
