#
# Got to think about bes tway to automate getting bets for sports, and the leagues in those sports
#  E.g Premier league in football
#

from bets import get_bets
from core import points


def main():
    #tournament = get_bets(tournament='premier-league')
    #tournament = get_bets(tournament='uefa-champions-league')
    tournament = get_bets(tournament='world-cup')

    for matches in tournament:
        print(matches)
        bets = tournament[matches]

        bet1 = bets[0]
        bet1 = float(bet1.split("/")[0]) / float(bet1.split("/")[1])

        bet2 = bets[1]
        bet2 = float(bet2.split("/")[0]) / float(bet2.split("/")[1])

        bet3 = bets[2]
        bet3 = float(bet3.split("/")[0]) / float(bet3.split("/")[1])

        points(bet1, bet2, bet3, precision=2)

        return


if __name__ == "__main__":
    main()



