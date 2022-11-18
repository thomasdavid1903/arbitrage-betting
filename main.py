#
# Got to think about bes tway to automate getting bets for sports, and the leagues in those sports
#  E.g Premier league in football
#

from bets import get_bets
from core import points


def main():
    tournaments = get_bets()

    for league in tournaments:

        for matches in tournaments[league]:
            bets = tournaments[league][matches]

            points(bets[0], bets[1], bets[2], precision=2)


if __name__ == "__main__":
    main()



