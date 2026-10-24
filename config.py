import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')
ADMIN_IDS = [5874210682, 1845339377]
MODERATION_GROUP_ID = -1004425653871