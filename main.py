#
# Got to think about bes tway to automate getting bets for sports, and the leagues in those sports
#  E.g Premier league in football
# i reckon at the moment we just focus on getting a program where it takes the bets from the website and reports back the profitable matches and the possible bets
## and worry about the automation later

from bets import get_bets
from core import points
from paypal_bridge import PayPal


def main():
    #tournament = get_bets(tournament='premier-league')
    #tournament = get_bets(tournament='uefa-champions-league')
    # tournament = get_bets(tournament='world-cup')
    # tournament = get_bets(tournament='championship')
    # tournament = get_bets(tournament='la-liga')
    # tournament = get_bets(tournament='uefa-europa-league')

    competition = ['premier-league','uefa-champions-league','world-cup','championship','la-liga','uefa-europa-league']

    tournament = get_bets(tournament='uefa-europa-league')

    for matches in tournament:
        print(matches)
        bets = tournament[matches]

        bet1 = bets[0]
        bet1 = float(bet1.split("/")[0]) / float(bet1.split("/")[1])

        bet2 = bets[1]
        bet2 = float(bet2.split("/")[0]) / float(bet2.split("/")[1])

        bet3 = bets[2]
        bet3 = float(bet3.split("/")[0]) / float(bet3.split("/")[1])

        profitableBets = points(bet1, bet2, bet3, precision=2)

        # Tommy

        # 'points' needs to return something that can be used to decide whether a bet should be made or not
        # and what team to bet on

    return


if __name__ == "__main__":
    main()



