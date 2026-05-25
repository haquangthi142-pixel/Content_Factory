# import os
# import requests
# from dotenv import load_dotenv

# load_dotenv()

# API_KEY = os.getenv("API_FOOTBALL_KEY", "")

# # url = "https://api.football-data.org/v4/competitions/WC/matches"
# url = "https://v3.football.api-sports.io/standings"
# headers = {"X-Auth-Token": API_KEY}

# # Có thể lọc theo mùa giải 2026
# querystring = {"season": "2026"}

# query_params = {
#     "league": "1",
#     "season": "2026"
# }
# response = requests.get(url, headers=headers, params=query_params)
# data = response.json()
# print(data)
# if 'matches' in data:
#     print(f"Tìm thấy {len(data['matches'])} trận đấu!")
#     # In thử trận đầu tiên
#     if data['matches']:
#         match = data['matches'][0]
#         print(f"Trận đấu: {match['homeTeam']['name']} vs {match['awayTeam']['name']}")
# else:
#     print("Lỗi hoặc chưa có dữ liệu:", data)



import requests

API_KEY = 'uBG9FBTqmIdA1OoKTlDs0F04ZUxrKPRM'  # Replace with your actual API key
BASE_URL = 'https://getbloombet.com/api'
SPORT = 'nfl'  # Available values are 'nba' or 'nfl'

# Get live odds
response = requests.get(
    f'{BASE_URL}/live',
    params={
        'api_key': API_KEY,
        'sport': SPORT
    }
)

if response.status_code == 200:
    data = response.json()
    print(data)
else:
    print(f"Error: {response.status_code}")
    print(response.text)
                    