"""Odds from the OddsPapi REST API.

Replaces the easyodds.com scraper in utils.py, whose competition pages now
redirect to the site's homepage and serve no match data.

Unlike the scraper, this keeps track of *which* bookmaker offered each price.
An arbitrage needs three bets placed at three specific books, so the best
price alone is not actionable.

Set the API key in the ODDSPAPI_KEY environment variable, or pass api_key=.
"""

import os
from collections import namedtuple
from urllib.parse import urlencode

import requests

BASE_URL = "https://api.oddspapi.io"

SPORT_FOOTBALL = 10

# Market 101 is match odds (1X2); its outcomes are home, draw and away.
MARKET_1X2 = "101"
OUTCOME_HOME = "101"
OUTCOME_DRAW = "102"
OUTCOME_AWAY = "103"

# Positional fields 0-4 match the scraper's row shape, so core.py and the
# existing unpacking keep working; the rest is extra context.
Match = namedtuple(
    "Match",
    "home away bet1 bet2 bet3 books fixture_id start_time",
)


class OddsPapiError(RuntimeError):
    pass


def _get(path, api_key=None, **params):
    api_key = api_key or os.environ.get("ODDSPAPI_KEY")
    if not api_key:
        raise OddsPapiError("no API key: set ODDSPAPI_KEY or pass api_key=")

    params["apiKey"] = api_key
    response = requests.get(BASE_URL + path, params=params, timeout=30)
    if response.status_code != 200:
        raise OddsPapiError(
            "%s returned %s: %s" % (path, response.status_code, response.text[:200])
        )
    return response.json()


def get_tournaments(sport_id=SPORT_FOOTBALL, api_key=None):
    """All tournaments for a sport, as returned by the API."""
    return _get("/v4/tournaments", api_key=api_key, sportId=sport_id)


def find_tournament_ids(slugs, sport_id=SPORT_FOOTBALL, api_key=None):
    """Resolve slugs such as 'premier-league' to the numeric ids the API wants."""
    wanted = set(slugs)
    return [
        t["tournamentId"]
        for t in get_tournaments(sport_id, api_key)
        if t.get("tournamentSlug") in wanted
    ]


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


def _team_names(fixture):
    """Best available names, falling back to participant ids.

    The odds response identifies teams numerically; name fields appear only on
    some responses, so try the plausible spellings before giving up.
    """
    names = []
    for n in (1, 2):
        for key in ("participant%dName" % n, "participant%d" % n, "team%d" % n):
            value = fixture.get(key)
            if isinstance(value, str) and value:
                names.append(value)
                break
        else:
            names.append("participant %s" % fixture.get("participant%dId" % n, "?"))
    return names


def best_prices(fixture):
    """Best 1X2 price across bookmakers, with the book offering each.

    Returns (odds, books) where odds are fractional ratios for home, draw and
    away, and books names the bookmaker for each. Returns None when any of the
    three outcomes is unpriced, since an arbitrage needs all three.
    """
    best = [None, None, None]
    books = [None, None, None]

    for book_name, book in (fixture.get("bookmakerOdds") or {}).items():
        if not book.get("bookmakerIsActive", True):
            continue

        market = (book.get("markets") or {}).get(MARKET_1X2)
        if not market:
            continue

        for index, outcome_id in enumerate((OUTCOME_HOME, OUTCOME_DRAW, OUTCOME_AWAY)):
            price = _outcome_price(market, outcome_id)
            if price is not None and (best[index] is None or price > best[index]):
                best[index] = price
                books[index] = book_name

    if any(price is None for price in best):
        return None
    return [_decimal_to_fractional(p) for p in best], books


def get_bets(tournament_ids, bookmakers, api_key=None, verbose=False):
    """Match rows for the given tournaments, shaped like the scraper's output.

    `bookmakers` is a list of bookmaker identifiers; taking the best price
    across several is what creates arbitrage opportunities in the first place.
    """
    if isinstance(tournament_ids, (int, str)):
        tournament_ids = [tournament_ids]
    if isinstance(bookmakers, str):
        bookmakers = [bookmakers]

    fixtures = _get(
        "/v4/odds-by-tournaments",
        api_key=api_key,
        bookmaker=",".join(bookmakers),
        tournamentIds=",".join(str(t) for t in tournament_ids),
        oddsFormat="decimal",
    )

    matches = []
    for fixture in fixtures:
        if not fixture.get("hasOdds"):
            continue

        priced = best_prices(fixture)
        if priced is None:
            continue
        (bet1, bet2, bet3), books = priced

        home, away = _team_names(fixture)
        match = Match(
            home, away, bet1, bet2, bet3, books,
            fixture.get("fixtureId"), fixture.get("startTime"),
        )
        matches.append(match)

        if verbose:
            print("%s vs %s  %.2f %.2f %.2f  (%s)"
                  % (home, away, bet1, bet2, bet3, ", ".join(books)))

    return matches
