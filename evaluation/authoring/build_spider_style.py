"""Build data/benchmarks/corpora/spider_style.jsonl (60 items).

EVALUATION_PROTOCOL.md §2.1: "clean, formal phrasing; no business jargon, no
ambiguity. This subset isolates *structural* difficulty." Target histogram,
fixed by the protocol and not negotiable here:

    easy 24 (40%) | medium 24 (40%) | hard 9 (15%) | extra 3 (5%)

The `tier` on each row below is the author's *intent*. It is not what ships:
`main()` runs Spider's `eval_hardness` over the reference SQL and refuses to
write the manifest if intent and computation disagree, because §2.1 requires the
tier to be a property of the SQL. When they disagreed during authoring the query
was rewritten, never relabelled.

Phrasing rule for this corpus: every question names its own filter in schema
terms ("released before 2010", not "the classics"). Jargon, coded values and
ambiguity are the other three corpora's job; conflating them here would mean a
failure could not be attributed to structure.

Usage:  python -m evaluation.authoring.build_spider_style
"""

from __future__ import annotations

from evaluation.corpus import CorpusItem, write_corpus

# (id_number, natural language, reference SQL, intended tier, order_matters)
ITEMS: list[tuple[int, str, str, str, bool]] = [
    # -- easy: comp1 <= 1, others == 0 -------------------------------------
    (1, "List the names of all artists.", "SELECT name FROM artists", "easy", False),
    (2, "How many tracks are there?", "SELECT COUNT(*) FROM tracks", "easy", False),
    (
        3,
        "Show the titles of all albums whose album type is 'album'.",
        "SELECT title FROM albums WHERE album_type = 'album'",
        "easy",
        False,
    ),
    (
        4,
        "Which genres have no parent genre?",
        "SELECT name FROM genres WHERE parent_genre_id IS NULL",
        "easy",
        False,
    ),
    (
        5,
        "List the display names of all users ordered by the date they joined.",
        "SELECT display_name FROM users ORDER BY joined_at",
        "easy",
        True,
    ),
    (
        6,
        "How many users are from Colombia?",
        "SELECT COUNT(*) FROM users WHERE country = 'CO'",
        "easy",
        False,
    ),
    (
        7,
        "Which subscription plans allow offline downloads?",
        "SELECT name FROM subscription_plans WHERE has_downloads = 1",
        "easy",
        False,
    ),
    (
        8,
        "List the titles of all tracks marked as explicit.",
        "SELECT title FROM tracks WHERE is_exp = 1",
        "easy",
        False,
    ),
    (
        9,
        "What is the highest monthly price among the subscription plans?",
        "SELECT MAX(monthly_price) FROM subscription_plans",
        "easy",
        False,
    ),
    (
        10,
        "List the distinct countries that artists come from.",
        "SELECT DISTINCT country FROM artists",
        "easy",
        False,
    ),
    (
        11,
        "Show the names of all public playlists.",
        "SELECT name FROM playlists WHERE is_public = 1",
        "easy",
        False,
    ),
    (12, "How many play events are recorded?", "SELECT COUNT(*) FROM play_events", "easy", False),
    (
        13,
        "List track titles ordered from longest to shortest duration.",
        "SELECT title FROM tracks ORDER BY trk_dur_ms DESC",
        "easy",
        True,
    ),
    (
        14,
        "Which artists debuted before 2010?",
        "SELECT name FROM artists WHERE debut_year < 2010",
        "easy",
        False,
    ),
    (
        15,
        "What is the average track duration in milliseconds?",
        "SELECT AVG(trk_dur_ms) FROM tracks",
        "easy",
        False,
    ),
    (
        16,
        "List the email addresses of users whose status is 1.",
        "SELECT email FROM users WHERE status = 1",
        "easy",
        False,
    ),
    (
        17,
        "Which albums were released by the label 'Republic Records'?",
        "SELECT title FROM albums WHERE label = 'Republic Records'",
        "easy",
        False,
    ),
    (18, "List the names of all genres.", "SELECT name FROM genres", "easy", False),
    (
        19,
        "How many playlists were forked from another playlist?",
        "SELECT COUNT(*) FROM playlists WHERE forked_from_id IS NOT NULL",
        "easy",
        False,
    ),
    (
        20,
        "What is the earliest album release date on record?",
        "SELECT MIN(release_date) FROM albums",
        "easy",
        False,
    ),
    (
        21,
        "Show the titles of tracks that do not belong to any album.",
        "SELECT title FROM tracks WHERE album_id IS NULL",
        "easy",
        False,
    ),
    (
        22,
        "What is the total amount of all payments?",
        "SELECT SUM(amount) FROM payments",
        "easy",
        False,
    ),
    (
        23,
        "List the names of playlists whose type is 'curated'.",
        "SELECT name FROM playlists WHERE playlist_type = 'curated'",
        "easy",
        False,
    ),
    (
        24,
        "How many distinct users appear in the play events table?",
        "SELECT COUNT(DISTINCT user_id) FROM play_events",
        "easy",
        False,
    ),
    # -- medium ------------------------------------------------------------
    (
        25,
        "List the title and release date of every album, ordered by release date.",
        "SELECT title, release_date FROM albums ORDER BY release_date",
        "medium",
        True,
    ),
    (
        26,
        "Show the name and country of artists whose label is 'Warner Records'.",
        "SELECT name, country FROM artists WHERE label = 'Warner Records'",
        "medium",
        False,
    ),
    (
        27,
        "List the name and monthly price of each subscription plan, most expensive first.",
        "SELECT name, monthly_price FROM subscription_plans ORDER BY monthly_price DESC",
        "medium",
        True,
    ),
    (
        28,
        "How many users are there in each country?",
        "SELECT country, COUNT(*) FROM users GROUP BY country",
        "medium",
        False,
    ),
    (
        29,
        "Show each artist's name together with the titles of their albums.",
        "SELECT a.name, al.title FROM artists a JOIN albums al ON a.artist_id = al.artist_id",
        "medium",
        False,
    ),
    (
        30,
        "List the title and duration of tracks longer than 200000 milliseconds.",
        "SELECT title, trk_dur_ms FROM tracks WHERE trk_dur_ms > 200000",
        "medium",
        False,
    ),
    (
        31,
        "How many events of each event type are recorded?",
        "SELECT event_type, COUNT(*) FROM play_events GROUP BY event_type",
        "medium",
        False,
    ),
    (
        32,
        "Show the five playlists with the most followers, with their follower counts.",
        "SELECT name, follower_count FROM playlists ORDER BY follower_count DESC LIMIT 5",
        "medium",
        True,
    ),
    (
        33,
        "Show each user's display name alongside the start date of their subscription.",
        "SELECT u.display_name, s.start_date FROM users u "
        "JOIN subscriptions s ON u.user_id = s.user_id",
        "medium",
        False,
    ),
    (
        34,
        "What is the total payment amount for each payment method?",
        "SELECT payment_method, SUM(amount) FROM payments GROUP BY payment_method",
        "medium",
        False,
    ),
    (
        35,
        "List the titles of explicit tracks in alphabetical order.",
        "SELECT title FROM tracks WHERE is_exp = 1 ORDER BY title",
        "medium",
        True,
    ),
    (
        36,
        "Show the name and debut year of artists from the United States.",
        "SELECT name, debut_year FROM artists WHERE country = 'US'",
        "medium",
        False,
    ),
    (
        37,
        "How many artists come from each country, most represented country first?",
        # Ordering by the alias rather than repeating COUNT(*) is deliberate:
        # Spider counts aggregates across SELECT *and* ORDER BY, so the repeated
        # form scores two aggregates and lands in 'extra'. Same result set,
        # different computed tier — a reminder that the metric reads surface
        # form, which is exactly why §2.1 forbids relabelling.
        "SELECT country, COUNT(*) AS artist_count FROM artists "
        "GROUP BY country ORDER BY artist_count DESC",
        "medium",
        True,
    ),
    (
        38,
        "Show the genre name and track title for every track that has a genre.",
        "SELECT g.name, t.title FROM genres g "
        "JOIN track_genres tg ON g.genre_id = tg.genre_id "
        "JOIN tracks t ON tg.track_id = t.track_id",
        "medium",
        False,
    ),
    (
        39,
        "List the names of algorithmic playlists ordered by creation date.",
        "SELECT name FROM playlists WHERE playlist_type = 'algorithmic' ORDER BY created_at",
        "medium",
        True,
    ),
    (
        40,
        "How many play events came from each device type?",
        "SELECT device_type, COUNT(*) FROM play_events GROUP BY device_type",
        "medium",
        False,
    ),
    (
        41,
        "Show the ten tracks with the highest total play counts.",
        "SELECT title, total_plays FROM tracks ORDER BY total_plays DESC LIMIT 10",
        "medium",
        True,
    ),
    (
        42,
        "How many subscriptions exist for each plan?",
        "SELECT plan_id, COUNT(*) FROM subscriptions GROUP BY plan_id",
        "medium",
        False,
    ),
    (
        43,
        "Show the display name and country of users whose acquisition source is 3.",
        "SELECT display_name, country FROM users WHERE usr_acq_src = 3",
        "medium",
        False,
    ),
    (
        44,
        "How many albums has each artist released?",
        "SELECT a.name, COUNT(*) FROM artists a "
        "JOIN albums al ON a.artist_id = al.artist_id GROUP BY a.name",
        "medium",
        False,
    ),
    (
        45,
        "Show the metric date and stream count recorded for artist 1.",
        "SELECT metric_date, stream_count FROM daily_artist_metrics WHERE artist_id = 1",
        "medium",
        False,
    ),
    (
        46,
        "Show the name and maximum device count of plans that include hi-fi audio.",
        "SELECT name, max_devices FROM subscription_plans WHERE has_hifi = 1",
        "medium",
        False,
    ),
    (
        47,
        "List the titles of tracks longer than 180000 milliseconds that are not explicit.",
        "SELECT title FROM tracks WHERE trk_dur_ms > 180000 AND is_exp = 0",
        "medium",
        False,
    ),
    (
        48,
        "Show each user's display name together with the names of playlists they created.",
        "SELECT u.display_name, p.name FROM users u JOIN playlists p ON u.user_id = p.user_id",
        "medium",
        False,
    ),
    # -- hard --------------------------------------------------------------
    (
        49,
        "Show the name and country of the first five artists from Great Britain, "
        "in alphabetical order.",
        "SELECT name, country FROM artists WHERE country = 'GB' ORDER BY name LIMIT 5",
        "hard",
        True,
    ),
    (
        50,
        "How many play events does each track have, most played first?",
        "SELECT t.title, COUNT(*) FROM tracks t "
        "JOIN play_events pe ON t.track_id = pe.track_id "
        "GROUP BY t.title ORDER BY COUNT(*) DESC",
        "hard",
        True,
    ),
    (
        51,
        "Which artists are credited on at least one track?",
        "SELECT name FROM artists WHERE artist_id IN (SELECT artist_id FROM track_artists)",
        "hard",
        False,
    ),
    (
        52,
        "List the titles of tracks that belong to an album of type 'album'.",
        "SELECT title FROM tracks WHERE album_id IN "
        "(SELECT album_id FROM albums WHERE album_type = 'album')",
        "hard",
        False,
    ),
    (
        53,
        "Which users have a subscription with status 1?",
        "SELECT display_name FROM users WHERE user_id IN "
        "(SELECT user_id FROM subscriptions WHERE status = 1)",
        "hard",
        False,
    ),
    (
        54,
        "For users whose status is 1 and whose acquisition source is 2, how many are "
        "there in each country and status combination?",
        "SELECT u.country, COUNT(*) FROM users u "
        "WHERE u.status = 1 AND u.usr_acq_src = 2 GROUP BY u.country, u.status",
        "hard",
        False,
    ),
    (
        55,
        "For genres numbered between 1 and 100, how many track links and how many "
        "distinct tracks does each have?",
        "SELECT genre_id, COUNT(*), COUNT(DISTINCT track_id) FROM track_genres "
        "WHERE genre_id > 0 AND genre_id < 100 GROUP BY genre_id",
        "hard",
        False,
    ),
    (
        56,
        "Show the names of artists from Great Britain with the titles of their albums, "
        "ordered by album release date.",
        "SELECT a.name, al.title FROM artists a "
        "JOIN albums al ON a.artist_id = al.artist_id "
        "WHERE a.country = 'GB' ORDER BY al.release_date",
        "hard",
        True,
    ),
    (
        57,
        "List the titles of tracks in the Pop genre.",
        "SELECT t.title FROM tracks t "
        "JOIN track_genres tg ON t.track_id = tg.track_id "
        "JOIN genres g ON tg.genre_id = g.genre_id WHERE g.name = 'Pop'",
        "hard",
        False,
    ),
    # -- extra hard --------------------------------------------------------
    (
        58,
        "How many play events of type 'play' does each track have, most played first?",
        "SELECT t.title, COUNT(*) FROM tracks t "
        "JOIN play_events pe ON t.track_id = pe.track_id "
        "WHERE pe.event_type = 'play' "
        "GROUP BY t.track_id, t.title ORDER BY COUNT(*) DESC",
        "extra",
        True,
    ),
    (
        59,
        "Show the five artists with the most distinct listeners, counting only "
        "events of type 'play'.",
        "SELECT a.name, COUNT(DISTINCT pe.user_id) FROM artists a "
        "JOIN track_artists ta ON a.artist_id = ta.artist_id "
        "JOIN play_events pe ON ta.track_id = pe.track_id "
        "WHERE pe.event_type = 'play' "
        "GROUP BY a.artist_id, a.name ORDER BY COUNT(DISTINCT pe.user_id) DESC LIMIT 5",
        "extra",
        True,
    ),
    (
        60,
        "List, in alphabetical order, the titles of tracks that belong to an album.",
        "SELECT title FROM tracks WHERE album_id IN (SELECT album_id FROM albums) "
        "ORDER BY title",
        "extra",
        True,
    ),
]


def build() -> list[CorpusItem]:
    return [
        CorpusItem(
            id=f"SPIDER-{number:03d}",
            corpus="spider_style",
            category="Structural",
            difficulty=tier,
            nl=nl,
            reference_sql=sql,
            order_matters=order_matters,
            expected_behaviour="answer",
            ec_tags=[],
            evidence=None,
            accepted_alternatives=[],
            notes="",
        )
        for number, nl, sql, tier, order_matters in ITEMS
    ]


def main() -> None:
    from collections import Counter

    from evaluation.corpus import execute
    from evaluation.hardness import components, eval_hardness

    items = build()
    mismatches, failures = [], []
    for item in items:
        computed = eval_hardness(item.reference_sql)
        if computed != item.difficulty:
            mismatches.append(
                f"  {item.id}: intended {item.difficulty!r}, computed {computed!r} "
                f"components={components(item.reference_sql)}  {item.nl[:50]}"
            )
        _, error = execute(item.reference_sql)
        if error:
            failures.append(f"  {item.id}: {error[:100]}")

    histogram = Counter(eval_hardness(i.reference_sql) for i in items)
    print(f"items: {len(items)}")
    print(f"computed histogram: {dict(histogram)}")
    print("target histogram:   {'easy': 24, 'medium': 24, 'hard': 9, 'extra': 3}")
    if mismatches:
        print(f"\ntier mismatches ({len(mismatches)}) — rewrite the SQL, do not relabel:")
        print("\n".join(mismatches))
    if failures:
        print(f"\nexecution failures ({len(failures)}):")
        print("\n".join(failures))
    if not mismatches and not failures:
        write_corpus("spider_style", items)
        print("\nwrote data/benchmarks/corpora/spider_style.jsonl")


if __name__ == "__main__":
    main()
