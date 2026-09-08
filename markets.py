"""Find arbitrages across every market a fixture offers, not only 1X2.

An odds response carries roughly 80 markets per fixture -- over/under lines,
both teams to score, handicaps, team totals -- and the great majority are
two-way. Scanning only the match result means hunting in the most efficiently
priced market on the board while ignoring the rest of a response already paid
for.

The arbitrage test is in core.arb_stakes: stakes proportional to 1/decimal pay
the same whichever outcome lands, so the sum of implied probabilities falling
below 1 is exactly the condition, for any number of outcomes.

Most of this module is not the test but the checks around it. Taking the best
price per outcome across bookmakers produces false arbitrages wherever the
feed's outcome mapping is imperfect, and on real data those vastly outnumber
the true ones -- so a market has to earn the right to be judged.
"""

from core import arb_stakes, implied_sum

# ---------------------------------------------------------------------------
# Settlement-rule risk.
#
# Two bookmakers can quote the same-looking line and settle it differently.
# Where that happens the two legs are not opposite sides of one bet, so the
# "arbitrage" is not one and both legs can lose.
#
# Goals are safe: every book settles ninety minutes plus stoppage time, extra
# time excluded, and a goal is a goal. Bookings and corners are not:
#
#   - some books price booking points (10 a yellow, 25 a red), others count
#     cards, and an Over/Under 2.5 line means different things under each
#   - a second yellow may count as one card, two, or three
#   - corners awarded but not taken, and whether extra time counts, vary
#
# That matters here because the large margins cluster precisely in those
# markets, which is what you would expect if the edge is a rules artifact
# rather than a pricing error.
# ---------------------------------------------------------------------------

# Markets with more outcomes than this are skipped: correct-score and
# scorecast markets are long, thinly quoted, and rarely a clean partition.
# Bumped whenever a guard changes what counts as an arbitrage. Scans found
# by different versions are not comparable, so persistence only measures
# within one version rather than reporting a survival rate across a change
# in what was being detected.
DETECTOR_VERSION = 3

MAX_OUTCOMES = 4

# An arbitrage capped below this is not worth the two bets it takes.
MIN_STAKE = 20.0

# A bookmaker builds a margin into its own book, so its complete quote should
# always imply more than 1. Anything below that means the outcomes have been
# mismapped -- prices from different underlying markets merged into one -- and
# the market cannot be trusted, however attractive it looks.
SELF_ARB_FLOOR = 1.0

# Two bookmakers price differently; they do not disagree about which outcome
# is likeliest. When one book's favourite is another's outsider, the feed has
# mapped the outcomes inconsistently between them, and taking the best of each
# label manufactures an enormous edge out of nothing. Prices within this
# fraction of each other are treated as a tie, since the ordering between them
# is not meaningful.
FAVOURITE_TOLERANCE = 0.15

# No genuine cross-book arbitrage on a mainstream football market runs into
# double figures. A ratio above this is a mapping artifact, not an
# opportunity, and is dropped rather than shown.
MAX_PLAUSIBLE_RATIO = 0.10

RULE_DIVERGENT = "divergent"
RULE_UNKNOWN = "unknown"
RULE_STANDARD = "standard"

# Which market families depend on a bookmaker's own definitions at all.
# Goals do not: every book settles ninety minutes plus stoppage, extra time
# excluded, and a goal is a goal.
RULE_FAMILIES = {
    "bookings": "cards",
    "cards": "cards",
    "corners": "corners",
}

# How each bookmaker settles a family, where it has been checked against the
# book's published rules. Books absent from a family are not assumed to match
# -- an unchecked pair is reported as unknown, not as safe.
#
# cards-1-2-ignore-second: yellow 1, red 2, second yellows ignored, so a
#   player tops out at 3; ninety minutes only; non-players excluded.
#   Verified for pinnacle and bet365 (their published rules agree exactly).
#   The competing convention is booking points -- yellow 10, red 25, a
#   second yellow counting 35 -- which settles an Over/Under line quite
#   differently.
#
# corners-taken-90min: only corners actually taken count, a retaken corner
#   counts once, ninety minutes plus stoppage, extra time excluded. Verified
#   for pinnacle and paddypower. The divergence to watch for elsewhere is
#   counting corners awarded but not taken.
#
# Ladbrokes does not publish its card rules in a form worth encoding, so it
# stays absent and its markets are reported unknown.
BOOK_RULE_SYSTEMS = {
    "cards": {
        "pinnacle": "cards-1-2-ignore-second",
        "bet365": "cards-1-2-ignore-second",
    },
    "corners": {
        "pinnacle": "corners-taken-90min",
        "paddypower": "corners-taken-90min",
    },
}

FAMILY_NOTES = {
    "cards": "books differ on whether cards or booking points are counted, "
             "and on how a second yellow is treated",
    "corners": "books differ on corners awarded versus taken, and on whether "
               "extra time counts",
}


def rule_risk(market_type, books=None):
    """Whether the books involved settle this market the same way.

    Returns (risk, note).

    A market on goals is standard for every bookmaker. A market on cards or
    corners depends on each book's own definitions, so it is judged on the
    books actually quoting it: matching verified systems are standard,
    differing ones divergent, and anything unchecked is unknown rather than
    assumed safe.
    """
    text = (market_type or "").lower()
    family = next((f for token, f in RULE_FAMILIES.items() if token in text), None)
    if family is None:
        return RULE_STANDARD, None

    note = FAMILY_NOTES[family]
    if not books:
        return RULE_UNKNOWN, note

    known = BOOK_RULE_SYSTEMS.get(family, {})
    systems = {known.get(b) for b in books}
    if None in systems:
        unchecked = sorted(b for b in books if b not in known)
        return RULE_UNKNOWN, note + " (rules not yet checked for %s)" % ", ".join(unchecked)
    if len(systems) == 1:
        return RULE_STANDARD, None
    return RULE_DIVERGENT, note


def _book_quotes_market(prices, expected):
    """Whether a bookmaker has quoted the market completely."""
    return len(prices) == expected


def _favourites(prices):
    """Outcomes a book prices at or near the shortest odds."""
    best = min(p["price"] for p in prices.values())
    return {oid for oid, p in prices.items()
            if p["price"] <= best * (1 + FAVOURITE_TOLERANCE)}


def _ranks_agree(complete):
    """Whether every complete quote agrees on the likeliest outcome.

    Disagreement means the outcome labels do not line up between books, so
    the prices are not comparable and must not be combined.
    """
    shared = None
    for prices in complete.values():
        favourites = _favourites(prices)
        shared = favourites if shared is None else (shared & favourites)
        if not shared:
            return False
    return True


def _coherent(prices):
    """Whether one book's outcomes all come from the same market at that book.

    The feed sometimes merges a price from a different bookmaker market into
    a normalised one; the betslip link gives it away. Those legs are not the
    same bet and combining them invents an arbitrage that cannot be placed.
    """
    sources = {p.get("sourceMarket") for p in prices.values() if p.get("sourceMarket")}
    return len(sources) <= 1


def evaluate_fixture(fixture_markets, index, bankroll=None, min_ratio=0.0,
                     operators=None):
    """Arbitrages in one fixture's collected markets.

    `fixture_markets` is what oddspapi.collect_all_markets returns; `index`
    maps market id to its definition.

    A market is judged only when it passes every check below. Each one exists
    because dropping it produced false positives on live data.
    """
    found = []

    for market_id, by_book in fixture_markets.items():
        definition = index.get(str(market_id))
        if not definition:
            continue

        expected = definition.get("marketLength") or 0
        if expected < 2 or expected > MAX_OUTCOMES:
            continue

        # At least one book must quote the whole market. Without a complete
        # quote there is nothing to check the outcome mapping against, and
        # stitching partial quotes together from several books invents
        # arbitrages wholesale -- it was worth 60 false alerts across ten
        # bookmakers before this check existed.
        complete = {b: p for b, p in by_book.items()
                    if _book_quotes_market(p, expected)}
        if not complete:
            continue

        if not _ranks_agree(complete):
            continue

        # Any book quoting the whole market must show a margin in its own
        # favour. If it does not, the outcomes have been mismapped.
        trustworthy = True
        for prices in complete.values():
            if not _coherent(prices):
                trustworthy = False
                break
            own = implied_sum([p["price"] for p in prices.values()])
            if own < SELF_ARB_FLOOR:
                trustworthy = False
                break
        if not trustworthy:
            continue

        # Best price per outcome across the books that pass.
        best = {}
        for book_name, prices in by_book.items():
            if not _coherent(prices):
                continue
            for outcome_id, data in prices.items():
                current = best.get(outcome_id)
                if current is None or data["price"] > current["price"]:
                    best[outcome_id] = dict(data, book=book_name)

        if len(best) != expected:
            continue

        ordered = sorted(best.items())
        decimals = [d["price"] for _, d in ordered]
        limits = [d.get("limit") for _, d in ordered]
        books = [d["book"] for _, d in ordered]

        result = arb_stakes(decimals, bankroll=bankroll, limits=limits)
        if not result or result["ratio"] <= min_ratio:
            continue
        if result["ratio"] > MAX_PLAUSIBLE_RATIO:
            continue
        if result["total"] < MIN_STAKE:
            continue

        risk, note = rule_risk(definition.get("marketType"), sorted(set(books)))

        found.append({
            "marketId": market_id,
            "marketName": definition.get("marketName"),
            "marketType": definition.get("marketType"),
            "ruleRisk": risk,
            "ruleNote": note,
            "period": definition.get("period"),
            "handicap": definition.get("handicap"),
            "outcomes": [{
                "outcomeId": oid,
                "name": _outcome_name(definition, oid, data),
                "price": data["price"],
                "book": data["book"],
                "limit": data.get("limit"),
                "changedAt": data.get("changedAt"),
                "link": data.get("link"),
                "deepLink": data.get("deepLink", False),
                "stake": round(stake, 2),
            } for (oid, data), stake in zip(ordered, result["stakes"])],
            "impliedSum": round(result["impliedSum"], 5),
            "ratio": round(result["ratio"], 5),
            "total": round(result["total"], 2),
            "profit": round(result["profit"], 2),
            "limited": result["limited"],
            # Every leg at one book is that book disagreeing with itself:
            # far likelier to be an error it will void than a real gap.
            # Clones count as one book, because they are one sportsbook
            # behind two brands and share the same prices and risk team.
            "singleBook": len({(operators or {}).get(b, b) for b in books}) == 1,
            "books": sorted(set(books)),
            "operators": sorted({(operators or {}).get(b, b) for b in books}),
        })

    found.sort(key=lambda r: -r["ratio"])
    return found


def _outcome_name(definition, outcome_id, data):
    """Readable outcome name, preferring the market definition's own."""
    for outcome in definition.get("outcomes") or []:
        if str(outcome.get("outcomeId")) == str(outcome_id):
            return outcome.get("outcomeName")
    return data.get("label") or outcome_id


def scan_markets(market_sink, matches, index, bankroll=None, min_ratio=0.0,
                 operators=None):
    """Every market arbitrage across a scan, best first.

    `matches` supplies team names and kick-off already resolved by the 1X2
    pass, so nothing extra is fetched.
    """
    meta = {m.fixture_id: m for m in matches}
    rows = []

    for fixture_id, fixture_markets in market_sink.items():
        match = meta.get(fixture_id)
        for row in evaluate_fixture(fixture_markets, index, bankroll, min_ratio,
                                    operators=operators):
            row["fixtureId"] = fixture_id
            row["home"] = match.home if match else ""
            row["away"] = match.away if match else ""
            row["startTime"] = match.start_time if match else None
            rows.append(row)

    rows.sort(key=lambda r: -r["ratio"])
    return rows


def coverage(market_sink, index):
    """How many markets were collected and how many were judged."""
    total = judged = 0
    for fixture_markets in market_sink.values():
        for market_id, by_book in fixture_markets.items():
            total += 1
            definition = index.get(str(market_id))
            if not definition:
                continue
            expected = definition.get("marketLength") or 0
            if 2 <= expected <= MAX_OUTCOMES:
                judged += 1
    return {"collected": total, "judged": judged}


def summarise(rows):
    """Counts for the page header: how many, and how many are actionable."""
    cross = [r for r in rows if not r["singleBook"]]
    # The count that matters is the one left after both filters: two
    # different books, and a market they settle the same way.
    solid = [r for r in cross if r["ruleRisk"] == RULE_STANDARD]
    return {
        "total": len(rows),
        "crossBook": len(cross),
        "singleBook": len(rows) - len(cross),
        "standardRules": len(solid),
        "uncheckedRules": len([r for r in rows if r["ruleRisk"] == RULE_UNKNOWN]),
        "divergentRules": len([r for r in rows if r["ruleRisk"] == RULE_DIVERGENT]),
        "bestRatio": max((r["ratio"] for r in rows), default=0.0),
        "bestSolidRatio": max((r["ratio"] for r in solid), default=0.0),
        "byType": _counts(r["marketType"] for r in rows),
    }


def _counts(values):
    out = {}
    for v in values:
        out[v] = out.get(v, 0) + 1
    return sorted(out.items(), key=lambda kv: -kv[1])


def margins(market_sink, matches, index):
    """Best achievable overround per judged market, for the distribution view.

    This is the useful output when nothing is an arbitrage: it says which
    kinds of market are priced loosely enough to be worth watching.
    """
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

            complete = {b: p for b, p in by_book.items() if len(p) == expected}
            if not complete:
                continue  # nothing to validate the outcome mapping against
            if any(not _coherent(p) for p in complete.values()):
                continue
            if not _ranks_agree(complete):
                continue
            if any(implied_sum([x["price"] for x in p.values()]) < SELF_ARB_FLOOR
                   for p in complete.values()):
                continue

            best = {}
            for book_name, prices in by_book.items():
                if not _coherent(prices):
                    continue
                for outcome_id, data in prices.items():
                    if outcome_id not in best or data["price"] > best[outcome_id]["price"]:
                        best[outcome_id] = dict(data, book=book_name)
            if len(best) != expected:
                continue

            risk, _ = rule_risk(definition.get("marketType"),
                                sorted(set(d["book"] for d in best.values())))
            rows.append({
                "marketType": definition.get("marketType"),
                "ruleRisk": risk,
                "marketName": definition.get("marketName"),
                "outcomes": expected,
                "overround": round(implied_sum([d["price"] for d in best.values()]), 5),
                "books": len(set(d["book"] for d in best.values())),
                "home": match.home if match else "",
                "away": match.away if match else "",
            })

    rows.sort(key=lambda r: r["overround"])
    return rows
