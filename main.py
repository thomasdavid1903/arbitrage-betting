# Takes the odds from the website and reports back the profitable matches and
# the stakes to place. Automation of the actual bet placement is still to come.
#
# Main program should eventually loop so it can re-check matches, since odds
# move and a match can turn profitable later. Placing bets, moving winnings
# back to PayPal and topping up bookmaker balances all remain unimplemented.

import pandas as pd
from tabulate import tabulate

from core import best_stakes, implied_probability, profit_if
from utils import get_bets

COMPETITIONS = [
    'premier-league',
    'uefa-champions-league',
    'world-cup',
    'championship',
    'la-liga',
    'uefa-europa-league',
    'euro-2024',
    'uefa-nations-league',
    'campeonato-brasileiro-serie-a',
    '',
]

COLUMNS = [
    "Team 1", "Team 2",
    "Win 1 odds", "Draw odds", "Win 2 odds",
    "Best bets", "Winnings", "Probabilities", "Sum of P",
    "Cost", "Expected returns", "Profit per pound betted",
]


def find_arbitrage(match, precision=1):
    """Return a results row for a match, or None when it is not profitable."""
    home_name, away_name, bet1, bet2, bet3 = match

    result = best_stakes(bet1, bet2, bet3, precision=precision)
    if result is None:
        return None
    stakes, ratio = result

    wins = profit_if(stakes, bet1, bet2, bet3)
    probabilities = [implied_probability(b) for b in (bet1, bet2, bet3)]
    expected_returns = sum(w * p for w, p in zip(wins, probabilities))

    return [
        home_name, away_name, bet1, bet2, bet3,
        stakes,
        [round(w, 4) for w in wins],
        [round(p, 4) for p in probabilities],
        round(sum(probabilities), 4),
        sum(stakes),
        expected_returns,
        ratio,
    ]


def main(competitions=COMPETITIONS, precision=1):
    profitable_bets = []

    for competition in competitions:
        print(" ---------- { " + competition + " } ----------")

        try:
            matches = get_bets(tournament=competition)
        except Exception as exc:
            # One dead competition page should not abort the whole run.
            print("could not fetch " + competition + ": " + str(exc))
            continue

        for match in matches:
            row = find_arbitrage(match, precision=precision)
            print(match)
            if row is not None:
                profitable_bets.append(row)
                print(row)

    return profitable_bets


if __name__ == "__main__":
    data = main()
    if data:
        frame = pd.DataFrame(data, columns=COLUMNS)
        frame = frame.sort_values("Profit per pound betted", ascending=False)
        print(tabulate(frame, headers=COLUMNS, tablefmt="fancy_grid"))
    else:
        print("No profitable matches found.")
