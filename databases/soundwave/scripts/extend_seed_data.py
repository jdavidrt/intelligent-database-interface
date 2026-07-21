"""
Extend the SoundWave seed data forward from 2025-01-20 to 2026-07-17.

WHY THIS EXISTS
---------------
The evaluation protocol (docs/EVALUATION_PROTOCOL.md) freezes the benchmark clock
at IDI_FREEZE_NOW=2026-07-17T12:00:00. The original seed data ends 2025-01-20, so
every relative-time window ("last month", "this year", "trailing 12 months")
resolved to zero rows — which would have silently voided ~35 of the 75 IDI-EXEC-75
queries and the whole Temporal/Trends category. This script fills the 18-month gap.

DESIGN CONSTRAINTS
------------------
1. Deterministic. Seeded RNG; running it twice produces byte-identical SQL.
2. Appends in place. FileConnector._find_one("*_data.sql") requires EXACTLY ONE
   data file in the folder, so the output is spliced into 02_soundwave_data.sql
   immediately before the trailing `SET FOREIGN_KEY_CHECKS = 1;` rather than
   written to a second file.
3. Preserves the traps. SoundWave exists to break NL2SQL systems; an extension
   that smooths out its edge cases would defeat the point. Specifically preserved:
     EC-02  coded values keep their coded meaning (event_type, status, acq_src)
     EC-03  new nullable FKs (standalone singles, organic signups, playlist-less
            plays) continue to appear
     EC-04  new users extend the self-referential referral chain
     EC-06  the pricing_history SCD gets a real mid-window price change: the old
            open row is CLOSED (effective_to set) and a new open row added, so
            "current price" stops being answerable by a naive MAX() or by
            subscription_plans.monthly_price
     EC-07  daily_artist_metrics keeps its inflated-vs-raw discrepancy, and the
            cached counters (tracks.total_plays, artists.monthly_listeners_cached)
            are bumped so they keep drifting from the raw event log
     EC-17  new payments include failed/refunded rows so status filtering matters
4. Growth is real, not flat. Event volume ramps over the window so that
   "are we growing?" has a defensible answer instead of noise.

DOWNSTREAM EFFECTS (deliberate — see EVALUATION_PROTOCOL.md §0.2 and §11)
-------------------------------------------------------------------------
Adding rows changes ground truth for hand-derived checkers in tests/evaluate.py:
  * _check_ec03 ("5 standalone singles") -> new singles are added, count changes
  * _check_ec06 ("current price 9.99")   -> the mid-window price change moves it
  * _check_ec05 ("avg duration ~3.65min")-> new tracks shift the mean slightly
These are re-derived after running this script. Ground truth for the four
benchmark corpora is computed by EXECUTING reference SQL (protocol §3.1), so the
corpora themselves need no edit.

Run:  python databases/soundwave/scripts/extend_seed_data.py
"""

from __future__ import annotations

import os
import random
from datetime import date, datetime, timedelta

SEED = 20260721
WINDOW_START = date(2025, 1, 21)
WINDOW_END = date(2026, 7, 17)

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(HERE, "..", "02_soundwave_data.sql")
MARKER = "-- ===== EXTENSION 2025-01-21 .. 2026-07-17 (generated) ====="
TERMINATOR = "SET FOREIGN_KEY_CHECKS = 1;"

rng = random.Random(SEED)

# -- existing catalogue (transcribed from 02_soundwave_data.sql) ---------------

# track_id -> primary artist_id
TRACK_ARTIST = {
    1: 1,
    2: 1,
    3: 1,
    4: 1,
    5: 1,
    6: 2,
    7: 2,
    8: 2,
    9: 3,
    10: 3,
    11: 3,
    12: 4,
    13: 4,
    14: 5,
    15: 5,
    16: 6,
    17: 6,
    18: 7,
    19: 7,
    20: 8,
    21: 8,
    22: 10,
    23: 10,
    24: 11,
    25: 12,
    28: 12,
    29: 12,
    26: 4,
    27: 9,
    30: 2,
}

# track_id -> trk_dur_ms for the 30 original tracks
EXISTING_TRACK_DURATION = {
    1: 200040,
    2: 215373,
    3: 237418,
    4: 190426,
    5: 205125,
    6: 200691,
    7: 201945,
    8: 253347,
    9: 248881,
    10: 192574,
    11: 278892,
    12: 224946,
    13: 341306,
    14: 210519,
    15: 154666,
    16: 207688,
    17: 338693,
    18: 203064,
    19: 187000,
    20: 232600,
    21: 220746,
    22: 242014,
    23: 178455,
    24: 232000,
    25: 218026,
    26: 173885,
    27: 233713,
    28: 200924,
    29: 174000,
    30: 178427,
}

# artist_id -> relative popularity weight (drives event sampling)
ARTIST_WEIGHT = {
    1: 12,
    2: 11,
    3: 10,
    4: 9,
    5: 8,
    6: 7,
    7: 9,
    8: 7,
    9: 9,
    10: 7,
    11: 4,
    12: 8,
}

EXISTING_USERS = list(range(1, 21))
# users 7, 8, 12 are lapsed/inactive/suspended -> they generate no new activity
ACTIVE_EXISTING_USERS = [u for u in EXISTING_USERS if u not in (7, 8, 12)]
EXISTING_PLAYLISTS = list(range(1, 19))

COUNTRIES = ["US", "US", "US", "GB", "CO", "MX", "BR", "JP", "KR", "IT", "AU", "CA", "ES"]
DEVICES = ["mobile", "mobile", "mobile", "desktop", "tablet", "smart_tv", "other"]

# subscription_id -> (user_id, plan_id, monthly_fee) for currently-active subs
ACTIVE_SUBS = {
    1: (1, 3, 9.99),
    2: (2, 3, 9.99),
    3: (3, 4, 15.99),
    4: (4, 2, 5.49),
    5: (5, 3, 9.99),
    7: (9, 3, 9.99),
    8: (10, 4, 15.99),
    9: (11, 2, 5.49),
    10: (13, 3, 9.99),
    11: (14, 2, 5.49),
    12: (15, 3, 9.99),
    13: (16, 3, 9.99),
    14: (17, 4, 15.99),
    16: (19, 2, 5.49),
    17: (20, 4, 15.99),
}

# -- new catalogue ------------------------------------------------------------

NEW_ALBUMS = [
    (16, "Midnight Reverie", 1, "2025-03-14", "album", "Republic Records", 4),
    (17, "Neon Season", 7, "2025-07-25", "album", "Warner Records", 4),
    (18, "Cartografía", 12, "2025-11-07", "album", "Universal Music Latino", 4),
    (19, "Static Bloom", 5, "2026-02-20", "album", "Interscope Records", 3),
    (20, "Long Way Home", 9, "2026-05-15", "ep", "Asylum Records", 3),
]

# (track_id, title, album_id, dur_ms, release_date, is_exp, track_number, artist_id)
NEW_TRACKS = [
    (31, "Midnight Reverie", 16, 213400, "2025-03-14", 0, 1, 1),
    (32, "Afterglow Drive", 16, 198750, "2025-03-14", 0, 2, 1),
    (33, "Cold Static", 16, 226100, "2025-03-14", 1, 3, 1),
    (34, "Slow Fade", 16, 241300, "2025-03-14", 0, 4, 1),
    (35, "Neon Season", 17, 187900, "2025-07-25", 0, 1, 7),
    (36, "Glass Hearts", 17, 202450, "2025-07-25", 0, 2, 7),
    (37, "Overdrive", 17, 176300, "2025-07-25", 0, 3, 7),
    (38, "Last Train", 17, 219800, "2025-07-25", 0, 4, 7),
    (39, "Cartografía", 18, 231600, "2025-11-07", 0, 1, 12),
    (40, "Mapa del Cielo", 18, 208400, "2025-11-07", 0, 2, 12),
    (41, "Sin Regreso", 18, 195200, "2025-11-07", 1, 3, 12),
    (42, "Volver", 18, 244700, "2025-11-07", 0, 4, 12),
    (43, "Static Bloom", 19, 189300, "2026-02-20", 0, 1, 5),
    (44, "Paper Thin", 19, 167800, "2026-02-20", 0, 2, 5),
    (45, "Undertow", 19, 233100, "2026-02-20", 1, 3, 5),
    # standalone singles (album_id NULL) [EC-03]
    (46, "Golden Hour", None, 205600, "2025-09-05", 0, None, 9),
    (47, "Ritmo Nuevo", None, 191400, "2026-01-16", 0, None, 3),
    (48, "Echoes", None, 224900, "2026-06-12", 0, None, 2),
]

NEW_USER_NAMES = [
    ("Hannah Brooks", "hannahb", "US"),
    ("Mateo Duarte", "mateod", "CO"),
    ("Sofia Ricci", "sofiar", "IT"),
    ("Liam O'Connor", "liamoc", "IE"),
    ("Amara Okafor", "amarao", "NG"),
    ("Kenji Sato", "kenjis", "JP"),
    ("Chloe Dubois", "chloed", "FR"),
    ("Diego Herrera", "diegoh", "MX"),
    ("Ingrid Larsen", "ingridl", "NO"),
    ("Rahul Mehta", "rahulm", "IN"),
    ("Beatriz Costa", "beatrizc", "BR"),
    ("Jonas Weber", "jonasw", "DE"),
    ("Mia Thompson", "miat", "AU"),
    ("Ali Hassan", "alih", "EG"),
    ("Nora Lindqvist", "noral", "SE"),
    ("Pablo Ramos", "pablor", "ES"),
    ("Grace Kim", "gracek", "KR"),
    ("Tomas Novak", "tomasn", "CZ"),
    ("Valentina Cruz", "valentinac", "AR"),
    ("Owen Baker", "owenb", "GB"),
]


def q(s: str) -> str:
    """SQL string literal with quotes escaped. Not optional: 'Liam O'Connor'
    silently produced an unterminated literal and broke the whole data file."""
    return "'" + s.replace("'", "''") + "'"


def d(x: date) -> str:
    return x.strftime("%Y-%m-%d")


def dt(x: datetime) -> str:
    return x.strftime("%Y-%m-%d %H:%M:%S")


def month_iter(start: date, end: date):
    y, m = start.year, start.month
    while (y, m) <= (end.year, end.month):
        yield y, m
        m += 1
        if m == 13:
            y, m = y + 1, 1


#: nothing may be timestamped after the frozen benchmark clock
FREEZE_INSTANT = datetime(2026, 7, 17, 12, 0, 0)


def rand_dt_in_month(y: int, m: int, floor: date, ceil: date) -> datetime:
    last = (date(y + (m == 12), (m % 12) + 1, 1) - timedelta(days=1)).day
    lo = max(date(y, m, 1), floor)
    hi = min(date(y, m, last), ceil)
    if lo > hi:
        return datetime.combine(lo, datetime.min.time())
    day = rng.randint(lo.day, hi.day) if lo.month == hi.month else rng.randint(1, last)
    when = datetime(y, m, day, rng.randint(6, 23), rng.choice([0, 15, 30, 45]), 0)
    # an event after "now" would make "plays today" include the future
    return min(when, FREEZE_INSTANT)


# -- generators ---------------------------------------------------------------


def gen_users() -> tuple[str, list[int]]:
    """20 new users joining across the window. Some referred by existing users
    (EC-04 referral chain), some organic (referred_by_user_id NULL, EC-03)."""
    rows, ids = [], []
    months = list(month_iter(WINDOW_START, WINDOW_END))
    for i, (name, disp, country) in enumerate(NEW_USER_NAMES):
        uid = 21 + i
        ids.append(uid)
        y, m = months[int(i * len(months) / len(NEW_USER_NAMES))]
        joined = rand_dt_in_month(y, m, WINDOW_START, WINDOW_END)
        # 40% referred -> usr_acq_src=3 and a real referrer [EC-03, EC-04]
        referred = rng.random() < 0.40
        ref = rng.choice(ACTIVE_EXISTING_USERS) if referred else None
        acq = 3 if referred else rng.choice([1, 1, 2, 4])
        status = 1 if rng.random() < 0.90 else rng.choice([0, 2])
        birth = date(rng.randint(1988, 2006), rng.randint(1, 12), rng.randint(1, 28))
        last_login = joined + timedelta(days=rng.randint(1, 400))
        if last_login.date() > WINDOW_END:
            last_login = datetime.combine(WINDOW_END, datetime.min.time()) + timedelta(
                hours=rng.randint(6, 22)
            )
        rows.append(
            f"    ({uid}, {q(name)}, {q(disp)}, {q(disp + '@email.com')}, '{country}', "
            f"'{d(birth)}', {status}, {acq}, "
            f"{ref if ref else 'NULL'}, '{dt(joined)}', '{dt(last_login)}')"
        )
    sql = (
        "INSERT INTO users\n"
        "    (user_id, name, display_name, email, country, birth_date, status, "
        "usr_acq_src,\n     referred_by_user_id, joined_at, last_login)\nVALUES\n"
        + ",\n".join(rows)
        + ";\n"
    )
    return sql, ids


def gen_catalogue() -> str:
    out = []
    rows = [
        f"    ({aid}, {q(title)}, {art}, '{rel}', '{atype}', {q(label)}, {n})"
        for aid, art, title, rel, atype, label, n in [
            (a[0], a[2], a[1], a[3], a[4], a[5], a[6]) for a in NEW_ALBUMS
        ]
    ]
    out.append(
        "INSERT INTO albums\n    (album_id, title, artist_id, release_date, "
        "album_type, label, total_tracks)\nVALUES\n" + ",\n".join(rows) + ";\n"
    )

    trows = []
    for tid, title, alb, dur, rel, exp, num, _artist in NEW_TRACKS:
        trows.append(
            f"    ({tid}, {q(title)}, {alb if alb else 'NULL'}, {dur}, '{rel}', "
            f"{exp}, {num if num else 'NULL'}, 0)"
        )
    out.append(
        "INSERT INTO tracks\n    (track_id, title, album_id, trk_dur_ms, "
        "release_date, is_exp, track_number, total_plays)\nVALUES\n" + ",\n".join(trows) + ";\n"
    )

    ta = [f"    ({tid}, {art}, 1, 'main')" for tid, _, _, _, _, _, _, art in NEW_TRACKS]
    out.append(
        "INSERT INTO track_artists (track_id, artist_id, is_prim, role) VALUES\n"
        + ",\n".join(ta)
        + ";\n"
    )
    return "\n".join(out)


def gen_play_events(new_users: list[int]) -> tuple[str, dict, dict]:
    """Ramped event volume across the window. Returns SQL plus per-artist and
    per-track raw counts, used later to seed the EC-07 discrepancy."""
    all_tracks = list(TRACK_ARTIST.keys()) + [t[0] for t in NEW_TRACKS]
    track_artist = dict(TRACK_ARTIST)
    for tid, _, _, _, _, _, _, art in NEW_TRACKS:
        track_artist[tid] = art

    track_weight = {tid: ARTIST_WEIGHT.get(track_artist[tid], 5) for tid in all_tracks}
    # release date per NEW track — a track cannot be played before it exists
    new_release = {x[0]: datetime.strptime(x[4], "%Y-%m-%d") for x in NEW_TRACKS}
    # real durations, so "average listen time" questions have honest ground truth
    duration = dict(EXISTING_TRACK_DURATION)
    for x in NEW_TRACKS:
        duration[x[0]] = x[3]

    months = list(month_iter(WINDOW_START, WINDOW_END))
    rows = []
    artist_counts: dict[int, int] = {}
    track_counts: dict[int, int] = {}

    for idx, (y, m) in enumerate(months):
        # ramp 34 -> ~78 events/month, with mild seasonal wobble
        base = 34 + int(idx * 2.5)
        volume = base + rng.randint(-4, 6)
        month_users = [u for u in ACTIVE_EXISTING_USERS]
        for u in new_users:
            month_users.append(u)
        for _ in range(volume):
            # tracks released in the future can't be played
            when = rand_dt_in_month(y, m, WINDOW_START, WINDOW_END)
            playable = [t for t in all_tracks if new_release.get(t, when) <= when]
            tid = rng.choices(playable, weights=[track_weight[t] for t in playable])[0]
            uid = rng.choice(month_users)
            # newer releases skew to 'play'; older catalogue gets more skips
            r = rng.random()
            if r < 0.78:
                etype = "play"
            elif r < 0.90:
                etype = "skip"
            elif r < 0.96:
                etype = "save"
            else:
                etype = "share"
            # [EC-03] ~30% of plays happen outside any playlist -> playlist_id NULL
            pl = rng.choice(EXISTING_PLAYLISTS) if rng.random() < 0.70 else None
            dur_total = duration.get(tid, 210000)
            if etype == "skip":
                pos = rng.randint(3000, 30000)
                listened = pos
            else:
                pos = 0
                listened = int(dur_total * rng.uniform(0.55, 1.0))
            country = rng.choice(COUNTRIES)
            rows.append(
                f"    ({uid}, {tid}, {pl if pl else 'NULL'}, '{etype}', "
                f"'{dt(when)}', {pos}, {listened}, '{country}', "
                f"'{rng.choice(DEVICES)}')"
            )
            if etype == "play":
                artist_counts[track_artist[tid]] = artist_counts.get(track_artist[tid], 0) + 1
                track_counts[tid] = track_counts.get(tid, 0) + 1

    sql = (
        "INSERT INTO play_events\n    (user_id, track_id, playlist_id, event_type, "
        "played_at,\n     trk_position_ms, duration_ms, country_code, device_type)\n"
        "VALUES\n" + ",\n".join(rows) + ";\n"
    )
    return sql, artist_counts, track_counts


def gen_pricing_change() -> str:
    """[EC-06] A real mid-window price change. Closes the currently-open rows and
    opens new ones, so 'the current price' requires effective_to IS NULL and can
    no longer be answered from subscription_plans.monthly_price alone."""
    change_date = "2025-09-01"
    prev_day = "2025-08-31"
    new_prices = {2: 6.49, 3: 11.99, 4: 17.99}
    out = [
        f"UPDATE pricing_history SET effective_to = '{prev_day}', "
        f"changed_reason = 'Superseded by 2025 adjustment' "
        f"WHERE effective_to IS NULL AND plan_id IN (2, 3, 4);\n"
    ]
    rows = [
        f"    ({pid}, {price}, '{change_date}', NULL, '2025 price adjustment')"
        for pid, price in sorted(new_prices.items())
    ]
    out.append(
        "INSERT INTO pricing_history\n"
        "    (plan_id, monthly_price, effective_from, effective_to, changed_reason)\n"
        "VALUES\n" + ",\n".join(rows) + ";\n"
    )
    # keep the denormalised catalogue price in step with the new open SCD row
    for pid, price in sorted(new_prices.items()):
        out.append(f"UPDATE subscription_plans SET monthly_price = {price} WHERE plan_id = {pid};")
    return "\n".join(out) + "\n"


def gen_subscriptions(new_users: list[int]) -> tuple[str, dict]:
    """New users subscribe; a few existing ones churn or upgrade mid-window."""
    out = []
    sub_rows, period_rows = [], []
    next_sub = 21
    new_sub_map = {}
    plan_fee = {1: 0.00, 2: 6.49, 3: 11.99, 4: 17.99}

    for uid in new_users:
        plan = rng.choices([1, 2, 3, 4], weights=[2, 3, 5, 2])[0]
        start = WINDOW_START + timedelta(days=rng.randint(5, 520))
        if start > WINDOW_END:
            start = WINDOW_END - timedelta(days=30)
        churned = rng.random() < 0.20
        end = start + timedelta(days=rng.randint(60, 300)) if churned else None
        if end and end > WINDOW_END:
            end = None
            churned = False
        status = 0 if churned else 1
        fee = plan_fee[plan]
        sub_rows.append(
            f"    ({next_sub}, {uid}, {plan}, {status}, '{d(start)}', "
            f"{repr(d(end)) if end else 'NULL'}, {0 if churned else 1})"
        )
        period_rows.append(
            f"    ({uid}, {plan}, '{d(start)}', {repr(d(end)) if end else 'NULL'}, {fee})"
        )
        if not churned:
            new_sub_map[next_sub] = (uid, plan, fee, start)
        next_sub += 1

    # [EC-06] two existing users upgrade mid-window: close the open period, open a new one
    upgrade_date = "2025-10-01"
    out.append(
        "UPDATE subscription_periods SET period_end = '2025-09-30' "
        "WHERE user_id IN (4, 11) AND period_end IS NULL;"
    )
    period_rows.append(f"    (4, 3, '{upgrade_date}', NULL, 11.99)")
    period_rows.append(f"    (11, 3, '{upgrade_date}', NULL, 11.99)")
    out.append("UPDATE subscriptions SET plan_id = 3 WHERE subscription_id IN (4, 9);")

    out.append(
        "INSERT INTO subscriptions\n"
        "    (subscription_id, user_id, plan_id, status, start_date, end_date, auto_renew)\n"
        "VALUES\n" + ",\n".join(sub_rows) + ";\n"
    )
    out.append(
        "INSERT INTO subscription_periods\n"
        "    (user_id, plan_id, period_start, period_end, monthly_fee)\nVALUES\n"
        + ",\n".join(period_rows)
        + ";\n"
    )
    return "\n".join(out) + "\n", new_sub_map


def gen_payments(new_sub_map: dict) -> str:
    """Monthly recurring payments across the window for every paying subscription,
    including a realistic tail of failed and refunded rows [EC-17]."""
    rows = []
    # existing active subscriptions
    for sid, (uid, plan, fee) in sorted(ACTIVE_SUBS.items()):
        if plan == 1:
            continue
        for y, m in month_iter(date(2025, 2, 1), WINDOW_END):
            day = min(15, 28)
            pay_date = date(y, m, day)
            if pay_date > WINDOW_END:
                continue
            amount = fee if pay_date < date(2025, 9, 1) else {2: 6.49, 3: 11.99, 4: 17.99}[plan]
            r = rng.random()
            status = "completed" if r < 0.94 else ("failed" if r < 0.98 else "refunded")
            method = rng.choices(["card", "paypal", "crypto", "voucher"], weights=[7, 2, 1, 1])[0]
            rows.append(
                f"    ({sid}, {uid}, {amount}, '{d(pay_date)}', '{method}', " f"'{status}', 'USD')"
            )
    # new subscriptions
    for sid, (uid, plan, fee, start) in sorted(new_sub_map.items()):
        if plan == 1:
            continue
        for y, m in month_iter(start, WINDOW_END):
            pay_date = date(y, m, min(start.day, 28))
            if pay_date < start or pay_date > WINDOW_END:
                continue
            r = rng.random()
            status = "completed" if r < 0.94 else ("failed" if r < 0.98 else "refunded")
            method = rng.choices(["card", "paypal", "crypto", "voucher"], weights=[7, 2, 1, 1])[0]
            rows.append(
                f"    ({sid}, {uid}, {fee}, '{d(pay_date)}', '{method}', " f"'{status}', 'USD')"
            )
    return (
        "INSERT INTO payments\n    (subscription_id, user_id, amount, payment_date, "
        "payment_method, payment_status, currency)\nVALUES\n" + ",\n".join(rows) + ";\n"
    )


def gen_engagement(new_users: list[int]) -> str:
    """Likes, follows and playlist additions across the window."""
    out = []
    all_tracks = list(TRACK_ARTIST.keys()) + [t[0] for t in NEW_TRACKS]

    # Collision guard: the original data already holds likes over
    # users 1-20 x tracks 1-30. A duplicate (user_id, track_id) violates the
    # composite PK and SQLite aborts the WHOLE statement, silently dropping every
    # generated like. So existing users may only like NEW tracks; new users
    # (21-40) cannot collide with the original data at all.
    new_track_ids = [t[0] for t in NEW_TRACKS]
    likes, seen = [], set()
    for uid in ACTIVE_EXISTING_USERS + new_users:
        pool = all_tracks if uid in new_users else new_track_ids
        for _ in range(rng.randint(1, 6)):
            tid = rng.choice(pool)
            if (uid, tid) in seen:
                continue
            seen.add((uid, tid))
            when = WINDOW_START + timedelta(days=rng.randint(0, 540))
            if when > WINDOW_END:
                continue
            # Hoisted out of the f-string only to fit the line limit. The
            # rng.randint call must stay exactly here in the sequence: the
            # generator's determinism guarantee is a property of RNG call
            # ORDER, so moving or duplicating one rewrites every row after it.
            liked_at = datetime.combine(when, datetime.min.time()) + timedelta(
                hours=rng.randint(7, 22)
            )
            likes.append(f"    ({uid}, {tid}, '{dt(liked_at)}')")
    out.append(
        "INSERT INTO user_liked_tracks (user_id, track_id, liked_at) VALUES\n"
        + ",\n".join(likes)
        + ";\n"
    )

    follows, fseen = [], set()
    for uid in new_users:
        for _ in range(rng.randint(1, 4)):
            aid = rng.choice(list(ARTIST_WEIGHT.keys()))
            if (uid, aid) in fseen:
                continue
            fseen.add((uid, aid))
            when = WINDOW_START + timedelta(days=rng.randint(0, 540))
            if when > WINDOW_END:
                continue
            followed_at = datetime.combine(when, datetime.min.time()) + timedelta(
                hours=rng.randint(7, 22)
            )
            follows.append(f"    ({uid}, {aid}, '{dt(followed_at)}')")
    out.append(
        "INSERT INTO user_follows_artists (user_id, artist_id, followed_at) VALUES\n"
        + ",\n".join(follows)
        + ";\n"
    )

    pt, ptseen = [], set()
    for tid, _, _, _, rel, _, _, _ in NEW_TRACKS:
        rel_d = datetime.strptime(rel, "%Y-%m-%d").date()
        for pid in rng.sample(EXISTING_PLAYLISTS, rng.randint(2, 5)):
            if (pid, tid) in ptseen:
                continue
            ptseen.add((pid, tid))
            when = rel_d + timedelta(days=rng.randint(1, 60))
            if when > WINDOW_END:
                continue
            # Two draws here, and the position one comes FIRST — it was earlier
            # in the original f-string. Swapping them would still lint clean and
            # still look right, and would change every generated row from this
            # point on. See the note on liked_at above.
            position = rng.randint(1, 40)
            added_at = datetime.combine(when, datetime.min.time()) + timedelta(
                hours=rng.randint(8, 20)
            )
            pt.append(f"    ({pid}, {tid}, {position}, '{dt(added_at)}')")
    out.append(
        "INSERT INTO playlist_tracks (playlist_id, track_id, position, added_at) VALUES\n"
        + ",\n".join(pt)
        + ";\n"
    )
    return "\n".join(out)


def gen_daily_metrics(artist_counts: dict) -> str:
    """[EC-07] Pre-aggregated table. Follows the existing file's convention: the
    metrics carry realistic platform-scale numbers while play_events holds a
    sample, so the two sources disagree by construction.

    This function is where the repo-wide "~5% above raw" claim came from, and
    why it was wrong (corrected 2026-07-21). The 1.05 factor below is real, but
    it multiplies `scale` — a platform-scale figure around 380,000 per weight
    unit — not `raw`. So the ETL inflation is 5% *of a number already five
    orders of magnitude larger than the event count*, and `+ raw` at the end
    contributes a rounding error rather than a baseline. Measured against the
    seeded output the two sources differ by 290,000x to 1,070,000x.

    The trap is intentional and stays as it is; only its description was fixed.
    Anyone tempted to "restore" a true 5% relationship should note that doing so
    would rewrite every ground-truth value in the four benchmark corpora, which
    EVALUATION_PROTOCOL.md §0.2 does not permit once a run has been scored."""
    rows = []
    for y, m in month_iter(WINDOW_START, WINDOW_END):
        for aid in sorted(ARTIST_WEIGHT):
            if rng.random() > 0.45:
                continue
            day = rng.randint(1, 27)
            md = date(y, m, day)
            if md < WINDOW_START or md > WINDOW_END:
                continue
            country = rng.choice(["US", "GB", "CO", "MX", "BR", "JP", "KR"])
            raw = artist_counts.get(aid, 1)
            scale = ARTIST_WEIGHT[aid] * 380000
            streams = int(scale * rng.uniform(0.82, 1.18) * 1.05) + raw
            skips = int(streams * rng.uniform(0.02, 0.06))
            saves = int(streams * rng.uniform(0.01, 0.04))
            uniq = int(streams * rng.uniform(0.90, 0.97))
            pct = round(rng.uniform(86.0, 95.5), 2)
            rows.append(
                f"    ({aid}, '{d(md)}', '{country}', {streams}, {skips}, "
                f"{saves}, {uniq}, {pct})"
            )
    return (
        "INSERT INTO daily_artist_metrics\n    (artist_id, metric_date, country_code, "
        "stream_count, skip_count, save_count, unique_listeners, avg_listen_pct)\n"
        "VALUES\n" + ",\n".join(rows) + ";\n"
    )


def gen_cached_counter_drift(track_counts: dict) -> str:
    """[EC-07] Cached counters must keep drifting from the raw event log, so a
    question like 'how many plays does this track have?' still has two defensible
    and mutually inconsistent sources."""
    out = []
    for tid, cnt in sorted(track_counts.items()):
        bump = int(cnt * rng.uniform(1.04, 1.09)) + rng.randint(1000, 90000)
        out.append(f"UPDATE tracks SET total_plays = total_plays + {bump} WHERE track_id = {tid};")
    for aid in sorted(ARTIST_WEIGHT):
        bump = rng.randint(400000, 4200000)
        out.append(
            f"UPDATE artists SET monthly_listeners_cached = "
            f"monthly_listeners_cached + {bump} WHERE artist_id = {aid};"
        )
    return "\n".join(out) + "\n"


def main() -> None:
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        original = f.read()

    if MARKER in original:
        original = original.split(MARKER)[0].rstrip() + "\n\n\n" + TERMINATOR + "\n"
        print("[extend] previous extension found — regenerating from scratch")

    users_sql, new_users = gen_users()
    catalogue_sql = gen_catalogue()
    events_sql, artist_counts, track_counts = gen_play_events(new_users)
    pricing_sql = gen_pricing_change()
    subs_sql, new_sub_map = gen_subscriptions(new_users)
    payments_sql = gen_payments(new_sub_map)
    engagement_sql = gen_engagement(new_users)
    metrics_sql = gen_daily_metrics(artist_counts)
    drift_sql = gen_cached_counter_drift(track_counts)

    block = "\n\n".join(
        [
            MARKER,
            f"-- Generated by scripts/extend_seed_data.py  seed={SEED}\n"
            f"-- Window: {d(WINDOW_START)} .. {d(WINDOW_END)}\n"
            f"-- Regenerate with: python databases/soundwave/scripts/extend_seed_data.py\n"
            f"-- Preserves EC-02/03/04/06/07/17. See the module docstring.",
            "-- 1. new users [EC-03 organic NULL, EC-04 referral chain]",
            users_sql,
            "-- 2. new releases [EC-03 standalone singles keep album_id NULL]",
            catalogue_sql,
            "-- 3. pricing change [EC-06 closes the open SCD row, opens a new one]",
            pricing_sql,
            "-- 4. subscriptions, churn and upgrades [EC-06]",
            subs_sql,
            "-- 5. recurring payments [EC-17 failed/refunded tail]",
            payments_sql,
            "-- 6. play events [EC-02 event_type, EC-03 playlist_id NULL]",
            events_sql,
            "-- 7. engagement",
            engagement_sql,
            "-- 8. pre-aggregated metrics [EC-07 disagrees with raw events]",
            metrics_sql,
            "-- 9. cached counter drift [EC-07]",
            drift_sql,
        ]
    )

    body = original.rstrip()
    assert body.endswith(TERMINATOR), "unexpected tail in 02_soundwave_data.sql"
    body = body[: -len(TERMINATOR)].rstrip()
    updated = f"{body}\n\n\n{block}\n\n{TERMINATOR}\n"

    # newline="\n" is load-bearing on Windows: without it Python translates every
    # "\n" to "\r\n" while the committed file is LF, so the generator stops
    # reproducing its own output byte for byte and
    # tests/test_corpora.py::test_seed_generator_reproduces_the_data_file_byte_for_byte
    # fails on any Windows checkout. Same reason evaluation/corpus.py::write_corpus
    # pins it. Content is unaffected either way — only the line endings.
    with open(DATA_FILE, "w", encoding="utf-8", newline="\n") as f:
        f.write(updated)

    print(f"[extend] seed={SEED}  window {d(WINDOW_START)} .. {d(WINDOW_END)}")
    print(f"[extend] new users        : {len(new_users)}")
    print(f"[extend] new albums/tracks: {len(NEW_ALBUMS)}/{len(NEW_TRACKS)}")
    print(f"[extend] play_events      : {events_sql.count(chr(10)) - 4}")
    print(f"[extend] written to {os.path.normpath(DATA_FILE)}")


if __name__ == "__main__":
    main()
