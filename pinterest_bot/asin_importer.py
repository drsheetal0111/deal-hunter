#!/usr/bin/env python3
"""
Amazon Page Source → Google Sheets Auto-Importer v3
====================================================
v3 fixes:
- Better image extraction for bestsellers pages
- Better title extraction for bestsellers pages  
- Improved board routing
"""

import re
import os
import sys
import json
import argparse
from datetime import datetime
from collections import Counter

# ─── BOARD ROUTING RULES ──────────────────────────────────────────────────────
BOARD_ROUTING = [
    {
        "board": "Jewelry Aesthetic",
        "keywords": ["jewelry", "jewellery", "necklace", "earring",
                     "bracelet", "bangle", "ring", "pendant", "chain",
                     "maang tikka", "jhumka", "choker", "haar", "kundan",
                     "oxidised", "gold plated", "silver jewel"]
    },
    {
        "board": "Saree Look Ideas",
        "keywords": ["saree", "sari", "chanderi", "banarasi", "kanjivaram",
                     "silk saree", "cotton saree", "georgette saree",
                     "chiffon saree", "printed saree", "woven saree",
                     "blouse", "saree blouse", "patola", "pochampally"]
    },
    {
        "board": "Ethnic Outfits",
        "keywords": ["kurti", "kurta", "lehenga", "salwar", "anarkali",
                     "sharara", "palazzo", "churidar", "dupatta",
                     "ethnic", "indo western", "festive", "traditional",
                     "embroidered", "printed kurti", "phulkari",
                     "mirror work", "block print"]
    },
    {
        "board": "Daily Wear Outfit Ideas",
        "keywords": ["shirt", "top", "co-ord", "coord set", "nighty",
                     "casual", "dress", "tshirt", "t-shirt", "jeans",
                     "shorts", "nightwear", "loungewear", "western",
                     "cotton top", "tank top", "blouse top", "tunic"]
    },
    {
        "board": "Under \u20b9999 Fashion",
        "price_keywords": ["under 999", "under 500", "under 799",
                           "below 999", "budget", "affordable"],
        "price_threshold": 999,
        "keywords": []
    },
    {
        "board": "Fashion",
        "keywords": ["fashion", "women", "men", "shoes", "footwear",
                     "bag", "handbag", "luggage", "accessories",
                     "clothing", "apparel", "wear", "outfit"],
        "default": True
    }
]


# ─── BOARD ID MAPPING ─────────────────────────────────────────────────────────
BOARD_IDS = {
    "Fashion":                 "454722962316119111",
    "Jewelry Aesthetic":       "454722962316119578",
    "Saree Look Ideas":        "454722962316120062",
    "Ethnic Outfits":          "454722962316120063",
    "Under \u20b9999 Fashion": "454722962316120064",
    "Daily Wear Outfit Ideas": "454722962316120065"
}

CATEGORY_RULES = [
    (['saree', 'sari', 'chanderi', 'banarasi', 'dupatta', 'blouse'],
     'fashion', 'sarees'),
    (['kurti', 'kurta', 'lehenga', 'salwar', 'anarkali', 'sharara',
      'palazzo', 'ethnic', 'phulkari'],
     'fashion', 'ethnic_wear'),
    (['jewelry', 'jewellery', 'necklace', 'earring', 'bracelet',
      'bangle', 'ring', 'jhumka', 'kundan'],
     'fashion', 'jewelry'),
    (['shoes', 'sandals', 'heels', 'sneakers', 'footwear', 'loafers'],
     'fashion', 'footwear'),
    (['bag', 'handbag', 'luggage', 'suitcase', 'backpack', 'trolley'],
     'fashion', 'bags'),
    (['shirt', 'tshirt', 't-shirt', 'top', 'dress', 'nighty',
      'co-ord', 'jeans', 'shorts', 'jacket', 'tunic'],
     'fashion', 'clothing'),
]

AFFILIATE_TAG = os.environ.get('AMAZON_AFFILIATE_TAG', 'pulras0631-21')


# ─── IMPROVED EXTRACTOR ───────────────────────────────────────────────────────
def extract_products_from_html(html):
    """
    Extract ASIN + title + image from Amazon bestsellers/search pages.
    Uses multiple strategies optimized for different page types.
    """
    products = {}

    # ── Strategy 1: JSON data blobs (most reliable) ──
    # Amazon embeds product data as JSON in script tags
    json_patterns = [
        # Bestsellers grid data
        re.compile(
            r'"asin"\s*:\s*"([B][A-Z0-9]{9})"'
            r'(?:[^}]{0,500}?"title"\s*:\s*"([^"]{5,150})")?'
            r'(?:[^}]{0,500}?"imageUrl"\s*:\s*"([^"]+)")?',
            re.IGNORECASE | re.DOTALL
        ),
        # Search results data
        re.compile(
            r'"ASIN"\s*:\s*"([B][A-Z0-9]{9})"'
            r'(?:[^}]{0,500}?"title"\s*:\s*"([^"]{5,150})")?'
            r'(?:[^}]{0,500}?"image"\s*:\s*"([^"]+)")?',
            re.IGNORECASE | re.DOTALL
        ),
    ]

    for pattern in json_patterns:
        for m in pattern.finditer(html):
            asin = m.group(1).upper()
            title = m.group(2).strip() if m.group(2) else ''
            image = m.group(3) if m.group(3) else ''
            if asin not in products:
                products[asin] = {'asin': asin, 'title': title, 'image': image}
            else:
                if not products[asin]['title'] and title:
                    products[asin]['title'] = title
                if not products[asin]['image'] and image:
                    products[asin]['image'] = image

    # ── Strategy 2: HTML img tags with data-asin ──
    # <div data-asin="B0XXX"><img src="https://...">
    s2 = re.compile(
        r'data-asin="([B][A-Z0-9]{9})"'
        r'(?:[^>]{0,200}?>|.{0,500}?)<img[^>]*'
        r'src="(https://m\.media-amazon\.com/images/I/[^"]+)"'
        r'(?:[^>]*alt="([^"]{5,150})")?',
        re.IGNORECASE | re.DOTALL
    )
    for m in s2.finditer(html[:500000]):
        asin = m.group(1).upper()
        image = m.group(2)
        title = m.group(3).strip() if m.group(3) else ''
        if asin not in products:
            products[asin] = {'asin': asin, 'title': title, 'image': image}
        else:
            if not products[asin]['image'] and image:
                products[asin]['image'] = image
            if not products[asin]['title'] and title:
                products[asin]['title'] = title

    # ── Strategy 3: /dp/ASIN links with nearby img ──
    s3 = re.compile(
        r'/dp/([B][A-Z0-9]{9})[^"]*"[^>]*>'
        r'(?:.{0,300}?)'
        r'<img[^>]*src="(https://m\.media-amazon\.com/images/I/[^"]+)"'
        r'(?:[^>]*alt="([^"]{5,150})")?',
        re.IGNORECASE | re.DOTALL
    )
    for m in s3.finditer(html[:600000]):
        asin = m.group(1).upper()
        image = m.group(2)
        title = m.group(3).strip() if m.group(3) else ''
        if asin not in products:
            products[asin] = {'asin': asin, 'title': title, 'image': image}
        else:
            if not products[asin]['image'] and image:
                products[asin]['image'] = image
            if not products[asin]['title'] and title:
                products[asin]['title'] = title

    # ── Strategy 4: alt text near ASIN links ──
    s4 = re.compile(
        r'alt="([^"]{10,150})"[^>]*>[^<]*</[^>]+>'
        r'(?:.{0,100}?)/dp/([B][A-Z0-9]{9})',
        re.IGNORECASE | re.DOTALL
    )
    for m in s4.finditer(html[:600000]):
        title = m.group(1).strip()
        asin = m.group(2).upper()
        if asin in products and not products[asin]['title']:
            products[asin]['title'] = title

    # ── Strategy 5: srcset images (bestsellers uses these) ──
    s5 = re.compile(
        r'/dp/([B][A-Z0-9]{9})'
        r'(?:.{0,500}?)'
        r'srcset="(https://m\.media-amazon\.com/images/I/[^"]+)',
        re.IGNORECASE | re.DOTALL
    )
    for m in s5.finditer(html[:600000]):
        asin = m.group(1).upper()
        image = m.group(2).split(' ')[0]  # take first URL from srcset
        if asin in products and not products[asin]['image']:
            products[asin]['image'] = image

    # ── Strategy 6: catch remaining ASINs ──
    all_asin_patterns = [
        re.compile(r'data-asin="([B][A-Z0-9]{9})"', re.IGNORECASE),
        re.compile(r'/dp/([B][A-Z0-9]{9})(?:/|\?|")', re.IGNORECASE),
        re.compile(r'"ASIN"\s*:\s*"([B][A-Z0-9]{9})"', re.IGNORECASE),
    ]
    for pattern in all_asin_patterns:
        for m in pattern.finditer(html):
            asin = m.group(1).upper()
            if len(asin) == 10 and asin not in products:
                products[asin] = {'asin': asin, 'title': '', 'image': ''}

    # ── Clean up image URLs ──
    for asin in products:
        img = products[asin]['image']
        if img:
            # Get clean high-quality URL
            img = img.split('._')[0] + '.jpg' if '._' in img else img
            img = img.replace('\\/', '/')
            products[asin]['image'] = img

    # Fallback: construct image URL from ASIN for any missing images
    for asin in products:
        if not products[asin]['image']:
            products[asin]['image'] = (
                f"https://ws-in.amazon-adsystem.com/widgets/q"
                f"?_encoding=UTF8&ASIN={asin}&Format=_SL250_"
                f"&ID=AsinImage&MarketPlace=IN"
                f"&ServiceVersion=20070822&WS=1"
                f"&tag=pulras0631-21"
            )

    return list(products.values())


# ─── BOARD ROUTER ─────────────────────────────────────────────────────────────
def assign_board(title, keywords_str):
    """Assign product to correct Pinterest board."""
    combined = (title + ' ' + keywords_str).lower()

    for rule in BOARD_ROUTING:
        if rule.get('default'):
            continue

        if rule['board'] == 'Under \u20b9999 Fashion':
            for kw in rule.get('price_keywords', []):
                if kw in combined:
                    return rule['board']
            # Try price extraction
            m = re.search(r'₹\s*(\d+)|rs\.?\s*(\d+)', combined)
            if m:
                price = int(m.group(1) or m.group(2))
                if price <= rule['price_threshold']:
                    return rule['board']
            continue

        for kw in rule.get('keywords', []):
            if kw in combined:
                return rule['board']

    return 'Fashion'


def detect_category(title):
    """Detect category from title."""
    t = title.lower()
    for keywords, category, sub_category in CATEGORY_RULES:
        for kw in keywords:
            if kw in t:
                return category, sub_category
    return 'fashion', 'clothing'


def build_keywords(title):
    """Build keywords from title."""
    stopwords = {'and', 'the', 'for', 'with', 'set', 'pack', 'of',
                 'in', 'to', 'by', 'from', 'a', 'an', 'on', 'at'}
    words = re.findall(r'[a-zA-Z]{3,}', title.lower())
    seen, unique = set(), []
    for w in words:
        if w not in stopwords and w not in seen:
            seen.add(w)
            unique.append(w)
    return ','.join(unique[:5])


# ─── GOOGLE SHEETS ────────────────────────────────────────────────────────────
def get_sheet(sheet_id, creds_json):
    """Connect to Google Sheet."""
    try:
        import gspread
        from google.oauth2.service_account import Credentials
        creds_dict = json.loads(creds_json)
        scopes = ['https://spreadsheets.google.com/feeds',
                  'https://www.googleapis.com/auth/drive']
        creds = Credentials.from_service_account_info(
            creds_dict, scopes=scopes)
        client = gspread.authorize(creds)
        sheet = client.open_by_key(sheet_id)
        worksheet = sheet.worksheet('Sheet1')
        existing = set(
            v.strip().upper()
            for v in worksheet.col_values(1)[1:]
            if v.strip()
        )
        print(f'📋 Found {len(existing)} existing ASINs in sheet')
        return existing, worksheet
    except Exception as e:
        print(f'❌ Sheet error: {e}')
        return set(), None


# ─── MAIN ─────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', required=True)
    parser.add_argument('--sheet-id',
                        default=os.environ.get('GOOGLE_SHEET_ID', ''))
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--tag', default=AFFILIATE_TAG)
    args = parser.parse_args()

    print('=' * 60)
    print('🤖 AMAZON IMPORTER v3 — Bestsellers Optimized')
    print(f'   Source: {args.source}')
    print(f'   Dry run: {args.dry_run}')
    print('=' * 60)

    try:
        with open(args.source, 'r', encoding='utf-8', errors='ignore') as f:
            html = f.read()
        print(f'📄 Read {len(html):,} characters')
    except FileNotFoundError:
        print(f'❌ File not found: {args.source}')
        sys.exit(1)

    print('\n🔍 Extracting products...')
    raw = extract_products_from_html(html)
    print(f'   Found {len(raw)} unique ASINs')

    # Get existing
    existing_asins = set()
    worksheet = None
    if not args.dry_run and args.sheet_id:
        creds = os.environ.get('GOOGLE_SHEETS_CREDENTIALS', '')
        if creds:
            existing_asins, worksheet = get_sheet(args.sheet_id, creds)

    # Process
    new_products = []
    skipped = 0
    no_image = 0
    no_title = 0

    for p in raw:
        asin = p['asin'].upper()
        if asin in existing_asins:
            skipped += 1
            continue

        title = p.get('title', '').strip()
        image = p.get('image', '').strip()

        if not title:
            title = f'Amazon Fashion Product {asin}'
            no_title += 1
        if not image:
            no_image += 1

        category, sub_category = detect_category(title)
        keywords = build_keywords(title)
        board = assign_board(title, keywords)

        board_id = BOARD_IDS.get(board, '454722962316119111')
        new_products.append({
            'asin': asin,
            'product_title': title[:100],
            'category': category,
            'sub_category': sub_category,
            'keywords': keywords,
            'posted': 'NO',
            'last_posted': '',
            'pin_id': '',
            'image_url': image,
            'board_name': board,
            'board_id': board_id
        })

    # Summary
    print(f'\n📊 RESULTS')
    print(f'   Total found:        {len(raw)}')
    print(f'   Duplicates skipped: {skipped}')
    print(f'   New products:       {len(new_products)}')
    print(f'   Missing image:      {no_image}')
    print(f'   Missing title:      {no_title}')

    if not new_products:
        print('\n✅ Nothing new to import!')
        return

    boards = Counter(p['board_name'] for p in new_products)
    print('\n   By board:')
    for board, count in sorted(boards.items()):
        imgs = sum(1 for p in new_products
                   if p['board_name'] == board and p['image_url'])
        print(f'     {board:<32} {count:>3} products  '
              f'({imgs} with images ✅)')

    print('\n📋 Preview (first 5 with images):')
    shown = 0
    for p in new_products:
        if p['image_url'] and shown < 5:
            print(f'   {p["asin"]} | {p["board_name"]:<25} | '
                  f'{p["product_title"][:45]}')
            shown += 1

    if args.dry_run:
        print('\n🧪 DRY RUN — nothing written to sheet')
        return

    if worksheet:
        print('\n📝 Writing to Google Sheet...')
        rows = [[
            p['asin'], p['product_title'], p['category'],
            p['sub_category'], p['keywords'], p['posted'],
            p['last_posted'], p['pin_id'], p['image_url'],
            p['board_name'], p['board_id']
        ] for p in new_products]
        worksheet.append_rows(rows)
        print(f'✅ Added {len(rows)} products to Google Sheet!')
    else:
        print('⚠️  No sheet connection — dry run data only')

    print('=' * 60)


if __name__ == '__main__':
    main()
