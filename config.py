import os
from dotenv import load_dotenv

load_dotenv()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
MODEL = "claude-sonnet-4-6"

CITY = "Katowice"
CITY_BBOX = (50.1850, 18.9200, 50.3200, 19.1500)  # (lat_min, lon_min, lat_max, lon_max)

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "katowice.db")

WALKING_SPEED_KMH = 4.5
AVG_TRAM_SPEED_KMH = 20.0
