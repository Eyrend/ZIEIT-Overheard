import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')
ADMIN_IDS = [5874210682, 1845339377]
MODERATION_GROUP_ID = -1004425653871
IBAN = "UA673220010000026204363828571"
PAYMENT_RECIPIENT = "Линь Жу Янь"

PIN_OPTIONS = {
    "pin_6": (6, 20),
    "pin_12": (12, 40),
    "pin_24": (24, 50),
}