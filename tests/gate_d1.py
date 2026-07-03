"""
Gate D1 verification script.
Sends 8 probe queries (one per EC-01…EC-08) to POST /query
and checks that >= 6/8 pass verification and return rows.

Run:
    python tests/gate_d1.py
"""

import json
import sys

import requests

BASE_URL = "http://localhost:5000"

PROBES = [
    {
        "ec": "EC-01",
        "query": "Show me all artists from Colombia.",
        "expected_table": "artists",
        "must_not_contain": "users",
    },
    {
        "ec": "EC-02",
        "query": "Which subscription plans include high-fidelity audio?",
        "expected_keyword": "has_hifi",
    },
    {
        "ec": "EC-03",
        "query": "How many tracks are standalone singles (not part of any album)?",
        "expected_keyword": "IS NULL",
    },
    {
        "ec": "EC-04",
        "query": "Which genres have subgenres?",
        "expected_table": "genres",
    },
    {
        "ec": "EC-05",
        "query": "What is the average track duration in minutes?",
        "expected_keyword": "trk_dur_ms",
    },
    {
        "ec": "EC-06",
        "query": "What is the current price of the Individual Premium plan?",
        "expected_table": "pricing_history",
    },
    {
        "ec": "EC-07",
        "query": "Which artist had the most plays last month?",
        "note": "Should use play_events, not cached daily_artist_metrics",
    },
    {
        "ec": "EC-08",
        "query": "Which playlists contain tracks by Adele?",
        "expected_table": "playlist_tracks",
    },
]


def run_query(query: str) -> tuple[dict, list]:
    resp = requests.post(
        f"{BASE_URL}/query",
        json={"message": query},
        stream=True,
        timeout=120,
    )
    result = {}
    events = []
    for line in resp.iter_lines():
        if line:
            data = json.loads(line)
            if data.get("type") == "result":
                result = data
            else:
                events.append(data)
    return result, events


def main():
    passed = 0
    failed = 0

    print(f"\nGate D1 — Running {len(PROBES)} edge-case probes\n{'='*60}")

    for probe in PROBES:
        ec = probe["ec"]
        query = probe["query"]
        print(f"\n[{ec}] {query}")

        try:
            result, events = run_query(query)
        except Exception as e:
            print(f"  ERROR: {e}")
            failed += 1
            continue

        # Check verification passed
        verify = result.get("verify") or {}
        if not verify.get("overall_passed", False):
            print("  FAIL — verification did not pass")
            print(f"         syntax:   {verify.get('syntax', {}).get('message')}")
            print(f"         semantic: {verify.get('semantic', {}).get('message')}")
            print(f"         sanity:   {verify.get('sanity', {}).get('message')}")
            failed += 1
            continue

        # Check rows returned
        row_count = result.get("row_count", 0)
        if row_count == 0:
            print("  FAIL — 0 rows returned")
            failed += 1
            continue

        # Check SQL content hints
        sql = (result.get("sql") or {}).get("sql", "").upper()
        if probe.get("expected_keyword"):
            kw = probe["expected_keyword"].upper()
            if kw not in sql:
                print(f"  WARN — expected '{probe['expected_keyword']}' not in SQL")
        if probe.get("expected_table"):
            tbl = probe["expected_table"].upper()
            if tbl not in sql:
                print(f"  WARN — expected table '{probe['expected_table']}' not in SQL")

        # Check the adapter events fired (Gate D1 criterion 4)
        adapters = {
            (e.get("payload") or {}).get("adapter")
            for e in events
            if (e.get("payload") or {}).get("adapter")
        }
        if adapters:
            print(f"  adapters seen: {sorted(adapters)}")

        print(f"  PASS — {row_count} row(s) | verification passed")
        passed += 1

    print(f"\n{'='*60}")
    print(f"Result: {passed}/{len(PROBES)} passed  (need >= 6)")
    if passed >= 6:
        print("GATE D1: PASSED")
        sys.exit(0)
    else:
        print("GATE D1: FAILED")
        sys.exit(1)


if __name__ == "__main__":
    main()
