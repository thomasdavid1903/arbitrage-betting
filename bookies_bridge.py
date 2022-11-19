#
# Copyright (C) Alex King - All Rights Reserved
#
# Unauthorized copying of this file, via any medium is strictly prohibited
# Proprietary and confidential
# 
# Created on DATE by USER
#

class Bookies:

    balance = 0
    active_bets = []

    def __init__(self):
        self.tick()

    def tick(self):
        """
        THIS FUNCTION NEEDS TO BE CALLED AT THE START OF EVERY OTHER FUNCTION
        :return:
        """
        self.update_balance()

    def update_balance(self) -> None:
        pass

    def get_balance(self) -> float:
        self.tick()
        return self.balance

    def make_bet(self, amount: float):
        self.tick()

        # If bet amount is below balance (should probably be a lot less than current balance)

        # Then place bet

    def get_bets(self) -> list:
        """Returns list of all active bets"""
        self.tick()
        return self.active_bets


def main():
    pass


if __name__ == "__main__":
    main()
