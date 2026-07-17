"""Hand-authored augmentation content for the soundwave LoRA training dataset.

Data only — no logic. Consumed by training/build_dataset.py.

Three blocks:
- GOLD_META: per-gold-query (Q01..Q30 in 03_soundwave_edge_cases.md) paraphrases,
  intent annotations, a rationale target, and optional value substitutions.
- TARGETED: standalone NL->SQL pairs oversampling EC-02 (business term -> flag /
  coded column) and EC-04 (self-join direction), the two probes where prompt
  engineering plateaued (docs/FineTuningFableRound1.md §5).
- PROBE_EVAL: authored gold SQL for the 8 gate_d1.py probe wordings — EVAL ONLY,
  never trained on, so execution-accuracy benchmarks stay uncontaminated.
- QU_EXTRA: query_understanding-only intent cases (requested_fields trailing
  clauses, ambiguity positives and negatives).

Substitution entries: {"nl": {token: replacement}, "sql": {token: replacement}}.
The NL map is applied to every wording (original + paraphrases) that contains the
token, plus the restatement and filters; the SQL map is applied to the gold SQL.
"""

# ---------------------------------------------------------------------------
# Q01..Q30 — the gold catalog augmentation
# ---------------------------------------------------------------------------

GOLD_META: dict[str, dict] = {
    "Q01": {
        "paraphrases": [
            "List the artists based in Colombia.",
            "Which artists come from Colombia?",
            "Give me every artist whose country is Colombia.",
            "What artists do we have from Colombia?",
        ],
        "restatement": "The user wants the list of artists whose country is Colombia.",
        "filters": ["artists.country = 'CO' (Colombia)"],
        "rationale": (
            "The question is about artists, so the country filter belongs on artists.country — "
            "not users.country, which also exists. Country values are ISO-3166 alpha-2 codes, "
            "so Colombia is stored as 'CO'."
        ),
        "subs": [
            {"nl": {"Colombia": "Canada"}, "sql": {"'CO'": "'CA'"}},
            {"nl": {"Colombia": "the United States"}, "sql": {"'CO'": "'US'"}},
            {"nl": {"Colombia": "the United Kingdom"}, "sql": {"'CO'": "'GB'"}},
            {"nl": {"Colombia": "South Korea"}, "sql": {"'CO'": "'KR'"}},
            {"nl": {"Colombia": "Puerto Rico"}, "sql": {"'CO'": "'PR'"}},
        ],
    },
    "Q02": {
        "paraphrases": [
            "Which plans offer lossless audio?",
            "What subscription plans come with hi-fi sound?",
            "Show the plans that support high-fidelity streaming.",
            "Which subscription tiers include lossless listening?",
        ],
        "restatement": "The user wants the subscription plans that include high-fidelity audio.",
        "filters": ["subscription_plans.has_hifi = 1"],
        "rationale": (
            "'High-fidelity audio' is a plan feature stored as the boolean flag "
            "subscription_plans.has_hifi — it is not a genre and not a track attribute, and no "
            "row stores the text 'hi-fi'. Filtering has_hifi = 1 returns the qualifying plans."
        ),
        "subs": [
            {
                "nl": {
                    "high-fidelity audio": "offline downloads",
                    "lossless audio": "offline downloads",
                    "hi-fi sound": "offline listening",
                    "high-fidelity streaming": "downloads for offline use",
                    "lossless listening": "offline playback",
                },
                "sql": {"has_hifi": "has_downloads"},
            },
        ],
    },
    "Q03": {
        "paraphrases": [
            "How many songs aren't attached to any album?",
            "Count the tracks that were released without an album.",
            "How many standalone singles are in the catalog?",
            "What's the number of tracks with no album?",
        ],
        "restatement": (
            "The user wants a count of tracks that are not linked to any album "
            "(standalone singles)."
        ),
        "filters": ["tracks.album_id IS NULL"],
        "rationale": (
            "Standalone singles are tracks whose album_id foreign key is NULL. The NULL check "
            "must use IS NULL — 'album_id = NULL' always evaluates to UNKNOWN in SQL and would "
            "silently return a count of 0."
        ),
    },
    "Q04": {
        "paraphrases": [
            "Give me the play counts per track for 2024.",
            "How often was each track streamed during 2024?",
            "Show each track's number of plays in 2024.",
            "For 2024, how many plays did every track get?",
        ],
        "restatement": (
            "The user wants, for each track, how many times it was played during 2024."
        ),
        "filters": [
            "play_events.event_type = 'play' (exclude skips, saves and shares)",
            "year of played_at = 2024",
        ],
        "time_range": "2024",
        "rationale": (
            "play_events stores several interaction types behind the event_type discriminator, "
            "so counting plays requires event_type = 'play' — a bare COUNT(*) would also count "
            "skips, saves and shares. Joining to tracks and grouping per track yields the 2024 "
            "play counts."
        ),
        "subs": [
            {"nl": {"2024": "2023"}, "sql": {"2024": "2023"}},
        ],
    },
    "Q05": {
        "paraphrases": [
            "Which albums came out after 2022?",
            "Show albums with a release date later than 2022.",
            "What albums were published after 2022?",
            "List every album that dropped after 2022.",
        ],
        "restatement": "The user wants the albums released after the end of 2022.",
        "filters": ["albums.release_date > '2022-12-31'"],
        "time_range": "after 2022",
        "rationale": (
            "The question asks about albums, so title and release_date must come from the albums "
            "table — both columns also exist on tracks, which is the classic wrong pick. A date "
            "comparison against '2022-12-31' keeps only albums released after 2022."
        ),
        "subs": [
            {"nl": {"2022": "2021"}, "sql": {"2022-12-31": "2021-12-31"}},
            {"nl": {"2022": "2023"}, "sql": {"2022-12-31": "2023-12-31"}},
        ],
    },
    "Q06": {
        "paraphrases": [
            "What does each plan cost per month right now?",
            "Show the current price of every subscription plan.",
            "What are the plans' monthly prices today?",
            "Give me each subscription plan with its present monthly price.",
        ],
        "restatement": "The user wants the current monthly price of each subscription plan.",
        "filters": ["pricing_history.effective_to IS NULL (the price currently in force)"],
        "rationale": (
            "Prices are tracked historically in pricing_history; the authoritative current price "
            "is the row whose effective_to is NULL. Joining subscription_plans to pricing_history "
            "on plan_id with that filter returns each plan's price in force today, even after "
            "price changes."
        ),
    },
    "Q07": {
        "paraphrases": [
            "Which users have played songs by The Weeknd?",
            "Who has listened to The Weeknd?",
            "List the users that streamed tracks by The Weeknd.",
            "Which listeners played music from The Weeknd?",
        ],
        "restatement": "The user wants the users who have played tracks by the artist The Weeknd.",
        "filters": ["artists.name = 'The Weeknd'", "play_events.event_type = 'play'"],
        "rationale": (
            "No bridge table is named in the question, but connecting users to an artist requires "
            "the chain users → play_events → track_artists → artists. event_type = 'play' keeps "
            "real listens only, and DISTINCT avoids repeating users who played several tracks."
        ),
        "subs": [
            {"nl": {"The Weeknd": "Taylor Swift"}, "sql": {"'The Weeknd'": "'Taylor Swift'"}},
            {"nl": {"The Weeknd": "Bad Bunny"}, "sql": {"'The Weeknd'": "'Bad Bunny'"}},
            {"nl": {"The Weeknd": "Karol G"}, "sql": {"'The Weeknd'": "'Karol G'"}},
            {"nl": {"The Weeknd": "Billie Eilish"}, "sql": {"'The Weeknd'": "'Billie Eilish'"}},
        ],
    },
    "Q08": {
        "paraphrases": [
            "Show every user's current subscription plan.",
            "Which plan is each user subscribed to right now?",
            "What plan does each user currently have?",
            "For each user, show their active plan today.",
        ],
        "restatement": "The user wants each user's currently active subscription plan.",
        "filters": ["subscription_periods.period_end IS NULL (the ongoing period)"],
        "rationale": (
            "subscription_periods is the slowly-changing-dimension table recording every plan "
            "interval per user; the current plan is the period whose period_end is NULL. Joining "
            "it to users and subscription_plans returns the plan in force right now, including "
            "for users who changed plans — a status flag on subscriptions would miss those."
        ),
    },
    "Q09": {
        "paraphrases": [
            "For each country, how many distinct artists do its users follow?",
            "Count the unique artists followed by listeners in each country.",
            "Per country, what's the number of different artists users follow?",
            "How many distinct artists are followed by users from each country?",
        ],
        "restatement": (
            "The user wants, per user country, the number of distinct artists followed."
        ),
        "metrics_extra": ["COUNT DISTINCT"],
        "filters": [],
        "rationale": (
            "'Unique artists' calls for COUNT(DISTINCT ufa.artist_id) — a plain COUNT would count "
            "follow rows, not distinct artists. Grouping users by country over the "
            "user_follows_artists bridge gives the per-country figure."
        ),
    },
    "Q10": {
        "paraphrases": [
            "What was each plan's revenue in the second quarter of 2023?",
            "Show revenue per subscription plan for Q2 2023.",
            "How much money did every plan bring in during Q2 2023?",
            "Total completed payments per plan between April and June 2023?",
        ],
        "restatement": (
            "The user wants the completed-payment revenue per subscription plan for Q2 2023."
        ),
        "filters": [
            "payments.payment_date BETWEEN '2023-04-01' AND '2023-06-30'",
            "payments.payment_status = 'completed'",
        ],
        "time_range": "Q2 2023 (April–June 2023)",
        "rationale": (
            "Revenue means completed payments only, so payment_status = 'completed' must "
            "accompany the Q2 2023 date range — otherwise failed and refunded payments inflate "
            "the total. Payments reach plans through the subscriptions table."
        ),
        "subs": [
            {
                "nl": {
                    "Q2 2023": "Q3 2023",
                    "second quarter of 2023": "third quarter of 2023",
                    "between April and June 2023": "between July and September 2023",
                },
                "sql": {
                    "'2023-04-01' AND '2023-06-30'": "'2023-07-01' AND '2023-09-30'",
                    "q2_2023_revenue": "q3_2023_revenue",
                },
            },
        ],
        "min_rows": 0,
    },
    "Q11": {
        "paraphrases": [
            "Show artists with over 5 unique listeners in any month of 2024.",
            "Which artists exceeded 5 distinct monthly listeners during 2024?",
            "Find the artists that had more than five different listeners per month in 2024.",
            "Which artists topped 5 unique listeners in a month in 2024?",
        ],
        "restatement": (
            "The user wants the artists whose distinct monthly listener count exceeded 5 in 2024."
        ),
        "metrics_extra": ["COUNT DISTINCT"],
        "filters": [
            "year of played_at = 2024",
            "play_events.event_type = 'play'",
            "more than 5 distinct listeners per artist per month (post-aggregation)",
        ],
        "time_range": "2024",
        "rationale": (
            "The 'more than 5 distinct listeners' condition applies to an aggregated count, so it "
            "belongs in HAVING with COUNT(DISTINCT pe.user_id) — placing an aggregate in WHERE is "
            "invalid SQL. Grouping by artist and month produces the per-month listener counts."
        ),
        "min_rows": 0,
    },
    "Q12": {
        "paraphrases": [
            "Which users follow artists they have never actually played?",
            "Find users following at least one artist whose music they never listened to.",
            "Show me followers who never streamed the artists they follow.",
            "Which users have never played anything by an artist they follow?",
        ],
        "restatement": (
            "The user wants users who follow at least one artist but have zero play events for "
            "that same artist."
        ),
        "filters": ["no play event exists for the same (user, followed artist) pair"],
        "rationale": (
            "The NOT EXISTS must be correlated on both user_id and artist_id: for each follow "
            "relationship we check that no play event exists for that same user and that same "
            "artist. A flat NOT IN over play_events would instead find users with zero plays "
            "overall — a different question."
        ),
    },
    "Q13": {
        "paraphrases": [
            "Show each referred user with their referrer's display name.",
            "Who referred each user? Show both names.",
            "List referred users next to the person who referred them.",
            "For every user that was referred, show who brought them in.",
        ],
        "restatement": (
            "The user wants each referred user together with the display name of their referrer."
        ),
        "filters": ["users.referred_by_user_id IS NOT NULL (implicit via the inner self-join)"],
        "rationale": (
            "Referrals live in users.referred_by_user_id, which points back at the users table "
            "itself — a self-join with two aliases (the referred user and the referrer) exposes "
            "both display names in one row."
        ),
    },
    "Q14": {
        "paraphrases": [
            "What are Rock's sub-genres?",
            "Show every genre whose parent genre is Rock.",
            "Which genres fall under Rock?",
            "List the sub-genres belonging to Rock.",
        ],
        "restatement": "The user wants the genres whose parent genre is Rock.",
        "filters": ["parent genre name = 'Rock'"],
        "rationale": (
            "The genre hierarchy is stored in the same table via genres.parent_genre_id, so a "
            "self-join is required: the child row's parent_genre_id must equal the parent row's "
            "genre_id, with the parent filtered to Rock. Filtering genre_id against Rock would "
            "return Rock itself, not its children."
        ),
        "subs": [
            {"nl": {"Rock": "Pop"}, "sql": {"'Rock'": "'Pop'"}},
            {"nl": {"Rock": "Hip-Hop"}, "sql": {"'Rock'": "'Hip-Hop'"}},
            {"nl": {"Rock": "Latin"}, "sql": {"'Rock'": "'Latin'"}},
            {"nl": {"Rock": "Electronic"}, "sql": {"'Rock'": "'Electronic'"}},
        ],
    },
    "Q15": {
        "paraphrases": [
            "Show tracks whose play count beats their genre's average.",
            "Which songs outperform the average plays of their own genre?",
            "Find tracks with more total plays than the genre average.",
            "Which tracks stream above the mean for their genre?",
        ],
        "restatement": (
            "The user wants the tracks whose total plays exceed the average total plays of their "
            "own genre."
        ),
        "filters": ["tracks.total_plays > per-genre average of total_plays"],
        "rationale": (
            "The comparison must be against the per-genre average, which requires a correlated "
            "subquery: the inner AVG is restricted to the same genre_id as the outer row. An "
            "uncorrelated subquery would compute the global average — same syntax shape, "
            "completely different meaning."
        ),
    },
    "Q16": {
        "paraphrases": [
            "Break down 2023 signups by acquisition channel.",
            "How many users joined via each acquisition source in 2023?",
            "Show 2023 new-user counts per acquisition channel.",
            "What was the 2023 signup count for each acquisition channel?",
        ],
        "restatement": (
            "The user wants, per acquisition channel, how many users signed up during 2023."
        ),
        "filters": ["year of joined_at = 2023"],
        "time_range": "2023",
        "rationale": (
            "usr_acq_src is an abbreviated, integer-coded column (1=Organic, 2=Social Media, "
            "3=Referral, 4=Ad Campaign), so the codes must be decoded with a CASE expression to "
            "return readable channel names, grouped over users whose joined_at falls in 2023."
        ),
        "subs": [
            {"nl": {"2023": "2022"}, "sql": {"2023": "2022"}},
        ],
    },
    "Q17": {
        "paraphrases": [
            "Which playlists include standalone singles?",
            "Find playlists containing tracks that don't belong to an album.",
            "Show playlists that have at least one track without an album.",
            "What playlists carry songs that aren't on any album?",
        ],
        "restatement": (
            "The user wants the playlists that contain tracks with no album (standalone singles)."
        ),
        "filters": ["tracks.album_id IS NULL"],
        "rationale": (
            "Standalone singles are tracks with album_id IS NULL, and the filter applies mid-join "
            "after traversing playlists → playlist_tracks → tracks. The single's title comes from "
            "tracks.title — not albums.title, which also exists."
        ),
    },
    "Q18": {
        "paraphrases": [
            "Rank artists by streams inside their primary genre.",
            "Within each primary genre, order the artists by total streams.",
            "Show artist stream rankings per primary genre.",
            "How do artists rank by plays within their main genre?",
        ],
        "restatement": (
            "The user wants each artist ranked by total streams within their primary genre."
        ),
        "metrics_extra": ["RANK"],
        "filters": [
            "artist_genres.is_prim = 1 (primary genre only)",
            "play_events.event_type = 'play'",
        ],
        "rationale": (
            "Ranking within a genre calls for RANK() OVER (PARTITION BY genre) ordered by the "
            "aggregated stream count. The artist_genres bridge must be restricted to is_prim = 1 "
            "so each artist is ranked only in their primary genre and not duplicated across all "
            "their genres."
        ),
    },
    "Q19": {
        "paraphrases": [
            "What's each artist's average monthly play count over all months?",
            "Compute the mean monthly plays per artist.",
            "On average, how many plays does each artist get per month?",
            "Show the average of monthly play totals for every artist.",
        ],
        "restatement": (
            "The user wants, per artist, the average of their monthly play totals across all "
            "months on record."
        ),
        "filters": ["play_events.event_type = 'play'"],
        "rationale": (
            "This is an average of counts: the inner query totals plays per artist per month, and "
            "the outer query averages those monthly totals. AVG(COUNT(*)) is invalid without the "
            "derived table, and a single-level aggregation answers a different question."
        ),
    },
    "Q20": {
        "paraphrases": [
            "For Karol G in 2024, compare streams from the analytics table with raw play events.",
            "Show Karol G's 2024 stream totals from both daily_artist_metrics and play_events.",
            "How do the cached analytics streams compare to raw play events for Karol G in 2024?",
            "Compare the reported and the raw 2024 stream counts for Karol G.",
        ],
        "restatement": (
            "The user wants Karol G's 2024 stream totals from the pre-aggregated metrics table "
            "and from raw play events, side by side."
        ),
        "filters": [
            "artists.name = 'Karol G'",
            "year = 2024",
            "play_events.event_type = 'play' for the raw source",
        ],
        "time_range": "2024",
        "rationale": (
            "The two sources intentionally disagree: daily_artist_metrics.stream_count is the "
            "pre-aggregated reporting figure, while COUNT over play_events is the raw count. "
            "UNION ALL keeps the two totals as separate labeled rows instead of conflating them "
            "in a single join, which would double-count."
        ),
        "subs": [
            {"nl": {"Karol G": "Bad Bunny"}, "sql": {"'Karol G'": "'Bad Bunny'"}},
            {"nl": {"Karol G": "The Weeknd"}, "sql": {"'Karol G'": "'The Weeknd'"}},
        ],
    },
    "Q21": {
        "paraphrases": [
            "Which artists' streams grew over 20% between 2023 and 2024?",
            "Show artists with more than 20% stream growth year over year, 2023 to 2024.",
            "Find artists whose 2024 stream total beat their 2023 total by more than 20%.",
            "Who grew their play counts by over 20% from 2023 to 2024?",
        ],
        "restatement": (
            "The user wants the artists whose total streams grew by more than 20% from 2023 to "
            "2024."
        ),
        "filters": ["growth ratio (2024 - 2023) / 2023 > 0.20", "play_events.event_type = 'play'"],
        "time_range": "2023 vs 2024",
        "rationale": (
            "Comparing two years requires two aggregation subqueries — the 2023 and 2024 stream "
            "totals per artist — joined on artist_id; a single pass grouped by year cannot "
            "compute the ratio. The 20% threshold is a ratio over the 2023 baseline, not a "
            "constant difference."
        ),
        "subs": [
            {"nl": {"20%": "50%"}, "sql": {"0.20": "0.50"}},
            {"nl": {"20%": "10%"}, "sql": {"0.20": "0.10"}},
        ],
        "min_rows": 0,
    },
    "Q22": {
        "paraphrases": [
            "What share of tracks has zero plays?",
            "What fraction of the catalog was never streamed?",
            "What's the percentage of tracks that were never played?",
            "How much of the track catalog has never been listened to?",
        ],
        "restatement": "The user wants the percentage of all tracks that have never been played.",
        "filters": ["no matching 'play' event (LEFT JOIN ... IS NULL)"],
        "rationale": (
            "Never-played tracks only survive if the event filter lives in the LEFT JOIN "
            "condition (pe.event_type = 'play' inside ON); moving it to WHERE collapses the outer "
            "join and reports zero never-played tracks. The percentage comes from a CASE WHEN "
            "pe.event_id IS NULL aggregate over all tracks."
        ),
    },
    "Q23": {
        "paraphrases": [
            "Total 2024 plays for the Latin genre including its sub-genres?",
            "How many plays did Latin and all its child genres get in 2024?",
            "Count 2024 streams across Latin and every sub-genre of Latin.",
            "What were the 2024 play counts for Latin and its sub-genres?",
        ],
        "restatement": (
            "The user wants 2024 play counts for the Latin genre and all of its sub-genres."
        ),
        "filters": [
            "genre is Latin or has Latin as parent",
            "play_events.event_type = 'play'",
            "year of played_at = 2024",
        ],
        "time_range": "2024",
        "rationale": (
            "'Latin and its sub-genres' requires traversing the hierarchy: keep genres whose "
            "genre_id is Latin's own id or whose parent_genre_id points at it. Track genres come "
            "from the track_genres bridge (not artist_genres), joined to play_events filtered to "
            "plays in 2024."
        ),
        "subs": [
            {"nl": {"Latin": "Pop"}, "sql": {"'Latin'": "'Pop'"}},
            {"nl": {"Latin": "Hip-Hop"}, "sql": {"'Latin'": "'Hip-Hop'"}},
            {"nl": {"Latin": "Rock"}, "sql": {"'Latin'": "'Rock'"}},
        ],
    },
    "Q24": {
        "paraphrases": [
            "Which plan was every user on during the third quarter of 2023?",
            "Show each user's subscription plan for Q3 2023.",
            "What plans were users on between July and September 2023?",
            "For Q3 2023, what plan did each user have?",
        ],
        "restatement": (
            "The user wants the subscription plan each user was on during Q3 2023 (July–September)."
        ),
        "filters": [
            "period_start <= '2023-09-30'",
            "period_end IS NULL OR period_end >= '2023-07-01' (overlap, ongoing included)",
        ],
        "time_range": "Q3 2023 (July–September 2023)",
        "rationale": (
            "A period covers Q3 2023 if it started on or before the quarter's end and ended on or "
            "after its start — with period_end IS NULL meaning still ongoing. A naive BETWEEN on "
            "period_start misses periods that began earlier but were still active during the "
            "quarter."
        ),
    },
    "Q25": {
        "paraphrases": [
            "Which genres get skipped more than 10% of the time?",
            "Show genres whose skip share of interactions exceeds 10%.",
            "Find genres with a skip ratio above ten percent.",
            "What genres have over 10% of their events as skips?",
        ],
        "restatement": (
            "The user wants the genres whose skip events exceed 10% of their total interactions."
        ),
        "filters": ["skip ratio above 10% of all events per genre (post-aggregation)"],
        "rationale": (
            "The skip rate needs skips and total interactions from the same rows, so skips are "
            "counted with SUM(CASE WHEN event_type = 'skip' ...) over all events — filtering "
            "skips in WHERE would destroy the denominator. The 10% threshold applies "
            "post-aggregation in HAVING."
        ),
        "min_rows": 0,
    },
    "Q26": {
        "paraphrases": [
            "Which curated playlists feature Colombian artists?",
            "Show curated playlists containing music by artists from Colombia.",
            "List the curated playlists that include songs from artists based in Colombia.",
            "What curated playlists have tracks by artists from Colombia?",
        ],
        "restatement": (
            "The user wants the curated playlists containing tracks by artists from Colombia."
        ),
        "filters": ["playlists.playlist_type = 'curated'", "artists.country = 'CO' (Colombia)"],
        "rationale": (
            "The full chain playlists → playlist_tracks → tracks → track_artists → artists "
            "connects playlists to artist countries. playlist_type = 'curated' is a stored enum "
            "value, and the country filter goes on artists.country — not users.country."
        ),
        "subs": [
            {
                "nl": {"Colombia": "Canada", "Colombian artists": "Canadian artists"},
                "sql": {"'CO'": "'CA'"},
            },
            {
                "nl": {"Colombia": "the United States", "Colombian artists": "American artists"},
                "sql": {"'CO'": "'US'"},
            },
        ],
    },
    "Q27": {
        "paraphrases": [
            "Which forked playlists added tracks that the original didn't have?",
            "Show tracks in forked playlists that are missing from their source playlist.",
            "Find forks containing songs not present in the playlist they were forked from.",
            "What tracks do forked playlists have that their originals lack?",
        ],
        "restatement": (
            "The user wants forked playlists' tracks that do not appear in the playlist they were "
            "forked from."
        ),
        "filters": ["track absent from the specific source playlist (correlated NOT EXISTS)"],
        "rationale": (
            "playlists.forked_from_id self-joins each fork to its origin, and a correlated NOT "
            "EXISTS checks that the fork's track is absent from that specific original playlist — "
            "not from playlists in general, which an uncorrelated EXCEPT would compute."
        ),
    },
    "Q28": {
        "paraphrases": [
            "Who was the most-streamed artist for each acquisition channel in 2024?",
            "Per acquisition channel, which artist got the most plays in 2024?",
            "Show 2024's top artist by streams for every user acquisition source.",
            "For each acquisition source, which artist was played the most in 2024?",
        ],
        "restatement": (
            "The user wants, for each user acquisition channel, the artist with the most streams "
            "in 2024."
        ),
        "metrics_extra": ["RANK"],
        "filters": [
            "play_events.event_type = 'play'",
            "year of played_at = 2024",
            "rank = 1 within each acquisition channel",
        ],
        "time_range": "2024",
        "rationale": (
            "Top-N per group needs RANK() OVER (PARTITION BY usr_acq_src) ordered by the play "
            "count, filtered to rank 1 in the outer query — a global ORDER BY ... LIMIT 1 returns "
            "one artist overall, not one per channel. The integer channel codes are decoded with "
            "a CASE expression."
        ),
    },
    "Q29": {
        "paraphrases": [
            "Which genre ranked second by streams in 2024?",
            "What was 2024's number-two genre by play count?",
            "Give me the runner-up genre by total streams in 2024.",
            "What's the second most popular genre of 2024 by plays?",
        ],
        "restatement": "The user wants the genre with the second-highest stream count in 2024.",
        "metrics_extra": ["DENSE_RANK"],
        "filters": [
            "play_events.event_type = 'play'",
            "year of played_at = 2024",
            "dense rank = 2",
        ],
        "time_range": "2024",
        "rationale": (
            "'Second most' maps to DENSE_RANK() = 2 over the per-genre stream counts, which "
            "handles ties correctly; LIMIT 1 OFFSET 1 silently skips tied genres. Descending "
            "order matters — ascending would return the least-streamed genre instead."
        ),
        "subs": [
            {
                "nl": {"second": "third", "number-two": "number-three", "runner-up": "third-place"},
                "sql": {"rnk = 2": "rnk = 3"},
            },
        ],
    },
    "Q30": {
        "paraphrases": [
            "Show artists whose unique Q3 listeners grew over 30% from 2023 to 2024, ignoring "
            "artists with under 3 events in Q3 2023, ordered by growth.",
            "Which artists increased distinct Q3 listeners by more than 30% year over year, "
            "excluding low-volume artists with fewer than 3 events in Q3 2023?",
            "Rank by growth the artists whose unique listeners rose more than 30% between Q3 2023 "
            "and Q3 2024, skipping artists below 3 events in the 2023 quarter.",
        ],
        "restatement": (
            "The user wants artists whose distinct Q3 listeners grew more than 30% from 2023 to "
            "2024, excluding artists with fewer than 3 events in Q3 2023, ranked by growth rate."
        ),
        "metrics_extra": ["COUNT DISTINCT"],
        "filters": [
            "play_events.event_type = 'play'",
            "Q3 windows: 2023-07-01..2023-09-30 and 2024-07-01..2024-09-30",
            "HAVING at least 3 events in Q3 2023",
            "growth ratio > 0.30",
        ],
        "time_range": "Q3 2023 vs Q3 2024",
        "rationale": (
            "Four patterns combine: COUNT(DISTINCT user_id) for unique listeners in each Q3 "
            "window, a HAVING filter that drops artists with fewer than 3 events in the 2023 "
            "baseline, a growth ratio over that baseline as the WHERE condition, and the "
            "multi-hop artist → track_artists → play_events chain inside both subqueries."
        ),
        "min_rows": 0,
    },
}


# ---------------------------------------------------------------------------
# TARGETED — EC-02 / EC-04 oversampling pairs (new gold, not in the Q catalog)
# ---------------------------------------------------------------------------

TARGETED: list[dict] = [
    # ---- EC-02: business vocabulary -> boolean flags / coded columns ----
    {
        "id": "T02-01",
        "ec": "EC-02",
        "nl": "Which plans include offline downloads?",
        "paraphrases": [
            "What subscription plans let you download music for offline listening?",
            "Show the plans that support downloads.",
            "Which subscription tiers allow offline playback?",
        ],
        "sql": (
            "SELECT name, monthly_price, plan_type\nFROM subscription_plans\n"
            "WHERE has_downloads = 1;"
        ),
        "restatement": "The user wants the subscription plans that include offline downloads.",
        "filters": ["subscription_plans.has_downloads = 1"],
        "rationale": (
            "'Offline downloads' is a plan feature stored as the boolean flag "
            "subscription_plans.has_downloads; filtering it to 1 returns the qualifying plans. "
            "No plan name or type contains the word 'download'."
        ),
    },
    {
        "id": "T02-02",
        "ec": "EC-02",
        "nl": "How many tracks are marked as explicit?",
        "paraphrases": [
            "Count the explicit tracks in the catalog.",
            "How many songs carry the explicit label?",
            "What's the number of explicit-content tracks?",
        ],
        "sql": "SELECT COUNT(*) AS explicit_tracks\nFROM tracks\nWHERE is_exp = 1;",
        "restatement": "The user wants a count of tracks flagged as explicit content.",
        "filters": ["tracks.is_exp = 1"],
        "rationale": (
            "Explicit content is stored in the abbreviated boolean flag tracks.is_exp (1 = "
            "explicit). The count filters is_exp = 1 — there is no 'explicit' text value stored "
            "anywhere."
        ),
    },
    {
        "id": "T02-03",
        "ec": "EC-02",
        "nl": "Which tracks are clean, meaning not explicit?",
        "paraphrases": [
            "List the non-explicit tracks.",
            "Show me the tracks without the explicit label.",
            "What songs are family-friendly (not explicit)?",
        ],
        "sql": "SELECT title, trk_dur_ms, release_date\nFROM tracks\nWHERE is_exp = 0;",
        "restatement": "The user wants the tracks that are not flagged as explicit.",
        "filters": ["tracks.is_exp = 0"],
        "rationale": (
            "'Clean' / 'not explicit' maps to the boolean flag tracks.is_exp = 0. The flag is "
            "abbreviated — is_exp stands for is-explicit — and holds 1 for explicit, 0 for clean."
        ),
    },
    {
        "id": "T02-04",
        "ec": "EC-02",
        "nl": "How many users are banned?",
        "paraphrases": [
            "Count the banned user accounts.",
            "How many accounts have been banned?",
            "What's the number of banned users on the platform?",
        ],
        "sql": "SELECT COUNT(*) AS banned_users\nFROM users\nWHERE status = 2;",
        "restatement": "The user wants a count of banned user accounts.",
        "filters": ["users.status = 2 (banned)"],
        "rationale": (
            "User account state is integer-coded in users.status: 0 = inactive, 1 = active, "
            "2 = banned. 'Banned' therefore filters status = 2 — the word 'banned' is never "
            "stored as text."
        ),
    },
    {
        "id": "T02-05",
        "ec": "EC-02",
        "nl": "Show the inactive users.",
        "paraphrases": [
            "Which user accounts are inactive?",
            "List every user whose account is inactive.",
            "Who are the inactive members?",
        ],
        "sql": "SELECT display_name, email, country, last_login\nFROM users\nWHERE status = 0;",
        "restatement": "The user wants the users whose account status is inactive.",
        "filters": ["users.status = 0 (inactive)"],
        "rationale": (
            "users.status is integer-coded (0 = inactive, 1 = active, 2 = banned), so inactive "
            "accounts are the rows with status = 0."
        ),
    },
    {
        "id": "T02-06",
        "ec": "EC-02",
        "nl": "How many active users do we have?",
        "paraphrases": [
            "Count the users with an active account.",
            "What's the active user count?",
            "How many accounts are currently active?",
        ],
        "sql": "SELECT COUNT(*) AS active_users\nFROM users\nWHERE status = 1;",
        "restatement": "The user wants a count of users whose account status is active.",
        "filters": ["users.status = 1 (active)"],
        "rationale": (
            "Account state is integer-coded in users.status; active accounts are status = 1 "
            "(0 = inactive, 2 = banned)."
        ),
    },
    {
        "id": "T02-07",
        "ec": "EC-02",
        "nl": "Which users joined through a referral?",
        "paraphrases": [
            "Show the users acquired via the referral channel.",
            "List users whose acquisition source was a referral.",
            "Who signed up through referrals?",
        ],
        "sql": "SELECT display_name, country, joined_at\nFROM users\nWHERE usr_acq_src = 3;",
        "restatement": "The user wants the users whose acquisition source is the referral channel.",
        "filters": ["users.usr_acq_src = 3 (referral)"],
        "rationale": (
            "The acquisition channel lives in the abbreviated, integer-coded column usr_acq_src "
            "(1 = organic, 2 = social, 3 = referral, 4 = ad). Referral signups filter "
            "usr_acq_src = 3."
        ),
    },
    {
        "id": "T02-08",
        "ec": "EC-02",
        "nl": "How many users came from ad campaigns?",
        "paraphrases": [
            "Count the users acquired through ads.",
            "How many signups did the ad channel produce?",
            "What's the number of users whose acquisition source was advertising?",
        ],
        "sql": "SELECT COUNT(*) AS ad_acquired_users\nFROM users\nWHERE usr_acq_src = 4;",
        "restatement": "The user wants a count of users acquired through the ad channel.",
        "filters": ["users.usr_acq_src = 4 (ad campaign)"],
        "rationale": (
            "usr_acq_src is integer-coded (1 = organic, 2 = social, 3 = referral, 4 = ad); users "
            "from ad campaigns are the rows with usr_acq_src = 4."
        ),
    },
    {
        "id": "T02-09",
        "ec": "EC-02",
        "nl": "List the verified artists.",
        "paraphrases": [
            "Which artists have a verified profile?",
            "Show every verified artist.",
            "Who are the verified artists on the platform?",
        ],
        "sql": "SELECT name, country, monthly_listeners_cached\nFROM artists\nWHERE verified = 1;",
        "restatement": "The user wants the artists whose profile is verified.",
        "filters": ["artists.verified = 1"],
        "rationale": (
            "Verification is the boolean flag artists.verified; verified artists are the rows "
            "with verified = 1."
        ),
    },
    {
        "id": "T02-10",
        "ec": "EC-02",
        "nl": "Which playlists are private?",
        "paraphrases": [
            "Show the playlists that are not public.",
            "List every private playlist.",
            "What playlists are hidden from the public?",
        ],
        "sql": "SELECT name, playlist_type, follower_count\nFROM playlists\nWHERE is_public = 0;",
        "restatement": "The user wants the playlists that are not public.",
        "filters": ["playlists.is_public = 0"],
        "rationale": (
            "Visibility is the boolean flag playlists.is_public; private playlists are the rows "
            "with is_public = 0."
        ),
    },
    {
        "id": "T02-11",
        "ec": "EC-02",
        "nl": "Show the algorithmic playlists.",
        "paraphrases": [
            "Which playlists were generated algorithmically?",
            "List the playlists of type algorithmic.",
            "What playlists does the algorithm build?",
        ],
        "sql": (
            "SELECT name, follower_count, created_at\nFROM playlists\n"
            "WHERE playlist_type = 'algorithmic';"
        ),
        "restatement": "The user wants the playlists whose type is algorithmic.",
        "filters": ["playlists.playlist_type = 'algorithmic'"],
        "rationale": (
            "playlist_type is a stored enum with the values 'user', 'curated' and 'algorithmic'; "
            "algorithmic playlists filter the exact stored string 'algorithmic'."
        ),
    },
    {
        "id": "T02-12",
        "ec": "EC-02",
        "nl": "How many share events happened in 2024?",
        "paraphrases": [
            "Count the times tracks were shared in 2024.",
            "How often did users share tracks during 2024?",
            "What's the 2024 share count across all tracks?",
        ],
        "sql": (
            "SELECT COUNT(*) AS share_events_2024\nFROM play_events\n"
            "WHERE event_type = 'share'\n  AND YEAR(played_at) = 2024;"
        ),
        "restatement": "The user wants a count of share events during 2024.",
        "filters": ["play_events.event_type = 'share'", "year of played_at = 2024"],
        "time_range": "2024",
        "rationale": (
            "Shares live in the polymorphic play_events table behind the event_type "
            "discriminator; counting them requires event_type = 'share' with the 2024 date "
            "filter — a bare COUNT(*) would also count plays, skips and saves."
        ),
    },
    {
        "id": "T02-13",
        "ec": "EC-02",
        "nl": "Who is the primary artist on each track?",
        "paraphrases": [
            "Show every track with its primary artist.",
            "For each track, list the main credited artist.",
            "Which artist is the lead on each track?",
        ],
        "sql": (
            "SELECT t.title, a.name AS primary_artist\nFROM tracks t\n"
            "JOIN track_artists ta ON t.track_id = ta.track_id AND ta.is_prim = 1\n"
            "JOIN artists a ON ta.artist_id = a.artist_id\nORDER BY t.title;"
        ),
        "restatement": "The user wants each track paired with its primary artist.",
        "filters": ["track_artists.is_prim = 1 (primary credit only)"],
        "rationale": (
            "Track credits live in the track_artists bridge, where the abbreviated boolean "
            "is_prim marks the primary artist. Restricting the join to is_prim = 1 returns one "
            "main artist per credit instead of every collaborator."
        ),
    },
    {
        "id": "T02-14",
        "ec": "EC-02",
        "nl": "Which plans offer hi-fi audio but not offline downloads?",
        "paraphrases": [
            "Show plans with lossless sound that lack download support.",
            "What subscription plans have high-fidelity audio and no offline downloads?",
        ],
        "sql": (
            "SELECT name, monthly_price, plan_type\nFROM subscription_plans\n"
            "WHERE has_hifi = 1\n  AND has_downloads = 0;"
        ),
        "restatement": (
            "The user wants the plans that include high-fidelity audio but do not include "
            "offline downloads."
        ),
        "filters": ["subscription_plans.has_hifi = 1", "subscription_plans.has_downloads = 0"],
        "rationale": (
            "Both features are boolean flags on subscription_plans: 'hi-fi audio' is has_hifi "
            "and 'offline downloads' is has_downloads. The combination requires has_hifi = 1 "
            "with has_downloads = 0 — neither feature is stored as text."
        ),
        "min_rows": 0,
    },
    {
        "id": "T02-15",
        "ec": "EC-02",
        "nl": "How many suspended subscriptions are there?",
        "paraphrases": [
            "Count the subscriptions that are suspended.",
            "What's the number of suspended subscriptions?",
        ],
        "sql": "SELECT COUNT(*) AS suspended_subscriptions\nFROM subscriptions\nWHERE status = 2;",
        "restatement": "The user wants a count of subscriptions whose status is suspended.",
        "filters": ["subscriptions.status = 2 (suspended)"],
        "rationale": (
            "subscriptions.status is integer-coded (0 = inactive, 1 = active, 2 = suspended) — a "
            "different code map than users.status, where 2 means banned. Suspended subscriptions "
            "are status = 2 on the subscriptions table."
        ),
        "min_rows": 0,
    },
    # ---- EC-04: self-join direction (both sides, all three hierarchies) ----
    {
        "id": "T04-01",
        "ec": "EC-04",
        "nl": "Which genres are parents of other genres?",
        "paraphrases": [
            "Show the genres that have at least one sub-genre.",
            "List the genres that act as parent genres.",
            "What genres have child genres underneath them?",
        ],
        "sql": (
            "SELECT DISTINCT parent.name AS parent_genre\nFROM genres child\n"
            "JOIN genres parent ON child.parent_genre_id = parent.genre_id\n"
            "ORDER BY parent.name;"
        ),
        "restatement": "The user wants the genres that have at least one sub-genre.",
        "filters": ["genre appears as another genre's parent"],
        "rationale": (
            "The hierarchy lives in genres.parent_genre_id, and here the question asks for the "
            "PARENT side: a genre qualifies when some child row's parent_genre_id points at its "
            "genre_id. The self-join direction matters — selecting the child side would return "
            "the sub-genres instead."
        ),
    },
    {
        "id": "T04-02",
        "ec": "EC-04",
        "nl": "Show each sub-genre together with its parent genre.",
        "paraphrases": [
            "List every child genre and the genre it belongs to.",
            "For each sub-genre, what is its parent genre?",
            "Map all sub-genres to their parents.",
        ],
        "sql": (
            "SELECT child.name AS subgenre, parent.name AS parent_genre\nFROM genres child\n"
            "JOIN genres parent ON child.parent_genre_id = parent.genre_id\n"
            "ORDER BY parent.name, child.name;"
        ),
        "restatement": "The user wants every sub-genre listed with its parent genre.",
        "filters": ["genre has a parent (inner self-join keeps only children)"],
        "rationale": (
            "A self-join over genres.parent_genre_id pairs each child row with its parent row; "
            "the inner join naturally drops top-level genres, whose parent_genre_id is NULL."
        ),
    },
    {
        "id": "T04-03",
        "ec": "EC-04",
        "nl": "List the top-level genres.",
        "paraphrases": [
            "Which genres have no parent genre?",
            "Show the root genres of the hierarchy.",
            "What are the main genres that don't belong under any other genre?",
        ],
        "sql": "SELECT name\nFROM genres\nWHERE parent_genre_id IS NULL\nORDER BY name;",
        "restatement": "The user wants the genres that have no parent (top-level genres).",
        "filters": ["genres.parent_genre_id IS NULL"],
        "rationale": (
            "Top-level genres are the rows whose parent_genre_id is NULL — no self-join is "
            "needed to identify roots, only the IS NULL check on the self-referencing column."
        ),
    },
    {
        "id": "T04-04",
        "ec": "EC-04",
        "nl": "How many sub-genres does each parent genre have?",
        "paraphrases": [
            "Count the child genres under every parent genre.",
            "Per parent genre, how many sub-genres exist?",
        ],
        "sql": (
            "SELECT parent.name AS parent_genre, COUNT(*) AS subgenre_count\nFROM genres child\n"
            "JOIN genres parent ON child.parent_genre_id = parent.genre_id\n"
            "GROUP BY parent.genre_id, parent.name\nORDER BY subgenre_count DESC;"
        ),
        "restatement": "The user wants, per parent genre, the number of its sub-genres.",
        "filters": [],
        "rationale": (
            "Counting children per parent means grouping the self-join by the PARENT side: each "
            "child row contributes to the parent its parent_genre_id points at. Grouping by the "
            "child side would answer a different question."
        ),
    },
    {
        "id": "T04-05",
        "ec": "EC-04",
        "nl": "Which genres have no sub-genres at all?",
        "paraphrases": [
            "Show the genres without any child genres.",
            "List the leaf genres — those nothing points to as a parent.",
        ],
        "sql": (
            "SELECT g.name\nFROM genres g\nWHERE NOT EXISTS (\n"
            "    SELECT 1 FROM genres child WHERE child.parent_genre_id = g.genre_id\n"
            ")\nORDER BY g.name;"
        ),
        "restatement": "The user wants the genres that are nobody's parent (no sub-genres).",
        "filters": ["no child row points at the genre via parent_genre_id"],
        "rationale": (
            "A genre has no sub-genres when no other row's parent_genre_id references its "
            "genre_id — an anti-join (NOT EXISTS) over the self-referencing column. This is the "
            "negated parent-side question."
        ),
    },
    {
        "id": "T04-06",
        "ec": "EC-04",
        "nl": "Which users have referred someone?",
        "paraphrases": [
            "Show the users who brought in at least one other user.",
            "List everyone who acted as a referrer.",
            "Who has referred other users to the platform?",
        ],
        "sql": (
            "SELECT DISTINCT r.display_name AS referrer\nFROM users u\n"
            "JOIN users r ON u.referred_by_user_id = r.user_id\nORDER BY r.display_name;"
        ),
        "restatement": "The user wants the users who referred at least one other user.",
        "filters": ["user appears as someone's referrer"],
        "rationale": (
            "Referrals self-reference through users.referred_by_user_id; the referrers are the "
            "rows other users point AT. Selecting the pointing side instead would return the "
            "referred users — the direction of the self-join decides the answer."
        ),
    },
    {
        "id": "T04-07",
        "ec": "EC-04",
        "nl": "Which users were referred by somebody?",
        "paraphrases": [
            "Show the users who joined through another user's referral.",
            "List every user that has a referrer.",
        ],
        "sql": (
            "SELECT display_name, country, joined_at\nFROM users\n"
            "WHERE referred_by_user_id IS NOT NULL\nORDER BY joined_at;"
        ),
        "restatement": "The user wants the users who were referred by another user.",
        "filters": ["users.referred_by_user_id IS NOT NULL"],
        "rationale": (
            "Referred users are the rows whose referred_by_user_id is set — the pointing side of "
            "the self-reference. The IS NOT NULL check suffices; no join is needed unless the "
            "referrer's name is also requested."
        ),
    },
    {
        "id": "T04-08",
        "ec": "EC-04",
        "nl": "How many users did each referrer bring in?",
        "paraphrases": [
            "Count the referrals made by every referring user.",
            "Per referrer, how many users did they refer?",
        ],
        "sql": (
            "SELECT r.display_name AS referrer, COUNT(*) AS referred_count\nFROM users u\n"
            "JOIN users r ON u.referred_by_user_id = r.user_id\n"
            "GROUP BY r.user_id, r.display_name\nORDER BY referred_count DESC;"
        ),
        "restatement": "The user wants, per referrer, how many users they referred.",
        "filters": [],
        "rationale": (
            "Counting referrals per referrer groups the users self-join by the REFERRER side "
            "(the row being pointed at). Each referred row contributes to the user its "
            "referred_by_user_id references."
        ),
    },
    {
        "id": "T04-09",
        "ec": "EC-04",
        "nl": "Which playlists are forks of another playlist?",
        "paraphrases": [
            "Show the playlists that were forked from an existing playlist, "
            "with the original's name.",
            "List every forked playlist and its source playlist.",
        ],
        "sql": (
            "SELECT fp.name AS forked_playlist, op.name AS original_playlist\nFROM playlists fp\n"
            "JOIN playlists op ON fp.forked_from_id = op.playlist_id\nORDER BY fp.name;"
        ),
        "restatement": "The user wants the forked playlists together with their source playlists.",
        "filters": ["playlists.forked_from_id IS NOT NULL (implicit via the inner self-join)"],
        "rationale": (
            "Forks self-reference through playlists.forked_from_id; joining the table to itself "
            "pairs each fork with the original playlist it points at. Top-level playlists have "
            "forked_from_id NULL and drop out of the inner join."
        ),
    },
    {
        "id": "T04-10",
        "ec": "EC-04",
        "nl": "Which playlists have been forked by someone?",
        "paraphrases": [
            "Show the playlists that other playlists were forked from.",
            "List the original playlists that have at least one fork.",
        ],
        "sql": (
            "SELECT DISTINCT op.name AS original_playlist\nFROM playlists fp\n"
            "JOIN playlists op ON fp.forked_from_id = op.playlist_id\nORDER BY op.name;"
        ),
        "restatement": "The user wants the playlists that have at least one fork.",
        "filters": ["playlist appears as another playlist's fork source"],
        "rationale": (
            "This is the PARENT side of the fork self-reference: an original playlist qualifies "
            "when some other row's forked_from_id points at its playlist_id. Selecting the fork "
            "side would return the copies instead of the sources."
        ),
    },
]


# ---------------------------------------------------------------------------
# PROBE_EVAL — gold SQL for the 8 gate_d1.py probe wordings. EVAL ONLY.
# ---------------------------------------------------------------------------

PROBE_EVAL: list[dict] = [
    {
        "id": "P-EC01",
        "ec": "EC-01",
        "nl": "Show me all artists from Colombia.",
        "sql": (
            "SELECT artist_id, name, country, monthly_listeners_cached\nFROM artists\n"
            "WHERE country = 'CO';"
        ),
        "restatement": "The user wants the list of artists whose country is Colombia.",
        "filters": ["artists.country = 'CO' (Colombia)"],
        "rationale": GOLD_META["Q01"]["rationale"],
    },
    {
        "id": "P-EC02",
        "ec": "EC-02",
        "nl": "Which subscription plans include high-fidelity audio?",
        "sql": (
            "SELECT name, monthly_price, plan_type, max_devices\nFROM subscription_plans\n"
            "WHERE has_hifi = 1;"
        ),
        "restatement": "The user wants the subscription plans that include high-fidelity audio.",
        "filters": ["subscription_plans.has_hifi = 1"],
        "rationale": GOLD_META["Q02"]["rationale"],
    },
    {
        "id": "P-EC03",
        "ec": "EC-03",
        "nl": "How many tracks are standalone singles (not part of any album)?",
        "sql": "SELECT COUNT(*) AS total_singles\nFROM tracks\nWHERE album_id IS NULL;",
        "restatement": "The user wants a count of tracks not linked to any album.",
        "filters": ["tracks.album_id IS NULL"],
        "rationale": GOLD_META["Q03"]["rationale"],
    },
    {
        "id": "P-EC04",
        "ec": "EC-04",
        "nl": "Which genres have subgenres?",
        "sql": (
            "SELECT DISTINCT parent.name AS parent_genre\nFROM genres child\n"
            "JOIN genres parent ON child.parent_genre_id = parent.genre_id\nORDER BY parent.name;"
        ),
        "restatement": "The user wants the genres that have at least one sub-genre.",
        "filters": ["genre appears as another genre's parent"],
        "rationale": (
            "The question asks for the PARENT side of the genres.parent_genre_id self-reference: "
            "a genre has sub-genres when some child row's parent_genre_id points at its genre_id. "
            "Selecting the child side, or adding a spurious parent_genre_id IS NOT NULL on the "
            "parent, returns the wrong set."
        ),
    },
    {
        "id": "P-EC05",
        "ec": "EC-05",
        "nl": "What is the average track duration in minutes?",
        "sql": ("SELECT ROUND(AVG(trk_dur_ms) / 60000.0, 2) AS avg_duration_minutes\nFROM tracks;"),
        "restatement": "The user wants the average track duration expressed in minutes.",
        "filters": [],
        "rationale": (
            "Track duration is stored in the abbreviated column trk_dur_ms, in milliseconds. The "
            "average must be converted to minutes by dividing by 60000."
        ),
    },
    {
        "id": "P-EC06",
        "ec": "EC-06",
        "nl": "What is the current price of the Individual Premium plan?",
        "sql": (
            "SELECT sp.name AS plan_name, ph.monthly_price AS current_price\n"
            "FROM subscription_plans sp\n"
            "JOIN pricing_history ph ON sp.plan_id = ph.plan_id\n"
            "WHERE ph.effective_to IS NULL\n  AND sp.name = 'Individual';"
        ),
        "restatement": "The user wants the current monthly price of the Individual plan.",
        "filters": [
            "pricing_history.effective_to IS NULL",
            "subscription_plans.name = 'Individual'",
        ],
        "rationale": (
            "'Current price' resolves to the pricing_history row whose effective_to is NULL — the "
            "history table is the authoritative source, not the cached column on "
            "subscription_plans. The plan is stored as 'Individual'."
        ),
    },
    {
        "id": "P-EC07",
        "ec": "EC-07",
        "nl": "Which artist had the most plays last month?",
        "sql": (
            "SELECT a.name AS artist_name, COUNT(*) AS plays\nFROM artists a\n"
            "JOIN track_artists ta ON a.artist_id = ta.artist_id\n"
            "JOIN play_events pe ON ta.track_id = pe.track_id\n"
            "WHERE pe.event_type = 'play'\n"
            "  AND pe.played_at >= '2024-12-01' AND pe.played_at < '2025-01-01'\n"
            "GROUP BY a.artist_id, a.name\nORDER BY plays DESC\nLIMIT 1;"
        ),
        "restatement": "The user wants the artist with the most plays during the last month.",
        "filters": ["play_events.event_type = 'play'", "played_at within the last month"],
        "time_range": "last month",
        "note": "Relative date — dataset frozen at 2025-01-20, so 'last month' = December 2024. "
        "Excluded from strict scoring, mirroring tests/evaluate.py.",
        "rationale": (
            "Play counts must come from the raw play_events table, not the pre-aggregated "
            "daily_artist_metrics (which is intentionally ~5% higher). The chain artists → "
            "track_artists → play_events with event_type = 'play' and the last-month window "
            "yields the top artist."
        ),
    },
    {
        "id": "P-EC08",
        "ec": "EC-08",
        "nl": "Which playlists contain tracks by Adele?",
        "sql": (
            "SELECT DISTINCT pl.name AS playlist_name\nFROM playlists pl\n"
            "JOIN playlist_tracks pt ON pl.playlist_id = pt.playlist_id\n"
            "JOIN track_artists ta ON pt.track_id = ta.track_id\n"
            "JOIN artists a ON ta.artist_id = a.artist_id\nWHERE a.name = 'Adele';"
        ),
        "restatement": "The user wants the playlists that contain tracks by the artist Adele.",
        "filters": ["artists.name = 'Adele'"],
        "note": "Adele does not exist in the seed catalog — the correct result is 0 rows "
        "(known probe quirk, see DAY3_PLAN completion note).",
        "min_rows": 0,
        "rationale": (
            "Connecting playlists to an artist requires the junction chain playlists → "
            "playlist_tracks → track_artists → artists, none of which is named in the question. "
            "The filter goes on artists.name; an empty result is the correct answer when the "
            "artist is not in the catalog."
        ),
    },
]


# ---------------------------------------------------------------------------
# QU_EXTRA — query_understanding-only intent cases (no SQL needed)
# ---------------------------------------------------------------------------
# Each entry: {"nl", "intent": {full Intent JSON target}, "split": "train"|"eval"}


def _intent(
    entities: list[str],
    restatement: str,
    metrics: list[str] | None = None,
    filters: list[str] | None = None,
    requested_fields: list[str] | None = None,
    time_range: str | None = None,
    ambiguity_flags: list[str] | None = None,
) -> dict:
    return {
        "entities": entities,
        "metrics": metrics or [],
        "filters": filters or [],
        "requested_fields": requested_fields or [],
        "time_range": time_range,
        "ambiguity_flags": ambiguity_flags or [],
        "plain_restatement": restatement,
    }


QU_EXTRA: list[dict] = [
    # ---- requested_fields trailing clauses (hard requirement policy) ----
    {
        "nl": "What are the top 10 tracks by total plays? give me the names",
        "split": "train",
        "intent": _intent(
            entities=["tracks", "total_plays", "names"],
            metrics=[],
            filters=["top 10 by total_plays"],
            requested_fields=["names"],
            restatement="The user wants the top 10 tracks by total plays, returning their names.",
        ),
    },
    {
        "nl": "Which users are banned? show me their emails",
        "split": "train",
        "intent": _intent(
            entities=["users", "status", "emails"],
            filters=["users.status = 2 (banned)"],
            requested_fields=["emails"],
            restatement="The user wants the banned users, returning their emails.",
        ),
    },
    {
        "nl": "List artists from Colombia - just the names",
        "split": "train",
        "intent": _intent(
            entities=["artists", "country", "names"],
            filters=["artists.country = 'CO' (Colombia)"],
            requested_fields=["names"],
            restatement="The user wants the artists from Colombia, returning only their names.",
        ),
    },
    {
        "nl": "Show the top 5 albums by number of tracks, return the titles",
        "split": "train",
        "intent": _intent(
            entities=["albums", "total_tracks", "titles"],
            filters=["top 5 by number of tracks"],
            requested_fields=["titles"],
            restatement="The user wants the top 5 albums by track count, returning their titles.",
        ),
    },
    {
        "nl": (
            "Which playlists have the most followers? "
            "I want the playlist names and follower counts"
        ),
        "split": "train",
        "intent": _intent(
            entities=["playlists", "follower_count", "playlist names", "follower counts"],
            filters=["ordered by follower_count descending"],
            requested_fields=["playlist names", "follower counts"],
            restatement=(
                "The user wants the playlists with the most followers, returning the playlist "
                "names and follower counts."
            ),
        ),
    },
    {
        "nl": "Who referred the most users? give me the display name",
        "split": "eval",
        "intent": _intent(
            entities=["users", "referred_by_user_id", "display name"],
            metrics=["COUNT"],
            filters=["referrer with the highest referral count"],
            requested_fields=["display name"],
            restatement=(
                "The user wants the user who referred the most other users, returning their "
                "display name."
            ),
        ),
    },
    # ---- ambiguity POSITIVES: genuinely more than one reading ----
    {
        "nl": "Show me the names and countries.",
        "split": "train",
        "intent": _intent(
            entities=["name", "country"],
            restatement="The user wants names and countries, but the target table is unclear.",
            ambiguity_flags=[
                "column 'name' exists in multiple tables (artists, users, genres, "
                "subscription_plans, playlists) — which entity's names?",
                "column 'country' exists in both artists and users",
            ],
        ),
    },
    {
        "nl": "How many streams does Blinding Lights have?",
        "split": "train",
        "intent": _intent(
            entities=["tracks", "play_events", "total_plays"],
            metrics=["COUNT"],
            filters=["tracks.title = 'Blinding Lights'"],
            restatement="The user wants the stream count for the track Blinding Lights.",
            ambiguity_flags=[
                "stream count could come from the raw play_events table or the cached "
                "tracks.total_plays counter — exact/live number or reported number?",
            ],
        ),
    },
    {
        "nl": "What did the Student plan cost?",
        "split": "train",
        "intent": _intent(
            entities=["subscription_plans", "pricing_history", "monthly_price"],
            filters=["subscription_plans.name = 'Student'"],
            restatement="The user wants the price of the Student plan.",
            ambiguity_flags=[
                "'did cost' is ambiguous between the current price and the historical prices "
                "tracked in pricing_history — right now or over time?",
            ],
        ),
    },
    {
        "nl": "Show me the release dates.",
        "split": "train",
        "intent": _intent(
            entities=["release_date"],
            restatement="The user wants release dates, but the target table is unclear.",
            ambiguity_flags=[
                "column 'release_date' exists in both albums and tracks — album releases or "
                "track releases?",
            ],
        ),
    },
    {
        "nl": "How many listeners does Karol G have?",
        "split": "eval",
        "intent": _intent(
            entities=["artists", "play_events", "monthly_listeners_cached"],
            metrics=["COUNT DISTINCT"],
            filters=["artists.name = 'Karol G'"],
            restatement="The user wants Karol G's listener count.",
            ambiguity_flags=[
                "listener count could be the cached monthly_listeners_cached figure or a "
                "distinct-user count over raw play_events — reported or exact?",
            ],
        ),
    },
    # ---- ambiguity NEGATIVES: mapping is obvious, must NOT flag ----
    {
        "nl": "What is the current price of each plan?",
        "split": "train",
        "intent": _intent(
            entities=["subscription_plans", "pricing_history", "monthly_price"],
            filters=["pricing_history.effective_to IS NULL (current price)"],
            restatement="The user wants the current monthly price of each subscription plan.",
        ),
    },
    {
        "nl": "Which artists are from Colombia?",
        "split": "train",
        "intent": _intent(
            entities=["artists", "country"],
            filters=["artists.country = 'CO' (Colombia)"],
            restatement="The user wants the artists whose country is Colombia.",
        ),
    },
    {
        "nl": "How many users are banned?",
        "split": "train",
        "intent": _intent(
            entities=["users", "status"],
            metrics=["COUNT"],
            filters=["users.status = 2 (banned)"],
            restatement="The user wants a count of banned user accounts.",
        ),
    },
    {
        "nl": "List the albums released in 2022.",
        "split": "train",
        "intent": _intent(
            entities=["albums", "release_date"],
            filters=["year of albums.release_date = 2022"],
            time_range="2022",
            restatement="The user wants the albums released during 2022.",
        ),
    },
    {
        "nl": "Which tracks are explicit?",
        "split": "eval",
        "intent": _intent(
            entities=["tracks", "is_exp"],
            filters=["tracks.is_exp = 1"],
            restatement="The user wants the tracks flagged as explicit content.",
        ),
    },
]
