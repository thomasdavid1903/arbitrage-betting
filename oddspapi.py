"""Odds from the OddsPapi REST API.

Replaces the easyodds.com scraper in utils.py, whose competition pages now
redirect to the site homepage and serve no match data.

Unlike the scraper, this keeps track of *which* bookmaker offered each price.
An arbitrage needs three bets placed at three specific books, so the best
price alone is not actionable.

Set the API key in the ODDSPAPI_KEY environment variable, or pass api_key=.
"""

import json
import os
import time
from collections import namedtuple

import requests

BASE_URL = "https://api.oddspapi.io"

SPORT_FOOTBALL = 10

# Market 101 is match odds (1X2); its outcomes are home, draw and away.
MARKET_1X2 = "101"
OUTCOME_HOME = "101"
OUTCOME_DRAW = "102"
OUTCOME_AWAY = "103"

# The odds endpoint rate limits at well under a second between calls.
MIN_REQUEST_INTERVAL = 1.0

# The odds endpoint rejects more than five tournament ids in one call.
MAX_TOURNAMENTS_PER_REQUEST = 5

# Positional fields 0-4 match the scraper's row shape, so core.py and the
# existing unpacking keep working; the rest is extra context.
Match = namedtuple(
    "Match",
    "home away bet1 bet2 bet3 books fixture_id start_time",
)

_last_request_at = [0.0]

# Requests made this process, so the UI can show what a scan actually cost.
request_count = [0]

CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".cache")

# The tournament and participant lists barely change and cost a request each,
# which is a real fraction of a small monthly quota.
CACHE_TTL_SECONDS = 7 * 24 * 3600


def _cached(name, ttl, build):
    """Return a cached JSON payload, rebuilding it when stale or absent."""
    path = os.path.join(CACHE_DIR, name + ".json")
    try:
        if time.time() - os.path.getmtime(path) < ttl:
            with open(path, encoding="utf-8") as handle:
                return json.load(handle)
    except (OSError, ValueError):
        pass

    value = build()
    try:
        os.makedirs(CACHE_DIR, exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(value, handle)
    except OSError:
        pass
    return value


class OddsPapiError(RuntimeError):
    pass


def _get(path, api_key=None, retries=3, **params):
    api_key = api_key or os.environ.get("ODDSPAPI_KEY")
    if not api_key:
        raise OddsPapiError("no API key: set ODDSPAPI_KEY or pass api_key=")

    params["apiKey"] = api_key

    for attempt in range(retries):
        # Self-throttle rather than relying on being told off.
        wait = MIN_REQUEST_INTERVAL - (time.monotonic() - _last_request_at[0])
        if wait > 0:
            time.sleep(wait)

        response = requests.get(BASE_URL + path, params=params, timeout=60)
        _last_request_at[0] = time.monotonic()
        request_count[0] += 1

        if response.status_code == 429:
            body = response.json().get("error", {})
            time.sleep(body.get("retryMs", 1000) / 1000 + 0.1)
            continue

        if response.status_code != 200:
            raise OddsPapiError(
                "%s returned %s: %s" % (path, response.status_code, response.text[:200])
            )
        return response.json()

    raise OddsPapiError("%s still rate limited after %d attempts" % (path, retries))


def get_tournaments(sport_id=SPORT_FOOTBALL, api_key=None, use_cache=True):
    """All tournaments for a sport, as returned by the API."""
    build = lambda: _get("/v4/tournaments", api_key=api_key, sportId=sport_id)
    if not use_cache:
        return build()
    return _cached("tournaments-%s" % sport_id, CACHE_TTL_SECONDS, build)


def get_participants(sport_id=SPORT_FOOTBALL, api_key=None, use_cache=True):
    """Map of participant id (as a string) to team name."""
    build = lambda: _get("/v4/participants", api_key=api_key, sportId=sport_id)
    if not use_cache:
        return build()
    return _cached("participants-%s" % sport_id, CACHE_TTL_SECONDS, build)


def get_markets(sport_id=SPORT_FOOTBALL, api_key=None, use_cache=True):
    """Market definitions: id, name, type, period, handicap and outcome names.

    marketLength is the number of outcomes the market has, which is what makes
    it safe to price a market at all: an arbitrage can only be judged when
    every outcome is covered.
    """
    build = lambda: _get("/v4/markets", api_key=api_key, sportId=sport_id)
    if not use_cache:
        return build()
    return _cached("markets-%s" % sport_id, CACHE_TTL_SECONDS, build)


def get_bookmakers(api_key=None, use_cache=True):
    """Every bookmaker the API knows, with its cloneOf relationship."""
    build = lambda: _get("/v4/bookmakers", api_key=api_key)
    if not use_cache:
        return build()
    return _cached("bookmakers", CACHE_TTL_SECONDS, build)


# The API's cloneOf covers technical clones -- one sportsbook behind several
# brands -- but not corporate ownership. These brands are separate sites with
# separate accounts, yet they share pricing and a risk team, so an
# "arbitrage" between two of them is not one worth trusting.
CORPORATE_GROUPS = {
    "paddypower": "flutter",
    "betfair-ex": "flutter",
    "skybet": "flutter",
    "ladbrokes": "entain",
    "coral": "entain",
    "bwin": "entain",
    "williamhill": "evoke",
    "888sport": "evoke",
}


def clone_groups(bookmakers):
    """Map each bookmaker slug to the operator it really is.

    A clone is the same sportsbook behind a different brand: the prices are
    the same book, so two legs across a clone pair are one bet placed twice,
    not an arbitrage, and a risk team will treat them as such. Corporate
    stablemates are folded in for the same reason.
    """
    groups = {}
    for book in bookmakers:
        slug = book.get("slug")
        if not slug:
            continue
        groups[slug] = CORPORATE_GROUPS.get(slug) or book.get("cloneOf") or slug
    return groups


def market_index(markets):
    """Market definitions keyed by id as a string."""
    return {str(m["marketId"]): m for m in markets}


def collect_all_markets(fixture, into=None):
    """Every market a fixture offers, kept per bookmaker.

    Same idea as collect_prices, but for all ~80 markets a fixture carries
    rather than only 1X2. The response already contains them, so this costs
    no extra requests.

    Prices are stored per bookmaker rather than immediately reduced to the
    best, because judging whether a market is trustworthy needs each book's
    own complete quote -- see markets.evaluate_fixture.

    Shape: {marketId: {bookmaker: {outcomeId: {price, limit, label,
                                               sourceMarket, mainLine}}}}
    """
    if into is None:
        into = {}

    for book_name, book in (fixture.get("bookmakerOdds") or {}).items():
        if not book.get("bookmakerIsActive", True):
            continue

        # Some books give a per-selection betslip link, others only a link to
        # the fixture. Either is enough to go and check the price by hand.
        fixture_path = book.get("fixturePath")

        for market_id, market in (book.get("markets") or {}).items():
            if market.get("marketActive") is False:
                continue
            slot = into.setdefault(market_id, {}).setdefault(book_name, {})

            for outcome_id, outcome in (market.get("outcomes") or {}).items():
                player = (outcome.get("players") or {}).get("0") or {}
                price = player.get("price")
                if price is None or not player.get("active", True):
                    continue

                # The betslip link names the bookmaker's own market for this
                # selection. When outcomes of one normalised market point at
                # different bookmaker markets, they are not the same bet and
                # must not be combined.
                source = player.get("betslip") or market.get("bookmakerMarketId")

                slot[outcome_id] = {
                    "price": float(price),
                    "limit": player.get("limit"),
                    "label": player.get("bookmakerOutcomeId"),
                    "changedAt": player.get("changedAt"),
                    "mainLine": player.get("mainLine"),
                    "sourceMarket": _source_market(source),
                    "link": _safe_link(player.get("betslip")) or _safe_link(fixture_path),
                    "deepLink": bool(_safe_link(player.get("betslip"))),
                }
    return into


def _safe_link(url):
    """Only pass through ordinary web links.

    These URLs come from the feed, so anything that is not plain http(s) is
    dropped rather than handed to a browser.
    """
    if not url:
        return None
    text = str(url).strip()
    return text if text.startswith(("https://", "http://")) else None


def _source_market(source):
    """The bookmaker's own market identifier, pulled out of a betslip URL."""
    if not source:
        return None
    text = str(source)
    if "marketId=" in text:
        return text.split("marketId=")[1].split("&")[0]
    return text


def find_tournament_ids(competitions, sport_id=SPORT_FOOTBALL, api_key=None,
                        tournaments=None):
    """Resolve (category, slug) pairs to the numeric ids the API wants.

    Slugs are not unique: 36 different tournaments are called
    'premier-league', so the country category is required to pick one out.
    Only tournaments with upcoming fixtures are returned, since there is
    nothing to price otherwise.
    """
    wanted = {(c, s) for c, s in competitions}
    if tournaments is None:
        tournaments = get_tournaments(sport_id, api_key)

    found = {}
    for t in tournaments:
        key = (t.get("categorySlug"), t.get("tournamentSlug"))
        if key in wanted and (t.get("futureFixtures") or t.get("liveFixtures")):
            found[key] = t["tournamentId"]

    missing = wanted - set(found)
    return found, sorted(missing)


def _decimal_to_fractional(price):
    """Decimal odds to the net-profit-per-unit-stake ratio core.py expects.

    Decimal odds include the returned stake, so 3.5 decimal is a 2.5 ratio.
    """
    return float(price) - 1


def _outcome_price(market, outcome_id):
    """Price for one outcome, or None when it is missing or suspended."""
    outcome = market.get("outcomes", {}).get(outcome_id)
    if not outcome:
        return None

    # Outcomes nest a "players" map; for 1X2 the only entry is "0".
    player = outcome.get("players", {}).get("0")
    if not player or not player.get("active", True):
        return None

    price = player.get("price")
    return None if price is None else float(price)


def collect_prices(fixture, into=None, sink=None):
    """Best 1X2 decimal price per outcome across the fixture's bookmakers.

    Pass the previous result as `into` to merge one bookmaker's response into
    the running best, which is how prices from separate requests are combined.
    Returns {"prices": [h, d, a], "books": [h, d, a]} with None for outcomes
    nothing has priced yet.

    Pass a list as `sink` to also collect every individual price seen, with
    the bookmaker's own changedAt timestamp -- that is what makes it possible
    to measure how fast prices move without polling repeatedly.
    """
    if into is None:
        into = {"prices": [None, None, None], "books": [None, None, None]}

    for book_name, book in (fixture.get("bookmakerOdds") or {}).items():
        if not book.get("bookmakerIsActive", True):
            continue

        market = (book.get("markets") or {}).get(MARKET_1X2)
        if not market:
            continue

        for i, outcome_id in enumerate((OUTCOME_HOME, OUTCOME_DRAW, OUTCOME_AWAY)):
            price = _outcome_price(market, outcome_id)

            if sink is not None:
                player = (market.get("outcomes", {}).get(outcome_id, {})
                          .get("players", {}).get("0")) or {}
                if player.get("price") is not None:
                    sink.append({
                        "fixtureId": fixture.get("fixtureId"),
                        "startTime": fixture.get("startTime"),
                        "tournamentId": fixture.get("tournamentId"),
                        "bookmaker": book_name,
                        "outcome": ("home", "draw", "away")[i],
                        "price": player.get("price"),
                        "changedAt": player.get("changedAt"),
                        "active": player.get("active", True),
                    })

            if price is not None and (into["prices"][i] is None or price > into["prices"][i]):
                into["prices"][i] = price
                into["books"][i] = book_name

    return into


def get_bets(tournament_ids, bookmakers, api_key=None, verbose=False, names=None,
             sink=None, market_sink=None):
    """Match rows for the given tournaments, shaped like the scraper's output.

    The API accepts exactly one bookmaker per request, so this makes one call
    per book and merges the best price for each outcome across them. Taking
    the best price across several books is what creates arbitrage in the first
    place, so this costs one request per bookmaker per scan.

    Tournaments are also capped at five per call, so the real cost is
    len(bookmakers) * ceil(len(tournament_ids) / 5) requests. Budget for it.
    """
    if isinstance(tournament_ids, (int, str)):
        tournament_ids = [tournament_ids]
    if isinstance(bookmakers, str):
        bookmakers = [bookmakers]

    chunks = [
        tournament_ids[i:i + MAX_TOURNAMENTS_PER_REQUEST]
        for i in range(0, len(tournament_ids), MAX_TOURNAMENTS_PER_REQUEST)
    ]
    merged = {}
    meta = {}

    for book in bookmakers:
        fixtures = []
        for chunk in chunks:
            try:
                fixtures += _get(
                    "/v4/odds-by-tournaments", api_key=api_key, bookmaker=book,
                    tournamentIds=",".join(str(t) for t in chunk),
                    oddsFormat="decimal",
                )
            except OddsPapiError as exc:
                # One failed chunk should not lose the rest of the prices.
                print("  %s: %s" % (book, exc))

        priced = 0
        for fixture in fixtures:
            if not fixture.get("hasOdds"):
                continue
            key = fixture["fixtureId"]
            merged[key] = collect_prices(fixture, merged.get(key), sink=sink)
            if market_sink is not None:
                market_sink[key] = collect_all_markets(fixture, market_sink.get(key))
            meta.setdefault(key, fixture)
            priced += 1

        if verbose:
            print("  %-14s %d fixtures" % (book, priced))

    matches = []
    for key, best in merged.items():
        if any(p is None for p in best["prices"]):
            continue

        fixture = meta[key]
        bet1, bet2, bet3 = [_decimal_to_fractional(p) for p in best["prices"]]
        home, away = _team_names(fixture, names)

        matches.append(Match(
            home, away, bet1, bet2, bet3, best["books"],
            key, fixture.get("startTime"),
        ))

    return matches


def _team_names(fixture, names=None):
    """Team names via the participants map, falling back to the raw ids."""
    names = names or {}
    out = []
    for n in (1, 2):
        pid = fixture.get("participant%dId" % n)
        out.append(names.get(str(pid)) or ("participant %s" % pid))
    return out
