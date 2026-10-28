
import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env", override=True)

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_IDS = [5874210682, 1845339377]
MODERATION_GROUP_ID = -1004425653871
PUBLISH_CHANNEL_ID = os.getenv("PUBLISH_CHANNEL_ID") or "@Podslushano_ZIEIT"
IBAN = "UA673220010000026204363828571"
PAYMENT_RECIPIENT = "Линь Жу Янь"

PIN_OPTIONS = {
    "pin_6": (6, 20, 20),
    "pin_12": (12, 40, 40),
    "pin_24": (24, 50, 50),
}
