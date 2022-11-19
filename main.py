#
# Got to think about bes tway to automate getting bets for sports, and the leagues in those sports
#  E.g Premier league in football
# i reckon at the moment we just focus on getting a program where it takes the bets from the website and reports back the profitable matches and the possible bets
## and worry about the automation later

from bets import get_bets
from core import points
from paypal_bridge import PayPal


def main():

    competition = ['premier-league',
                   'uefa-champions-league',
                   'world-cup',
                   'championship',
                   'la-liga',
                   'uefa-europa-league']

    tournament = get_bets(tournament=competition[5])

    for match in tournament:
        print(match)

        home_name = match[0]
        away_name = match[1]

        bet1 = match[2]
        bet2 = match[3]
        bet3 = match[4]

        profitable_bets = points(bet1, bet2, bet3, precision=2)

        # If list is not empty, profitable bets exist
        if profitable_bets:
            # Find bet in bookies and make bet

            print(profitable_bets)


if __name__ == "__main__":
    main()



