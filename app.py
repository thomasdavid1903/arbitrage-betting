"""Local web UI for the arbitrage scanner.

Run it, open the page, paste an OddsPapi key and scan. The key is held only
for the request and never written to disk; scan results are cached so that
reloading the page does not spend quota.
"""

import json
import os
import time

from flask import Flask, jsonify, render_template, request

import oddspapi
from core import best_stakes, overround, profit_if
from main import BOOKMAKERS, COMPETITIONS, requests_needed

app = Flask(__name__)

SCAN_CACHE = os.path.join(oddspapi.CACHE_DIR, "scan.json")


def scan(api_key, competitions=COMPETITIONS, bookmakers=BOOKMAKERS, precision=1):
    """Fetch odds, evaluate every match and return a JSON-ready payload."""
    started = time.time()
    oddspapi.request_count[0] = 0

    found, missing = oddspapi.find_tournament_ids(competitions, api_key=api_key)
    names = oddspapi.get_participants(api_key=api_key)
    matches = oddspapi.get_bets(
        list(found.values()), bookmakers, api_key=api_key, names=names
    )

    rows = []
    for m in matches:
        margin = overround(m.bet1, m.bet2, m.bet3)
        row = {
            "home": m.home,
            "away": m.away,
            "decimals": [round(m.bet1 + 1, 3), round(m.bet2 + 1, 3), round(m.bet3 + 1, 3)],
            "books": m.books,
            "overround": round(margin, 5),
            "startTime": m.start_time,
            "fixtureId": m.fixture_id,
            "arb": margin < 1,
            "stakes": None,
            "wins": None,
            "ratio": None,
        }

        if row["arb"]:
            result = best_stakes(m.bet1, m.bet2, m.bet3, precision=precision)
            if result:
                stakes, ratio = result
                row["stakes"] = [round(s, 2) for s in stakes]
                row["wins"] = [round(w, 2) for w in profit_if(stakes, m.bet1, m.bet2, m.bet3)]
                row["ratio"] = round(ratio, 5)
        rows.append(row)

    rows.sort(key=lambda r: r["overround"])

    return {
        "scannedAt": started,
        "elapsed": round(time.time() - started, 1),
        "requests": oddspapi.request_count[0],
        "requestsPerScan": requests_needed(found, bookmakers),
        "bookmakers": bookmakers,
        "tournaments": [{"category": c, "slug": s, "id": i}
                        for (c, s), i in found.items()],
        "missing": ["%s/%s" % key for key in missing],
        "matches": rows,
    }


def load_cached_scan():
    try:
        with open(SCAN_CACHE, encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, ValueError):
        return None


def save_scan(payload):
    try:
        os.makedirs(oddspapi.CACHE_DIR, exist_ok=True)
        with open(SCAN_CACHE, "w", encoding="utf-8") as handle:
            json.dump(payload, handle)
    except OSError:
        pass


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/cached")
def api_cached():
    """The last scan, so a page reload costs nothing."""
    payload = load_cached_scan()
    if payload is None:
        return jsonify({"empty": True})
    payload["fromCache"] = True
    return jsonify(payload)


@app.route("/api/scan", methods=["POST"])
def api_scan():
    body = request.get_json(silent=True) or {}
    api_key = (body.get("apiKey") or os.environ.get("ODDSPAPI_KEY") or "").strip()
    if not api_key:
        return jsonify({"error": "no API key supplied"}), 400

    try:
        payload = scan(api_key)
    except oddspapi.OddsPapiError as exc:
        return jsonify({"error": str(exc)}), 502

    save_scan(payload)
    payload["fromCache"] = False
    return jsonify(payload)


if __name__ == "__main__":
    app.run(port=5000, debug=False)
