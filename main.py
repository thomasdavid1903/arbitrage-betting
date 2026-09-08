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
from core import best_stakes, implied_probability, profit_if

# Tournament slugs, resolved to the API's numeric ids at run time.
COMPETITIONS = [
    'premier-league',
    'uefa-champions-league',
    'world-cup',
    'championship',
    'la-liga',
    'uefa-europa-league',
    'uefa-nations-league',
    'campeonato-brasileiro-serie-a',
]

# Taking the best price across several books is what creates the arbitrage;
# a single bookmaker's own prices are always overround in its favour.
BOOKMAKERS = ['pinnacle', 'bet365', 'williamhill', 'betfair', 'unibet']

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


def main(competitions=COMPETITIONS, bookmakers=BOOKMAKERS, precision=1, api_key=None):
    tournament_ids = oddspapi.find_tournament_ids(competitions, api_key=api_key)
    if not tournament_ids:
        print("none of those competition slugs matched a tournament")
        return []

    print("checking %d tournaments across %d bookmakers"
          % (len(tournament_ids), len(bookmakers)))

    matches = oddspapi.get_bets(
        tournament_ids, bookmakers, api_key=api_key, verbose=True
    )
    print("%d matches priced on all three outcomes" % len(matches))

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
