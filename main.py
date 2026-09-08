# Fetches odds and reports the profitable matches and the stakes to place.
# Automation of the actual bet placement is still to come.
#
# Main program should eventually loop so it can re-check matches, since odds
# move and a match can turn profitable later. Placing bets, moving winnings
# back to PayPal and topping up bookmaker balances all remain unimplemented.

import os
import sys

import pandas as pd
from tabulate import tabulate

import oddspapi
from core import best_stakes, implied_probability, overround, profit_if

# (country category, tournament slug). The category is required because slugs
# repeat: 36 different tournaments are called 'premier-league'.
COMPETITIONS = [
    ('england', 'premier-league'),
    ('england', 'championship'),
    ('spain', 'laliga'),
    ('brazil', 'brasileiro-serie-a'),
    ('international-clubs', 'uefa-champions-league'),
    ('international-clubs', 'uefa-europa-league'),
    ('international', 'uefa-nations-league'),
]

# One API request per bookmaker per chunk of five tournaments, so this list
# sets the cost of a scan directly. Slugs must match /v4/bookmakers
# ('betfair-ex', not 'betfair').
#
# Every entry is a different operator. Coral, Sky Bet, Betfair and 888sport
# are deliberately absent: they belong to the same companies as Ladbrokes,
# Paddy Power and William Hill respectively, so they add requests without
# adding an independent price.
BOOKMAKERS = [
    'pinnacle',      # sharp, moves first
    'bet365',
    'paddypower',    # Flutter
    'ladbrokes',     # Entain
    'williamhill',   # evoke
    'betfred',
    'betway',
    'unibet',
    'boylesports',
    'marathonbet',
]

COLUMNS = [
    "Team 1", "Team 2",
    "Win 1 odds", "Draw odds", "Win 2 odds",
    "Bookmakers", "Best bets", "Winnings",
    "Probabilities", "Sum of P", "Cost",
    "Expected returns", "Profit per pound betted",
]


def find_arbitrage(match, precision=1):
    """Return a results row for a match, or None when it is not profitable.

    Accepts either an oddspapi.Match or a plain [home, away, b1, b2, b3] row,
    so the old scraper output still works.
    """
    home_name, away_name = match[0], match[1]
    bet1, bet2, bet3 = match[2], match[3], match[4]
    books = getattr(match, "books", None) or ["?", "?", "?"]

    result = best_stakes(bet1, bet2, bet3, precision=precision)
    if result is None:
        return None
    stakes, ratio = result

    wins = profit_if(stakes, bet1, bet2, bet3)
    probabilities = [implied_probability(b) for b in (bet1, bet2, bet3)]
    expected_returns = sum(w * p for w, p in zip(wins, probabilities))

    return [
        home_name, away_name, bet1, bet2, bet3,
        books,
        stakes,
        [round(w, 4) for w in wins],
        [round(p, 4) for p in probabilities],
        round(sum(probabilities), 4),
        sum(stakes),
        expected_returns,
        ratio,
    ]


def requests_needed(found, bookmakers):
    """Requests one scan costs: tournaments and participants, plus the odds
    calls, which are one per bookmaker per chunk of five tournaments."""
    chunks = -(-len(found) // oddspapi.MAX_TOURNAMENTS_PER_REQUEST)
    return 2 + len(bookmakers) * chunks


def report_margins(matches, limit=10):
    """Show the matches that came closest to an arbitrage.

    Useful even on a run that finds nothing: it says whether the market is
    narrowly missing or nowhere near.
    """
    ranked = sorted(matches, key=lambda m: overround(m[2], m[3], m[4]))
    print("\nclosest to an arbitrage (overround below 1.0 would be one):")
    for m in ranked[:limit]:
        books = getattr(m, "books", None) or ["?", "?", "?"]
        print("  %.4f  %-40s %-18s %s" % (
            overround(m[2], m[3], m[4]),
            (str(m[0]) + " v " + str(m[1]))[:40],
            " ".join("%.2f" % (b + 1) for b in (m[2], m[3], m[4])),
            "/".join(books)))


def main(competitions=COMPETITIONS, bookmakers=BOOKMAKERS, precision=1, api_key=None):
    found, missing = oddspapi.find_tournament_ids(competitions, api_key=api_key)
    for key in missing:
        print("no upcoming fixtures for %s/%s" % key)
    if not found:
        print("nothing to check")
        return []

    print("checking %d tournaments across %d bookmakers (%d requests)"
          % (len(found), len(bookmakers), requests_needed(found, bookmakers)))

    names = oddspapi.get_participants(api_key=api_key)
    matches = oddspapi.get_bets(
        list(found.values()), bookmakers, api_key=api_key, verbose=True, names=names
    )
    print("%d matches priced on all three outcomes" % len(matches))
    if matches:
        report_margins(matches)

    profitable_bets = []
    for match in matches:
        row = find_arbitrage(match, precision=precision)
        if row is not None:
            profitable_bets.append(row)

    return profitable_bets


if __name__ == "__main__":
    if not os.environ.get("ODDSPAPI_KEY"):
        sys.exit("set ODDSPAPI_KEY first (see https://oddspapi.io)")

    data = main()
    if data:
        frame = pd.DataFrame(data, columns=COLUMNS)
        frame = frame.sort_values("Profit per pound betted", ascending=False)
        print(tabulate(frame, headers=COLUMNS, tablefmt="fancy_grid"))
    else:
        print("No profitable matches found.")
