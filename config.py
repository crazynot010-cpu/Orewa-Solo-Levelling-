import os
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")

CHAT_XP = 15
ARISE_COOLDOWN = 2  # seconds
SPAWN_MESSAGE_COUNT = 30
SPAWN_CHANCE = 0.34
DESPAWN_TIME = 300  # 5 minutes
