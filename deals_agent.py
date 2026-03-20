#!/usr/bin/env python3
"""
Deal Hunter Agent v5 - 4 Posts Daily
9 AM  - Morning Deals + Curator Picks
1 PM  - Lunch Break Tech Deals
5 PM  - Evening Fashion & Beauty Deals
9 PM  - Night Home & Essentials Deals

Run with time slot argument:
    python deals_agent.py morning
    python deals_agent.py afternoon
    python deals_agent.py evening
    python deals_agent.py night
"""

import os
import sys
import json
import time
import logging
import requests
from datetime import datetime, date
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# --- CONFIG -------------------------------------------------------------------
TELEGRAM_BOT_TOKEN   = os.getenv("TELEGRAM_BOT_TOKEN",   "YOUR_TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID     = os.getenv("TELEGRAM_CHAT_ID",     "@your_channel")
AMAZON_AFFILIATE_TAG = os.getenv("AMAZON_AFFILIATE_TAG", "pulras0631-21")

TELEGRAM_URL  = "https://api.telegram.org/bot" + TELEGRAM_BOT_TOKEN + "/sendMessage"
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
#  ESCAPE HELPER - escapes ALL Telegram MarkdownV2 special characters
# ==============================================================================

def e(text):
    """Escape all Telegram MarkdownV2 special characters."""
    text = str(text)
    for ch in ["\\", "_", "*", "[", "]", "(", ")", "~", "`", ">",
               "#", "+", "-", "=", "|", "{", "}", ".", "!"]:
        text = text.replace(ch, "\\" + ch)
    return text


# ==============================================================================
#  YOUR PRODUCTS - shown in morning post only
# ==============================================================================

MY_PRODUCTS = [
    {
        "id":             "MY-AMZ-001",
        "title":          "Moringa Face Pack 100g - Radiant Skin Naturally",
        "original_price": 299,
        "deal_price":     159,
        "discount_pct":   47,
        "emoji":          "🌿",
        "url":            "https://amzn.in/d/0fnLd5iF",
        "why":            "Power of miracle tree Moringa - get radiant skin naturally",
    },
    {
        "id":             "MY-AMZ-002",
        "title":          "Fullers Earth Multani Mitti - Reduces Acne and Blemishes",
        "original_price": 129,
        "deal_price":     69,
        "discount_pct":   46,
        "emoji":          "✨",
        "url":            "https://www.amazon.in/dp/B0FPBR8MNH",
        "why":            "Reduce acne and blemishes naturally - pure Multani Mitti",
    },
]


# ==============================================================================
#  4 TIME SLOT CONFIGURATIONS
#  Note: greeting/subheading/footer are plain text - escaped later via e()
# ==============================================================================

SLOTS = {
    "morning": {
        "greeting":      "GOOD MORNING DEAL HUNTERS",
        "emoji_header":  "sunrise",
        "subheading":    "Start your day with the HOTTEST deals",
        "footer_lines":  [
            "Kick off your morning with savings",
            "Share with friends and family",
            "Stay tuned for Lunch Deals at 1 PM",
        ],
        "show_products": True,
        "categories": [
            {"emoji": "🔥", "label": "Deal of the Day",     "url": "https://amzn.to/4sVtLD5"},
            {"emoji": "⚡", "label": "Lightning Deals",     "url": "https://amzn.to/40HoxyD"},
            {"emoji": "🤑", "label": "Crazy Deals",         "url": "https://amzn.to/4bkvkV5"},
            {"emoji": "📈", "label": "Trending Today",      "url": "https://amzn.to/4sqwaWs"},
            {"emoji": "🏷",  "label": "Coupons and Offers", "url": "https://amzn.to/4cXL81g"},
        ],
    },
    "afternoon": {
        "greeting":      "LUNCH BREAK DEALS",
        "emoji_header":  "afternoon",
        "subheading":    "Best tech deals to browse over lunch",
        "footer_lines":  [
            "Perfect lunch break shopping",
            "Share with your tech-loving friends",
            "Evening Fashion Deals at 5 PM",
        ],
        "show_products": False,
        "categories": [
            {"emoji": "📲", "label": "Smart Phones",           "url": "https://amzn.to/4uE0gqR"},
            {"emoji": "📱", "label": "Electronics",            "url": "https://amzn.to/3PgKi61"},
            {"emoji": "🎧", "label": "Headphones & Speakers",  "url": "https://amzn.to/4t0zzv7"},
            {"emoji": "🔌", "label": "Electronic Accessories", "url": "https://amzn.to/4d2XcOZ"},
            {"emoji": "🎮", "label": "Video Games",            "url": "https://amzn.to/4sjj0KF"},
        ],
    },
    "evening": {
        "greeting":      "EVENING TREAT YOURSELF DEALS",
        "emoji_header":  "evening",
        "subheading":    "You worked hard today - now save big",
        "footer_lines":  [
            "Treat yourself tonight",
            "Share with friends who love fashion and beauty",
            "Night Home Deals at 9 PM",
        ],
        "show_products": False,
        "categories": [
            {"emoji": "👗", "label": "Clothing",                  "url": "https://amzn.to/4uBRqdc"},
            {"emoji": "👟", "label": "Footwear",                  "url": "https://amzn.to/3PNnL0E"},
            {"emoji": "💄", "label": "Beauty",                    "url": "https://amzn.to/4bRxj3j"},
            {"emoji": "💊", "label": "Wellness",                  "url": "https://amzn.to/4bxo1bt"},
            {"emoji": "💍", "label": "Jewellery Luggage Watches", "url": "https://amzn.to/4lzvICw"},
            {"emoji": "🏋", "label": "Sports and Fitness",        "url": "https://amzn.to/4uLDiOT"},
        ],
    },
    "night": {
        "greeting":      "NIGHT SHOPPING DEALS",
        "emoji_header":  "night",
        "subheading":    "Best time to shop for home and family",
        "footer_lines":  [
            "Shop for your home and loved ones",
            "Share with family",
            "See you tomorrow at 9 AM for fresh deals",
        ],
        "show_products": False,
        "categories": [
            {"emoji": "🏠", "label": "Home and Kitchen",     "url": "https://amzn.to/4ssBmt6"},
            {"emoji": "🧺", "label": "Large Appliances",     "url": "https://amzn.to/4sUCCVo"},
            {"emoji": "🏥", "label": "Health and Household", "url": "https://amzn.to/4bB3WkM"},
            {"emoji": "🛒", "label": "Daily Essentials",     "url": "https://amzn.to/4lH4ZnV"},
            {"emoji": "🛒", "label": "Grocery",              "url": "https://amzn.to/4rGaaWo"},
            {"emoji": "👶", "label": "Kids and Baby",        "url": "https://amzn.to/4sTzCsv"},
            {"emoji": "🐾", "label": "Pet Supplies",         "url": "https://amzn.to/4soMhUy"},
            {"emoji": "💊", "label": "Wellness",             "url": "https://amzn.to/4bxo1bt"},
        ],
    },
}

HEADER_EMOJIS = {
    "sunrise":   "☀️",
    "afternoon": "🌤️",
    "evening":   "🌆",
    "night":     "🌙",
}


# ==============================================================================
#  ROTATION
# ==============================================================================

def get_todays_products():
    today = str(date.today())
    state = {}
    if ROTATION_FILE.exists():
        state = json.loads(ROTATION_FILE.read_text())
    if state.get("date") == today:
        ids    = state.get("featured_ids", [])
        result = [p for p in MY_PRODUCTS if p["id"] in ids]
        if result:
            return result
    last_index = state.get("last_index", -1)
    total      = len(MY_PRODUCTS)
    idx1       = (last_index + 1) % total
    idx2       = (last_index + 2) % total
    featured   = [MY_PRODUCTS[idx1], MY_PRODUCTS[idx2]]
    ROTATION_FILE.write_text(json.dumps({
        "date":         today,
        "last_index":   idx2,
        "featured_ids": [p["id"] for p in featured],
    }, indent=2))
    return featured


# ==============================================================================
#  FORMAT TELEGRAM MESSAGES
# ==============================================================================

def format_messages(slot_name):
    slot     = SLOTS[slot_name]
    date_str = datetime.now().strftime("%A, %d %B %Y")
    hdr_emo  = HEADER_EMOJIS[slot["emoji_header"]]
    messages = []

    # ── CURATOR PICKS (morning only) ──────────────────────────────────────────
    if slot["show_products"]:
        own = get_todays_products()
        m   = "🌿 *CURATOR PICKS \\- VERIFIED QUALITY* 🌿\n"
        m  += "📅 " + e(date_str) + "\n"
        m  += "━━━━━━━━━━━━━━━━━━━━\n"
        m  += "_Handpicked by our team \\- guaranteed quality_\n\n"
        for i, p in enumerate(own, 1):
            saving = int(p["original_price"]) - int(p["deal_price"])
            m += p["emoji"] + " *" + str(i) + "\\. " + e(p["title"]) + "*\n"
            m += "💸 ~" + e("Rs " + str(int(p["original_price"]))) + "~ \\-\\> *" + e("Rs " + str(int(p["deal_price"]))) + "*\n"
            m += "🔥 *" + e(str(p["discount_pct"]) + "% OFF") + "* \\| Save " + e("Rs " + str(saving)) + "\n"
            m += "✨ " + e(p["why"]) + "\n"
            m += "🔗 [Shop Now](" + p["url"] + ")\n\n"
        m += "━━━━━━━━━━━━━━━━━━━━\n"
        m += "👇 _Scroll down for today's deals_ 👇"
        messages.append(m)

    # ── MAIN DEALS MESSAGE ────────────────────────────────────────────────────
    m  = hdr_emo + " *" + e(slot["greeting"]) + "* " + hdr_emo + "\n"
    m += "📅 " + e(date_str) + "\n"
    m += e(slot["subheading"]) + "\n"
    m += "━━━━━━━━━━━━━━━━━━━━\n"
    m += "👇 *TAP YOUR CATEGORY FOR DEALS* 👇\n\n"

    for cat in slot["categories"]:
        m += cat["emoji"] + " [" + e(cat["label"]) + "](" + cat["url"] + ")\n"

    m += "\n━━━━━━━━━━━━━━━━━━━━\n"
    for line in slot["footer_lines"]:
        m += "✅ _" + e(line) + "_\n"
    m += "\n🛍 _Affiliate links \\- Share it with other deal hunters <Sharing is Saving>\\. Thanks_ 🙏"

    messages.append(m)
    return messages


# ==============================================================================
#  SAVE WHATSAPP FILE
# ==============================================================================

def save_whatsapp_file(slot_name):
    slot     = SLOTS[slot_name]
    date_str = datetime.now().strftime("%A, %d %B %Y")
    hdr_emo  = HEADER_EMOJIS[slot["emoji_header"]]
    wa_file  = Path("whatsapp_" + slot_name + ".txt")

    content  = hdr_emo + " " + slot["greeting"] + " " + hdr_emo + "\n"
    content += "📅 " + date_str + "\n"
    content += slot["subheading"] + "\n"
    content += "━━━━━━━━━━━━━━━━━━━━\n\n"

    if slot["show_products"]:
        own = get_todays_products()
        content += "🌿 CURATOR PICKS - VERIFIED QUALITY\n"
        content += "━━━━━━━━━━━━━━━━━━━━\n"
        for i, p in enumerate(own, 1):
            saving   = int(p["original_price"]) - int(p["deal_price"])
            content += p["emoji"] + " " + str(i) + ". " + p["title"] + "\n"
            content += "Rs " + str(int(p["original_price"])) + " -> Rs " + str(int(p["deal_price"])) + "\n"
            content += str(p["discount_pct"]) + "% OFF | Save Rs " + str(saving) + "\n"
            content += p["url"] + "\n\n"
        content += "━━━━━━━━━━━━━━━━━━━━\n\n"

    content += "👇 TAP YOUR CATEGORY FOR DEALS 👇\n\n"
    for cat in slot["categories"]:
        content += cat["emoji"] + " " + cat["label"] + "\n"
        content += cat["url"] + "\n\n"

    content += "━━━━━━━━━━━━━━━━━━━━\n"
    for line in slot["footer_lines"]:
        content += "✅ " + line + "\n"
    content += "\nAffiliate links - Share it with other deal hunters <Sharing is Saving>. Thanks 🙏"

    with open(wa_file, "w", encoding="utf-8") as f:
        f.write(content)
    log.info("WhatsApp file saved: " + str(wa_file))


# ==============================================================================
#  POST TO TELEGRAM
# ==============================================================================

def post_to_telegram(messages):
    for idx, text in enumerate(messages, 1):
        log.info("Posting message " + str(idx) + "/" + str(len(messages)) + " ...")
        payload = {
            "chat_id":               TELEGRAM_CHAT_ID,
            "text":                  text,
            "parse_mode":            "MarkdownV2",
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

def run_agent(slot_name):
    log.info("=== Deal Hunter Agent v5 - " + slot_name.upper() + " slot ===")
    try:
        messages = format_messages(slot_name)
        post_to_telegram(messages)
        save_whatsapp_file(slot_name)
        log.info("=== Done - " + slot_name + " post complete ===")
    except Exception as exc:
        log.error("Agent failed: " + str(exc), exc_info=True)
        raise


if __name__ == "__main__":
    valid_slots = ["morning", "afternoon", "evening", "night"]
    if len(sys.argv) < 2 or sys.argv[1] not in valid_slots:
        print("Usage: python deals_agent.py [morning|afternoon|evening|night]")
        print("Example: python deals_agent.py morning")
        sys.exit(1)
    run_agent(sys.argv[1])
