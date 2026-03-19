#!/usr/bin/env python3
"""
Deal Hunter Agent v3 - Amazon Loot for the Day -> Telegram
Format: Daily category directory + Your 2 Curator Pick products at top
All 23 affiliate links verified clean - no duplicates
"""

import os
import json
import time
import logging
import requests
from datetime import datetime, date
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# --- CONFIG -------------------------------------------------------------------
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "YOUR_TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID   = os.getenv("TELEGRAM_CHAT_ID",   "@your_channel")

TELEGRAM_URL = "https://api.telegram.org/bot" + TELEGRAM_BOT_TOKEN + "/sendMessage"

ROTATION_FILE = Path("rotation_state.json")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)s  %(message)s",
    handlers=[
        logging.FileHandler("deal_agent.log"),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger(__name__)


# ==============================================================================
#  YOUR 2 PRODUCTS — shown at top of every post as Curator Picks
# ==============================================================================

MY_PRODUCTS = [
    {
        "id": "MY-AMZ-001",
        "title": "Moringa Face Pack 100g - Radiant Skin Naturally",
        "original_price": 299,
        "deal_price": 159,
        "discount_pct": 47,
        "emoji": "🌿",
        "url": "https://amzn.in/d/0fnLd5iF",
        "why": "Power of miracle tree Moringa - get radiant skin naturally",
    },
    {
        "id": "MY-AMZ-002",
        "title": "Fullers Earth Multani Mitti - Reduces Acne & Blemishes",
        "original_price": 129,
        "deal_price": 69,
        "discount_pct": 46,
        "emoji": "✨",
        "url": "https://www.amazon.in/dp/B0FPBR8MNH",
        "why": "Reduce acne and blemishes naturally - pure Multani Mitti",
    },
]


# ==============================================================================
#  YOUR 23 VERIFIED AFFILIATE LINKS — checked clean, zero duplicates
# ==============================================================================

DEAL_CATEGORIES = [
    {"emoji": "🔥", "label": "Deal of the Day",          "url": "https://amzn.to/4sVtLD5"},
    {"emoji": "🤑", "label": "Crazy Deals",              "url": "https://amzn.to/4bkvkV5"},
    {"emoji": "⚡", "label": "Lightning Deals",          "url": "https://amzn.to/40HoxyD"},
    {"emoji": "📈", "label": "Trending",                 "url": "https://amzn.to/4sqwaWs"},
    {"emoji": "💊", "label": "Wellness",                 "url": "https://amzn.to/4bxo1bt"},
    {"emoji": "💄", "label": "Beauty",                   "url": "https://amzn.to/4bRxj3j"},
    {"emoji": "📱", "label": "Electronics",              "url": "https://amzn.to/3PgKi61"},
    {"emoji": "🔌", "label": "Electronic Accessories",   "url": "https://amzn.to/4d2XcOZ"},
    {"emoji": "🏠", "label": "Home & Kitchen",           "url": "https://amzn.to/4ssBmt6"},
    {"emoji": "🎧", "label": "Headphones & Speakers",    "url": "https://amzn.to/4t0zzv7"},
    {"emoji": "🛒", "label": "Daily Essentials",         "url": "https://amzn.to/4lH4ZnV"},
    {"emoji": "📲", "label": "Smart Phones",             "url": "https://amzn.to/4uE0gqR"},
    {"emoji": "💍", "label": "Jewellery, Luggage & Watches", "url": "https://amzn.to/4lzvICw"},
    {"emoji": "🏷️", "label": "Coupons",                 "url": "https://amzn.to/4cXL81g"},
    {"emoji": "🧺", "label": "Large Appliances",         "url": "https://amzn.to/4sUCCVo"},
    {"emoji": "🏥", "label": "Health & Households",      "url": "https://amzn.to/4bB3WkM"},
    {"emoji": "👗", "label": "Clothing",                 "url": "https://amzn.to/4uBRqdc"},
    {"emoji": "👟", "label": "Footwear",                 "url": "https://amzn.to/3PNnL0E"},
    {"emoji": "👶", "label": "Kids & Baby",              "url": "https://amzn.to/4sTzCsv"},
    {"emoji": "🛒", "label": "Grocery",                  "url": "https://amzn.to/4rGaaWo"},
    {"emoji": "🏋️", "label": "Sports & Fitness",        "url": "https://amzn.to/4uLDiOT"},
    {"emoji": "🎮", "label": "Video Games",              "url": "https://amzn.to/4sjj0KF"},
    {"emoji": "🐾", "label": "Pet Supplies",             "url": "https://amzn.to/4soMhUy"},
]


# ==============================================================================
#  ROTATION — cycles your 2 products daily
# ==============================================================================

def get_todays_products():
    today = str(date.today())
    state = {}
    if ROTATION_FILE.exists():
        state = json.loads(ROTATION_FILE.read_text())
    if state.get("date") == today:
        ids = state.get("featured_ids", [])
        result = [p for p in MY_PRODUCTS if p["id"] in ids]
        if result:
            return result
    last_index = state.get("last_index", -1)
    total = len(MY_PRODUCTS)
    idx1 = (last_index + 1) % total
    idx2 = (last_index + 2) % total
    featured = [MY_PRODUCTS[idx1], MY_PRODUCTS[idx2]]
    ROTATION_FILE.write_text(json.dumps({
        "date": today,
        "last_index": idx2,
        "featured_ids": [p["id"] for p in featured],
    }, indent=2))
    log.info("Today's featured: " + str([p["title"] for p in featured]))
    return featured


# ==============================================================================
#  FORMAT TELEGRAM MESSAGES
#  Message 1 — Curator Picks (your products)
#  Message 2 — Amazon Loot for the Day (all 23 categories)
# ==============================================================================

def escape_md(text):
    text = str(text)
    for ch in ["_", "*", "[", "]", "(", ")", "~", "`", ">", "#", "+", "-", "=", "|", "{", "}", ".", "!"]:
        text = text.replace(ch, "\\" + ch)
    return text


def format_messages(own_products):
    date_str  = datetime.now().strftime("%A, %d %B %Y")
    day_emoji = ["🌞","🌝","🌟","💫","⭐","🌈","🎯"][datetime.now().weekday()]
    messages  = []

    # ── MESSAGE 1: YOUR PRODUCTS ───────────────────────────────────────────────
    msg1 = (
        "🌿 *CURATOR PICKS \\- VERIFIED QUALITY* 🌿\n"
        "📅 " + escape_md(date_str) + "\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "_Our own products \\- handpicked quality guaranteed_\n\n"
    )
    for i, p in enumerate(own_products, 1):
        saving = int(p["original_price"]) - int(p["deal_price"])
        op   = escape_md("Rs " + str(int(p["original_price"])))
        dp   = escape_md("Rs " + str(int(p["deal_price"])))
        sav  = escape_md("Rs " + str(saving))
        ttl  = escape_md(p["title"])
        why  = escape_md(p["why"])
        disc = str(p["discount_pct"])
        url  = p["url"]
        msg1 += p["emoji"] + " *" + str(i) + "\\. " + ttl + "*\n"
        msg1 += "💸 ~" + op + "~ \\-\\> *" + dp + "*\n"
        msg1 += "🔥 *" + disc + "% OFF* \\| Save " + sav + "\n"
        msg1 += "✨ " + why + "\n"
        msg1 += "🔗 [Shop Now](" + url + ")\n\n"
    msg1 += (
        "━━━━━━━━━━━━━━━━━━━━\n"
        "👇 _Scroll down for today's Amazon Loot_ 👇"
    )
    messages.append(msg1)

    # ── MESSAGE 2: AMAZON LOOT DIRECTORY ──────────────────────────────────────
    msg2 = (
        day_emoji + " *AMAZON LOOT FOR THE DAY* " + day_emoji + "\n"
        "📅 " + escape_md(date_str) + "\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "👇 *TAP YOUR CATEGORY TO SEE DEALS* 👇\n\n"
    )
    for cat in DEAL_CATEGORIES:
        label = escape_md(cat["label"])
        url   = cat["url"]
        msg2 += cat["emoji"] + " [" + label + "](" + url + ")\n"

    msg2 += (
        "\n━━━━━━━━━━━━━━━━━━━━\n"
        "⚡ _All links updated daily \\- prices change fast\\!_\n"
        "📲 _Share with friends & family_\n"
        "🔔 _Follow for daily deal alerts_\n\n"
        "🛍 _All links are affiliate links \\- "
        "you pay same price, we earn a small commission\\. "
        "Thank you for supporting us\\!_ 🙏"
    )
    messages.append(msg2)

    return messages


# ==============================================================================
#  TELEGRAM POSTING
# ==============================================================================

def post_to_telegram(messages):
    for idx, text in enumerate(messages, 1):
        log.info("Posting message " + str(idx) + "/" + str(len(messages)) + " ...")
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": text,
            "parse_mode": "MarkdownV2",
            "disable_web_page_preview": False,
        }
        resp   = requests.post(TELEGRAM_URL, json=payload, timeout=30)
        result = resp.json()
        if not result.get("ok"):
            raise RuntimeError("Telegram error: " + str(result.get("description")))
        log.info("Message " + str(idx) + " posted OK")
        time.sleep(1.5)


# ==============================================================================
#  MAIN
# ==============================================================================

def run_agent():
    log.info("=== Deal Hunter Agent v3 starting ===")
    try:
        own_products = get_todays_products()
        messages     = format_messages(own_products)
        post_to_telegram(messages)
        log.info("=== Done - 2 messages posted ===")
    except Exception as exc:
        log.error("Agent failed: " + str(exc), exc_info=True)
        raise


if __name__ == "__main__":
    run_agent()
