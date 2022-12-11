#
# Got to think about bes tway to automate getting bets for sports, and the leagues in those sports
#  E.g Premier league in football
# i reckon at the moment we just focus on getting a program where it takes the bets from the website and reports back the profitable matches and the possible bets
## and worry about the automation later
from tabulate import tabulate
from bets import get_bets
from core import points
import pandas as pd
from paypal_bridge import PayPal
from bookies_bridge import Bookies

##############################################
#
# Main program should loop infinitely in order
# to check and make the bets, see nas bets can
# be updated.
#
# Bets may be updated from non-profitable to
# profitable.
#
# Program also needs to take winnings, move it
# back to PayPal, and distribute where
# necessary in case of low balance on other
# bookies site.
#
##############################################


def main():
    profitableBets = []
    competition = ['premier-league','uefa-champions-league','world-cup','championship','la-liga','uefa-europa-league']

    for i in range(len(competition)):

        print(" ---------- { " + competition[i] + " } ----------")

        tournament = get_bets(tournament=competition[i])

        for match in tournament:
            home_name = match[0]
            away_name = match[1]

            bet1 = match[2]
            bet2 = match[3]
            bet3 = match[4]

            profitable_bets = points(bet1, bet2, bet3, precision=3)
            bet1Win = 0
            bet2Win = 0
            bet3Win = 0
            # If list is not empty, profitable bets exist
            if profitable_bets:
                print(match)
                # Find bet in bookies and make bet
                highestTotal = 0
                bestCombo = []
                for bets in profitable_bets:
                    if(highestTotal<bets[0]*bet1 + bets[1]*bet2 + bets[2]*bet3 - (2*sum(bets))):
                        highestTotal = bets[0]*bet1 + bets[1]*bet2 + bets[2]*bet3 - (2*sum(bets))

                        bet1Win = bets[0] * bet1 - sum(bets) + bets[0]
                        bet2Win = bets[1] * bet2 - sum(bets) + bets[1]
                        bet3Win = bets[2] * bet3 - sum(bets)+ bets[2]

                        probabilyBet1 = 1/(bet1 + 1)
                        probabilyBet2 = 1 /(bet2 + 1)
                        probabilyBet3 = 1 /(bet3 + 1)
                        expectedReturns =  bet1Win*probabilyBet1 + bet2Win*probabilyBet2 + bet3Win*probabilyBet3
                        bestCombo = bets
                print(" ")
                print("Best bet : ", bestCombo)
                print("Bet1 Profit : " , bet1Win, " Bet2 Profit " , bet2Win, " Bet3 Profit " , bet3Win )
                print("Bet1 Probability : ", probabilyBet1, " Bet2 Probability ", probabilyBet2, " Bet3 Probability ", probabilyBet3)
                print("Expected return : ",expectedReturns , "when bet", sum(bets))
                print(" ")
                profitableBets.append( [match[0], match[1], match[2], match[3], match[4], bestCombo , expectedReturns, expectedReturns/sum(bets)] )
                print(match[0], match[1], match[2], match[3], match[4], bestCombo , expectedReturns, expectedReturns/sum(bets) )
    return profitableBets
if __name__ == "__main__":
    data = main()
    col_names = ["Team 1 ", "Team 2 ","Win 1 ", "Draw ", "Win 2 ", "Best bets ","Expected returns","expected returns over invest"]
    data = pd.DataFrame(data)
    data.sort_values(7)
    print(tabulate(data, headers=col_names, tablefmt="fancy_grid"))



