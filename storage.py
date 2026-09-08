"""Durable store for scans, so past data can be re-read without the API.

Two files, both append-only and both plain text so they stay greppable and
load straight into pandas:

  data/scans.jsonl  one JSON object per scan: the metadata and every match
                    with its best prices and overround.

  data/prices.csv   one row per price observed: the long/tidy format, so a
                    price can be followed across scans and bookmakers. This
                    is what the churn analysis reads, because it carries the
                    bookmaker's own changedAt timestamp for each price.

Neither file is ever rewritten, so a scan is recorded once and stays put.
"""

import csv
import json
import os
from datetime import datetime, timezone

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
SCANS_PATH = os.path.join(DATA_DIR, "scans.jsonl")
PRICES_PATH = os.path.join(DATA_DIR, "prices.csv")

PRICE_FIELDS = [
    "scannedAt",     # ISO8601 UTC, the scan this observation belongs to
    "fixtureId",
    "home",
    "away",
    "startTime",     # kick-off, ISO8601
    "tournamentId",
    "bookmaker",
    "outcome",       # home | draw | away
    "price",         # decimal odds
    "changedAt",     # when the bookmaker last moved this price
    "active",
]

OUTCOME_NAMES = {"101": "home", "102": "draw", "103": "away"}


def _iso(ts=None):
    dt = datetime.fromtimestamp(ts, timezone.utc) if ts else datetime.now(timezone.utc)
    return dt.replace(microsecond=0).isoformat().replace("+00:00", "Z")


def record_scan(payload, observations):
    """Append one scan's summary and its individual price observations."""
    os.makedirs(DATA_DIR, exist_ok=True)
    stamp = _iso(payload.get("scannedAt"))

    summary = {
        "scannedAt": stamp,
        "requests": payload.get("requests"),
        "elapsed": payload.get("elapsed"),
        "bookmakers": payload.get("bookmakers"),
        "tournaments": payload.get("tournaments"),
        "matches": payload.get("matches"),
    }
    with open(SCANS_PATH, "a", encoding="utf-8", newline="") as handle:
        handle.write(json.dumps(summary) + "\n")

    write_header = not os.path.exists(PRICES_PATH)
    with open(PRICES_PATH, "a", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=PRICE_FIELDS)
        if write_header:
            writer.writeheader()
        for row in observations:
            row = dict(row)
            row["scannedAt"] = stamp
            writer.writerow({k: row.get(k) for k in PRICE_FIELDS})

    return stamp


def load_scans(limit=None):
    """Scan summaries, oldest first."""
    if not os.path.exists(SCANS_PATH):
        return []
    scans = []
    with open(SCANS_PATH, encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                scans.append(json.loads(line))
            except ValueError:
                continue
    return scans[-limit:] if limit else scans


def load_prices():
    if not os.path.exists(PRICES_PATH):
        return []
    with open(PRICES_PATH, encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _parse(ts):
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except ValueError:
        return None


# Buckets are by time to kick-off, because that is what price movement
# actually tracks: a fixture a week out barely moves, one tonight moves
# every few minutes.
KICKOFF_BUCKETS = [
    ("< 3h", 0, 3),
    ("3h - 24h", 3, 24),
    ("1 - 3 days", 24, 72),
    ("> 3 days", 72, 1e9),
]


def _percentile(values, p):
    if not values:
        return None
    values = sorted(values)
    return values[min(len(values) - 1, int(len(values) * p))]


def price_ages():
    """Age of each observed price in minutes, with its time to kick-off.

    Age is measured from the scan that saw the price, not from now, so old
    rows stay meaningful.

    These ages are length-biased: a scan is likelier to land inside a long
    quiet spell than a short one, so they overstate the typical gap between
    moves. They are an upper bound, not an estimate.
    """
    rows = []
    for row in load_prices():
        seen = _parse(row.get("scannedAt"))
        changed = _parse(row.get("changedAt"))
        kickoff = _parse(row.get("startTime"))
        if not seen or not changed:
            continue
        age = (seen - changed).total_seconds() / 60.0
        if age < 0:
            continue
        rows.append({
            "age": age,
            "book": row.get("bookmaker"),
            "hoursToKickoff": (kickoff - seen).total_seconds() / 3600.0 if kickoff else None,
        })
    return rows


def churn_summary():
    """Price-age statistics by kick-off window and by bookmaker."""
    rows = price_ages()
    if not rows:
        return {"total": 0, "buckets": [], "books": [], "ages": []}

    buckets = []
    for name, lo, hi in KICKOFF_BUCKETS:
        ages = [r["age"] for r in rows
                if r["hoursToKickoff"] is not None and lo <= r["hoursToKickoff"] < hi]
        if not ages:
            continue
        buckets.append({
            "window": name,
            "count": len(ages),
            "p10": round(_percentile(ages, 0.10), 1),
            "p25": round(_percentile(ages, 0.25), 1),
            "median": round(_percentile(ages, 0.50), 1),
            "p75": round(_percentile(ages, 0.75), 1),
        })

    books = {}
    for r in rows:
        books.setdefault(r["book"], []).append(r["age"])
    book_rows = [{
        "book": name,
        "count": len(ages),
        "median": round(_percentile(ages, 0.50), 1),
        "p25": round(_percentile(ages, 0.25), 1),
        "p75": round(_percentile(ages, 0.75), 1),
        "freshShare": round(100.0 * sum(1 for a in ages if a < 5) / len(ages), 1),
    } for name, ages in books.items()]
    book_rows.sort(key=lambda r: r["median"])

    return {
        "total": len(rows),
        "buckets": buckets,
        "books": book_rows,
        # Log-spaced histogram: ages span seconds to days.
        "ages": [round(r["age"], 2) for r in rows],
    }


def overround_history():
    """Best and median overround per scan, for the trend chart."""
    out = []
    for scan in load_scans():
        values = sorted(m["overround"] for m in scan.get("matches", []))
        if not values:
            continue
        out.append({
            "scannedAt": scan["scannedAt"],
            "matches": len(values),
            "best": values[0],
            "median": _percentile(values, 0.5),
            "arbs": sum(1 for v in values if v < 1),
            "within1pct": sum(1 for v in values if v < 1.01),
        })
    return out


def fixture_tracks(limit=12):
    """Overround per fixture across scans, for the fixtures seen most often.

    With a single scan on file this is necessarily flat; it becomes the
    useful view once scans accumulate.
    """
    series = {}
    for scan in load_scans():
        for m in scan.get("matches", []):
            key = m.get("fixtureId") or (m["home"] + "|" + m["away"])
            series.setdefault(key, {
                "label": m["home"] + " v " + m["away"],
                "points": [],
            })["points"].append({
                "scannedAt": scan["scannedAt"],
                "overround": m["overround"],
            })

    tracks = [t for t in series.values() if len(t["points"]) > 1]
    tracks.sort(key=lambda t: (-len(t["points"]), min(p["overround"] for p in t["points"])))
    return tracks[:limit]


def stats():
    scans = load_scans()
    prices = os.path.getsize(PRICES_PATH) if os.path.exists(PRICES_PATH) else 0
    return {
        "scans": len(scans),
        "first": scans[0]["scannedAt"] if scans else None,
        "last": scans[-1]["scannedAt"] if scans else None,
        "priceRows": sum(1 for _ in load_prices()),
        "bytes": prices,
    }
