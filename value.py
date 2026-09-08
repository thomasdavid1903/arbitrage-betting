"""Find prices that beat a sharp bookmaker's estimate of the true odds.

An arbitrage needs two books wrong at once, which is why they are rare. A
value bet needs only one: take a sharp book's prices as the best available
estimate of what will actually happen, strip its margin out, and look for a
soft book offering more than that.

The trade is explicit. An arbitrage is risk-free and almost never available;
a value bet is a positive expectation that loses most of the time on long
shots and only pays over many bets. This module reports edges; it does not
suggest anyone act on them.

What makes it work here is that it needs one book to quote a market rather
than two, so the overlap problem that made tennis produce nothing does not
apply.
"""

from markets import (MAX_OUTCOMES, RULE_STANDARD, _coherent, _ranks_agree,
                     rule_risk)
from core import implied_sum

# The reference book. Pinnacle runs low margins and high limits and moves
# first, so its prices are the closest thing available to a market consensus.
DEFAULT_REFERENCE = "pinnacle"

# Edges above this are not real. A soft book is loose, not charitable, and on
# live data anything larger has meant a mapping fault rather than an
# opportunity.
MAX_PLAUSIBLE_EDGE = 0.20

# Below this an edge is inside the error of the method itself.
MIN_EDGE = 0.01


def devig_proportional(decimals):
    """Margin removed by dividing each implied probability by their sum.

    The obvious method, and biased: it assumes a book spreads its margin
    evenly, when in practice more of it sits on the long shots. Applied here
    it made every outsider look like value -- mean edge rose from 3.6% at
    short prices to 7.3% above 10.0, which is the bias rather than the market.
    """
    total = implied_sum(decimals)
    return [(1.0 / d) / total for d in decimals], total


def devig_power(decimals, tolerance=1e-9, max_iterations=80):
    """Margin removed by raising implied probabilities to a common power.

    Solves for k in sum((1/d)**k) = 1. Because k > 1, the exponent shrinks
    small probabilities more than large ones, which is the shape of a real
    bookmaker's margin: outsiders carry more of it than favourites.

    Falls back to the proportional result if the solve fails to converge.
    """
    raw = [1.0 / d for d in decimals]
    total = sum(raw)
    if total <= 1:
        return [p / total for p in raw], total

    low, high = 1.0, 10.0
    for _ in range(max_iterations):
        k = (low + high) / 2
        s = sum(p ** k for p in raw)
        if abs(s - 1) < tolerance:
            break
        if s > 1:
            low = k
        else:
            high = k
    else:
        return [p / total for p in raw], total

    adjusted = [p ** k for p in raw]
    scale = sum(adjusted)
    return [p / scale for p in adjusted], total


# The power method is the default: proportional is kept for comparison and
# because it is what most write-ups of this technique use.
devig = devig_power


def kelly_fraction(probability, decimal_odds):
    """Share of a bankroll Kelly would stake. Negative means no bet.

    Full Kelly is famously punishing when the probability is even slightly
    wrong, and here it is an estimate from another bookmaker's prices, so a
    fraction of this is the only sane way to use it.
    """
    b = decimal_odds - 1
    if b <= 0:
        return 0.0
    q = 1 - probability
    return max(0.0, (probability * b - q) / b)


def find_value(market_sink, matches, index, reference=DEFAULT_REFERENCE,
               min_edge=MIN_EDGE, operators=None):
    """Every soft price that beats the reference book's fair odds.

    The guards from the arbitrage path apply here too. A swapped outcome
    label between two books manufactures value exactly as it manufactures
    arbitrage, and a market the two books settle differently is not a
    comparison at all -- you would be pricing one bet against another.
    """
    operators = operators or {}
    reference_operator = operators.get(reference, reference)
    meta = {m.fixture_id: m for m in matches}
    rows = []

    for fixture_id, fixture_markets in market_sink.items():
        match = meta.get(fixture_id)

        for market_id, by_book in fixture_markets.items():
            definition = index.get(str(market_id))
            if not definition:
                continue
            expected = definition.get("marketLength") or 0
            if not 2 <= expected <= MAX_OUTCOMES:
                continue

            sharp = by_book.get(reference)
            if not sharp or len(sharp) != expected or not _coherent(sharp):
                continue

            ordered = sorted(sharp.items())
            fair, margin = devig([p["price"] for _, p in ordered])
            fair_by_outcome = {oid: p for (oid, _), p in zip(ordered, fair)}

            for book_name, prices in by_book.items():
                if operators.get(book_name, book_name) == reference_operator:
                    continue
                if len(prices) != expected or not _coherent(prices):
                    continue
                # A book that disagrees with the sharp book about which
                # outcome is likeliest has had its labels swapped, not found
                # an edge.
                if not _ranks_agree({reference: sharp, book_name: prices}):
                    continue

                risk, note = rule_risk(definition.get("marketType"),
                                       [reference, book_name])

                for outcome_id, data in prices.items():
                    probability = fair_by_outcome.get(outcome_id)
                    if probability is None:
                        continue

                    price = data["price"]
                    edge = price * probability - 1.0
                    if edge < min_edge or edge > MAX_PLAUSIBLE_EDGE:
                        continue

                    rows.append({
                        "fixtureId": fixture_id,
                        "home": match.home if match else "",
                        "away": match.away if match else "",
                        "startTime": match.start_time if match else None,
                        "marketId": market_id,
                        "marketName": definition.get("marketName"),
                        "marketType": definition.get("marketType"),
                        "handicap": definition.get("handicap"),
                        "outcome": _outcome_name(definition, outcome_id, data),
                        "book": book_name,
                        "price": price,
                        "fairPrice": round(1.0 / probability, 3),
                        "probability": round(probability, 4),
                        "edge": round(edge, 5),
                        "kelly": round(kelly_fraction(probability, price), 4),
                        "limit": data.get("limit"),
                        "changedAt": data.get("changedAt"),
                        "referenceChangedAt": sharp.get(outcome_id, {}).get("changedAt"),
                        "link": data.get("link"),
                        "deepLink": data.get("deepLink", False),
                        "referenceMargin": round(margin, 4),
                        "ruleRisk": risk,
                        "ruleNote": note,
                    })

    rows.sort(key=lambda r: -r["edge"])
    return rows


def _outcome_name(definition, outcome_id, data):
    for outcome in definition.get("outcomes") or []:
        if str(outcome.get("outcomeId")) == str(outcome_id):
            return outcome.get("outcomeName")
    return data.get("label") or outcome_id


def summarise(rows, reference=DEFAULT_REFERENCE):
    """Headline counts, and which books are loosest."""
    standard = [r for r in rows if r["ruleRisk"] == RULE_STANDARD]

    by_book = {}
    for row in rows:
        entry = by_book.setdefault(row["book"], {"book": row["book"], "count": 0,
                                                 "totalEdge": 0.0, "best": 0.0})
        entry["count"] += 1
        entry["totalEdge"] += row["edge"]
        entry["best"] = max(entry["best"], row["edge"])
    books = sorted(by_book.values(), key=lambda b: -b["count"])
    for entry in books:
        entry["meanEdge"] = round(entry["totalEdge"] / entry["count"], 5)
        del entry["totalEdge"]

    by_type = {}
    for row in rows:
        entry = by_type.setdefault(row["marketType"], {"marketType": row["marketType"],
                                                       "count": 0, "best": 0.0})
        entry["count"] += 1
        entry["best"] = max(entry["best"], row["edge"])
    types = sorted(by_type.values(), key=lambda t: -t["count"])[:12]

    return {
        "reference": reference,
        "total": len(rows),
        "standardRules": len(standard),
        "bestEdge": max((r["edge"] for r in rows), default=0.0),
        "meanEdge": round(sum(r["edge"] for r in rows) / len(rows), 5) if rows else 0.0,
        "books": books,
        "types": types,
    }
