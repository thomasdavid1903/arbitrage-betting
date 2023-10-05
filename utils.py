import urllib.request as ul
from bs4 import BeautifulSoup as soup


def get_bets(tournament, verbose=False):
    if verbose:
        print("\n ------------- ( " + tournament + " ) -----------------")

    football_url = "https://easyodds.com/football/" + tournament
    print(football_url)

    req = ul.Request(football_url)

    client = ul.urlopen(req)
    htmldata = client.read()
    client.close()

    pagesoup = soup(htmldata, "html.parser")
    row = pagesoup.findAll('a', {"class": "eo-match"})
    ##### THIS DOESNT RETURN ALL BETS
    # href =
    print(row , " : this is the bets fetched from website")
    bets = []

    for item in row:

        #game = item.find_next('a')
        game_link = item['href']

        """
        game_req = ul.Request(game_link)

        client = ul.urlopen(game_req)
        htmldata = client.read()
        client.close()
    
        pagesoup = soup(htmldata, "html.parser")

        rows = pagesoup.findAll('div', {'class': 'eo-outcome'})

        temp = [bet.findAllNext('a', {'class': 'eo-bestBookie-odds'}) for bet in rows]

        for a in temp:
            print(a)
        """
        """
        for bet in rows:
            bets = bet.findAllNext('div', {'class': 'eo-actions-bestBookie'})

            for temp in bets:
                temp1 = temp.findAllNext('a', {'class': 'eo-bestBookie-odds'})
                
                
                
                print(temp1)

            #print(bets)
        """

        home = item.find_next('span', {'class': 'match-side itm-side1'})
        draw = item.find_next('span', {'class': 'draw-odds'})
        away = item.find_next('span', {'class': 'match-side itm-side2'})

        home_name = home.find_next('span', {'class': 'side-name'}).text.strip()
        home_bet = home.find_next('span', {'class': 'side-odds'}).text.strip()

        draw_bet = draw.text.strip()

        away_name = away.find_next('span', {'class': 'side-name'}).text.strip()
        away_bet = away.find_next('span', {'class': 'side-odds'}).text.strip()

        if verbose:
            print(home_name + " vs " + away_name)
            print(home_bet + " " + draw_bet + " " + away_bet)

        bet1 = float(home_bet.split("/")[0]) / float(home_bet.split("/")[1])
        bet2 = float(draw_bet.split("/")[0]) / float(draw_bet.split("/")[1])
        bet3 = float(away_bet.split("/")[0]) / float(away_bet.split("/")[1])

        bets.append([home_name, away_name, bet1, bet2, bet3])

    return bets

##def get_odds():
    tournaments = ['premier-league', 'uefa-champions-league']
    odds = []
    bets_tournaments = {}

    for t in tournaments:

        print("\n ------------- ( " + t + " ) -----------------")

        football_url = "https://easyodds.com/football/" + t
        req = ul.Request(football_url)
        client = ul.urlopen(req)
        htmldata = client.read()
        client.close()

        pagesoup = soup(htmldata, "html.parser")
        itemlocator = pagesoup.findAll('div', {"class": "tournament-event__row"})

        bets = {}

        for item in itemlocator:
            home = item.find_next('div', {'class': 'tournament-event__cell event-team event-team-home'})
            draw = item.find_next('div', {'class': 'tournament-event__cell event-draw'})
            away = item.find_next('div', {'class': 'tournament-event__cell event-team event-team-away'})

            home_name = (home.find_next('div', {'class': 'event-team__name'})).text.strip()
            home_bet = (home.find_next('span', {'class': 'odds-button'})).text.strip()

            draw_bet = (draw.find_next('span', {'class': 'odds-button'})).text.strip()

            away_name = (away.find_next('div', {'class': 'event-team__name'})).text.strip()
            away_bet = (away.find_next('span', {'class': 'odds-button'})).text.strip()

            print(home_name + " vs " + away_name)
            print(home_bet + " " + draw_bet + " " + away_bet)

            # Figure out return format for bets
            odds.append([home_name,away_name,float(home_bet), float(draw_bet), float(away_bet)])
        print(odds)
        return odds


class PayPal:
    """
    PayPal API:
        - Uses HTTP posting to communicate with paypal via web
        - Posting requires credentials
        - Researching how to post to paypal in order to transfer money

    Functions:
        - Send Money (Via address)
        - Check Balance
        - Get recent transactions

    """

    def __int__(self):
        pass

    def call(self):
        ...


class Bookies:
    """
    Bookies API:

    """

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

