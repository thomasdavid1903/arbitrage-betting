import requests
from bs4 import BeautifulSoup

def get_profitable_combinations(url):
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')

    # Find all the football match elements
    match_elements = soup.find_all('div', class_='football-match')
    print(match_elements)
    for match_element in match_elements:
        # Extract relevant information for each match
        teams = match_element.find_all('span', class_='team-name')
        team1 = teams[0].text.strip()
        team2 = teams[1].text.strip()

        odds_elements = match_element.find_all('span', class_='odds-value')
        odds = [float(odd.text) for odd in odds_elements]
        print( "Match : ",team1, " vs ", team2)
        # Calculate profitability based on odds
        if len(odds) == 3:
            # Assuming the odds are in the format: [home, draw, away]
            if odds[0] > 1 and odds[1] > 1 and odds[2] > 1:
                print(f"Profitable combinations for {team1} vs {team2}:")
                print(f"- Home win: {odds[0]}")
                print(f"- Draw: {odds[1]}")
                print(f"- Away win: {odds[2]}")
                print()
        if len(odds) == 2:
            # Assuming the odds are in the format: [home win, away win]
            if odds[0] > 1 and odds[1] > 1:
                print(f"Profitable combinations for {team1} vs {team2}:")
                print(f"- Home win: {odds[0]}")
                print(f"- Away win: {odds[1]}")
                print()
# Example usage
url = "https://www.easyodds.com/football/"
get_profitable_combinations(url)



