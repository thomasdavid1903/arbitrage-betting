import urllib.request as ul

from bs4 import BeautifulSoup as soup

BASE_URL = "https://easyodds.com/football/"

# Some sites reject the default urllib agent outright.
HEADERS = {"User-Agent": "Mozilla/5.0"}


def parse_odds(text: str) -> float:
    """Fractional odds ("5/2") as a ratio of net profit to stake.

    Evens is written several ways depending on the page, so those are handled
    explicitly. Anything else raises ValueError for the caller to skip.
    """
    text = text.strip().lower()
    if text in ("evs", "evens", "even", "1/1"):
        return 1.0

    if "/" in text:
        numerator, _, denominator = text.partition("/")
        return float(numerator) / float(denominator)

    raise ValueError("unrecognised odds format: " + text)


def fetch_page(tournament: str) -> str:
    request = ul.Request(BASE_URL + tournament, headers=HEADERS)
    with ul.urlopen(request) as client:
        return client.read()


def get_bets(tournament, verbose=False):
    """Scrape a competition page and return [home, away, bet1, bet2, bet3] rows.

    Odds are the best price the aggregator lists, which may come from three
    different bookmakers.
    """
    if verbose:
        print("\n ------------- ( " + tournament + " ) -----------------")
        print(BASE_URL + tournament)

    pagesoup = soup(fetch_page(tournament), "html.parser")
    rows = pagesoup.findAll('a', {"class": "eo-match"})

    if verbose:
        print(str(len(rows)) + " matches found on the page")

    bets = []

    for item in rows:
        home = item.find_next('span', {'class': 'match-side itm-side1'})
        draw = item.find_next('span', {'class': 'draw-odds'})
        away = item.find_next('span', {'class': 'match-side itm-side2'})

        if home is None or draw is None or away is None:
            # Layout differs for postponed or in-play matches; skip them.
            continue

        try:
            home_name = home.find_next('span', {'class': 'side-name'}).text.strip()
            away_name = away.find_next('span', {'class': 'side-name'}).text.strip()

            bet1 = parse_odds(home.find_next('span', {'class': 'side-odds'}).text)
            bet2 = parse_odds(draw.text)
            bet3 = parse_odds(away.find_next('span', {'class': 'side-odds'}).text)
        except (AttributeError, ValueError, ZeroDivisionError) as exc:
            if verbose:
                print("skipping a match: " + str(exc))
            continue

        if verbose:
            print(home_name + " vs " + away_name)
            print("%s %s %s" % (bet1, bet2, bet3))

        bets.append([home_name, away_name, bet1, bet2, bet3])

    return bets


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

    def __init__(self):
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
