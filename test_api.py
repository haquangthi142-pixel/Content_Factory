import os
import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("API_FOOTBALL_KEY", "")

url = "https://api.football-data.org/v4/competitions/WC/matches"
headers = {"X-Auth-Token": API_KEY}

# Có thể lọc theo mùa giải 2026
querystring = {"season": "2026"}

response = requests.get(url, headers=headers, params=querystring)
data = response.json()
print(data)
if 'matches' in data:
    print(f"Tìm thấy {len(data['matches'])} trận đấu!")
    # In thử trận đầu tiên
    if data['matches']:
        match = data['matches'][0]
        print(f"Trận đấu: {match['homeTeam']['name']} vs {match['awayTeam']['name']}")
else:
    print("Lỗi hoặc chưa có dữ liệu:", data)