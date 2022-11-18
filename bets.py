import urllib.request as ul
from bs4 import BeautifulSoup as soup


def get_bets(tournament, verbose=False):

    if verbose:
        print("\n ------------- ( " + tournament + " ) -----------------")

    football_url = "https://easyodds.com/football/" + tournament

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

        if verbose:
            print(home_name + " vs " + away_name)
            print(home_bet + " " + draw_bet + " " + away_bet)

        # Figure out return format for bets
        bets[home_name + " vs " + away_name] = [home_bet, draw_bet, away_bet]

    return bets

