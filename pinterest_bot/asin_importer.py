#!/usr/bin/env python3
"""
Amazon Page Source → Google Sheets Auto-Importer v2
====================================================
NEW in v2:
- Auto-extracts image URLs from page source
- Auto-assigns board_name based on category/keywords
- Fills Column I (image_url) and Column J (board_name)
- No manual image URL work needed
"""

import re
import os
import sys
import json
import argparse
from datetime import datetime

# ─── BOARD ROUTING RULES ──────────────────────────────────────────────────────
# Order matters — first match wins
BOARD_ROUTING = [
    {
        "board": "Jewelry Aesthetic",
        "keywords": ["jewelry", "jewellery", "necklace", "earring",
                     "bracelet", "bangle", "ring", "pendant", "chain",
                     "maang tikka", "jhumka", "choker", "haar"]
    },
    {
        "board": "Saree Look Ideas",
        "keywords": ["saree", "sari", "chanderi", "banarasi", "kanjivaram",
                     "silk saree", "cotton saree", "georgette saree",
                     "chiffon saree", "printed saree", "embroidered saree",
                     "blouse", "saree blouse"]
    },
    {
        "board": "Ethnic Outfits",
        "keywords": ["kurti", "kurta", "lehenga", "salwar", "anarkali",
                     "sharara", "palazzo", "churidar", "dupatta",
                     "ethnic", "indo western", "festive wear",
                     "traditional", "embroidered", "printed kurti"]
    },
    {
        "board": "Daily Wear Outfit Ideas",
        "keywords": ["shirt", "top", "co-ord", "coord set", "nighty",
                     "casual", "dress", "tshirt", "t-shirt", "jeans",
                     "shorts", "nightwear", "loungewear", "everyday",
                     "comfortable", "western wear", "cotton top"]
    },
    {
        "board": "Under \u20b9999 Fashion",
        "price_keywords": ["under 999", "under 500", "under 799",
                           "budget", "affordable", "value"],
        "price_threshold": 999,  # will try to extract price from title
        "keywords": []  # fallback only — price logic takes priority
    },
    {
        "board": "Fashion",
        "keywords": ["fashion", "women", "men", "shoes", "footwear",
                     "bag", "handbag", "luggage", "accessories",
                     "clothing", "apparel", "wear"],
        "default": True  # catches everything else
    }
]

# ─── CATEGORY RULES ───────────────────────────────────────────────────────────
CATEGORY_RULES = [
    (['saree', 'sari', 'chanderi', 'banarasi', 'dupatta'],
     'fashion', 'sarees'),
    (['kurti', 'kurta', 'lehenga', 'salwar', 'anarkali', 'sharara',
      'palazzo', 'ethnic'],
     'fashion', 'ethnic_wear'),
    (['jewelry', 'jewellery', 'necklace', 'earring', 'bracelet',
      'bangle', 'ring', 'jhumka'],
     'fashion', 'jewelry'),
    (['shoes', 'sandals', 'heels', 'sneakers', 'footwear', 'loafers'],
     'fashion', 'footwear'),
    (['bag', 'handbag', 'luggage', 'suitcase', 'backpack', 'trolley'],
     'fashion', 'bags'),
    (['shirt', 'tshirt', 't-shirt', 'top', 'dress', 'nighty',
      'co-ord', 'jeans', 'shorts', 'jacket'],
     'fashion', 'clothing'),
    (['face pack', 'skincare', 'serum', 'moisturizer', 'sunscreen',
      'makeup', 'lipstick', 'foundation', 'moringa', 'multani'],
     'skincare', 'beauty_care'),
]

AFFILIATE_TAG = os.environ.get('AMAZON_AFFILIATE_TAG', 'pulras0631-21')


# ─── IMAGE URL EXTRACTOR ──────────────────────────────────────────────────────
def extract_image_for_asin(html_content, asin):
    """Try multiple patterns to find the best image URL for an ASIN."""

    image_url = ''

    # Pattern 1: data-csa-c-item-id near src image (deals grid)
    p1 = re.compile(
        rf'amzn1\.asin\.{asin}[^"]*"[^>]*>.*?'
        rf'<img[^>]*src="(https://m\.media-amazon\.com/images/I/[^"]+)"',
        re.IGNORECASE | re.DOTALL
    )
    m = p1.search(html_content[:300000])
    if m:
        image_url = m.group(1)

    # Pattern 2: /dp/ASIN followed by image src nearby
    if not image_url:
        p2 = re.compile(
            rf'/dp/{asin}[^"]*"[^>]*>.*?'
            rf'src="(https://m\.media-amazon\.com/images/I/[^"]+)"',
            re.IGNORECASE | re.DOTALL
        )
        m = p2.search(html_content[:300000])
        if m:
            image_url = m.group(1)

    # Pattern 3: data-asin attribute near image
    if not image_url:
        p3 = re.compile(
            rf'data-asin="{asin}"[^>]*>.*?'
            rf'src="(https://m\.media-amazon\.com/images/I/[^"]+)"',
            re.IGNORECASE | re.DOTALL
        )
        m = p3.search(html_content[:300000])
        if m:
            image_url = m.group(1)

    # Pattern 4: JSON blob with ASIN and hiRes/large image
    if not image_url:
        p4 = re.compile(
            rf'"{asin}".*?"(https://m\.media-amazon\.com/images/I/[^"]+)"',
            re.IGNORECASE | re.DOTALL
        )
        m = p4.search(html_content[:200000])
        if m:
            image_url = m.group(1)

    # Clean up image URL — get highest quality version
    if image_url:
        # Remove size constraints to get full quality image
        image_url = re.sub(r'\._[A-Z]{2}_[^.]*\.', '.', image_url)
        # Ensure it ends with image extension
        if not image_url.endswith(('.jpg', '.png', '.jpeg')):
            image_url = image_url.split('.jpg')[0] + '.jpg'

    return image_url


# ─── TITLE EXTRACTOR ──────────────────────────────────────────────────────────
def extract_title_for_asin(html_content, asin):
    """Extract product title for a given ASIN."""
    title = ''

    # Pattern 1: alt text near product link
    p1 = re.compile(
        rf'/dp/{asin}[^"]*"[^>]*alt="([^"]{10,150})"',
        re.IGNORECASE
    )
    m = p1.search(html_content)
    if m:
        title = m.group(1).strip()

    # Pattern 2: title attribute
    if not title:
        p2 = re.compile(
            rf'/dp/{asin}[^"]*"[^>]*title="([^"]{10,150})"',
            re.IGNORECASE
        )
        m = p2.search(html_content)
        if m:
            title = m.group(1).strip()

    # Pattern 3: JSON "title" field near ASIN
    if not title:
        p3 = re.compile(
            rf'"{asin}".*?"title"\s*:\s*"([^"]{10,150})"',
            re.IGNORECASE | re.DOTALL
        )
        m = p3.search(html_content[:300000])
        if m:
            title = m.group(1).strip()

    return title[:100] if title else ''


# ─── ASIN EXTRACTOR ───────────────────────────────────────────────────────────
def extract_asins_from_html(html_content):
    """Extract all ASINs from Amazon page source."""
    asins = set()

    patterns = [
        re.compile(r'data-csa-c-item-id="amzn1\.asin\.([A-Z0-9]{10})',
                   re.IGNORECASE),
        re.compile(r'data-asin="([B][A-Z0-9]{9})"', re.IGNORECASE),
        re.compile(r'/dp/([B][A-Z0-9]{9})(?:/|\?|")', re.IGNORECASE),
        re.compile(r'"ASIN"\s*:\s*"([B][A-Z0-9]{9})"', re.IGNORECASE),
    ]

    for pattern in patterns:
        for match in pattern.finditer(html_content):
            asin = match.group(1).upper()
            if len(asin) == 10:
                asins.add(asin)

    return list(asins)


# ─── PRICE EXTRACTOR ──────────────────────────────────────────────────────────
def extract_price_from_title(title):
    """Try to extract price from product title."""
    # Look for patterns like ₹588, Rs.999, 588/-
    patterns = [
        r'₹\s*(\d+)',
        r'Rs\.?\s*(\d+)',
        r'(\d+)\s*/-',
        r'(\d+)\s*rupees',
    ]
    for p in patterns:
        m = re.search(p, title, re.IGNORECASE)
        if m:
            return int(m.group(1))
    return None


# ─── BOARD ROUTER ─────────────────────────────────────────────────────────────
def assign_board(title, category, sub_category, keywords_str):
    """Assign product to the correct Pinterest board."""
    title_lower = title.lower()
    keywords_lower = keywords_str.lower()
    combined = title_lower + ' ' + keywords_lower

    for rule in BOARD_ROUTING:
        # Skip default board for now
        if rule.get('default'):
            continue

        # Check price threshold for Under ₹999 board
        if rule['board'] == 'Under \u20b9999 Fashion':
            price = extract_price_from_title(title)
            if price and price <= 999:
                return rule['board']
            # Also check price keywords
            for kw in rule.get('price_keywords', []):
                if kw in combined:
                    return rule['board']
            continue

        # Check keywords
        for kw in rule.get('keywords', []):
            if kw in combined:
                return rule['board']

    # Default to Fashion
    return 'Fashion'


# ─── CATEGORY DETECTOR ────────────────────────────────────────────────────────
def detect_category(title):
    """Detect category and sub_category from product title."""
    title_lower = title.lower()
    for keywords, category, sub_category in CATEGORY_RULES:
        for kw in keywords:
            if kw in title_lower:
                return category, sub_category
    return 'fashion', 'clothing'


def build_keywords(title):
    """Build comma-separated keywords from title."""
    stopwords = {'and', 'the', 'for', 'with', 'set', 'pack', 'of', 'in',
                 'to', 'by', 'from', 'a', 'an', 'on', 'at', 'is', 'are'}
    words = re.findall(r'[a-zA-Z]{3,}', title.lower())
    words = [w for w in words if w not in stopwords]
    seen, unique = set(), []
    for w in words:
        if w not in seen:
            seen.add(w)
            unique.append(w)
    return ','.join(unique[:5])


# ─── GOOGLE SHEETS ────────────────────────────────────────────────────────────
def get_existing_asins(sheet_id, creds_json):
    """Fetch existing ASINs from Google Sheet."""
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
        existing = worksheet.col_values(1)
        existing_set = set(
            v.strip().upper() for v in existing[1:] if v.strip())
        print(f'📋 Found {len(existing_set)} existing ASINs in sheet')
        return existing_set, worksheet
    except ImportError:
        print('⚠️  Run: pip install gspread google-auth')
        return set(), None
    except Exception as e:
        print(f'❌ Google Sheets error: {e}')
        return set(), None


def append_to_sheet(worksheet, rows):
    """Append new rows to Google Sheet."""
    try:
        worksheet.append_rows(rows)
        print(f'✅ Added {len(rows)} new products to Google Sheet')
        return True
    except Exception as e:
        print(f'❌ Failed to append: {e}')
        return False


# ─── MAIN ─────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description='Amazon Page Source → Google Sheets Importer v2'
    )
    parser.add_argument('--source', required=True,
                        help='Path to Amazon page source HTML')
    parser.add_argument('--sheet-id',
                        default=os.environ.get('GOOGLE_SHEET_ID', ''))
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--tag', default=AFFILIATE_TAG)
    args = parser.parse_args()

    print('=' * 60)
    print('🤖 AMAZON IMPORTER v2 — with Image URLs + Board Routing')
    print(f'   Source: {args.source}')
    print(f'   Dry run: {args.dry_run}')
    print('=' * 60)

    # Read source
    try:
        with open(args.source, 'r', encoding='utf-8', errors='ignore') as f:
            html = f.read()
        print(f'📄 Read {len(html):,} characters')
    except FileNotFoundError:
        print(f'❌ File not found: {args.source}')
        sys.exit(1)

    # Extract ASINs
    print('\n🔍 Extracting ASINs...')
    asins = extract_asins_from_html(html)
    print(f'   Found {len(asins)} unique ASINs')

    if not asins:
        print('⚠️  No ASINs found. Is this a valid Amazon page source?')
        sys.exit(1)

    # Get existing ASINs
    existing_asins = set()
    worksheet = None
    if not args.dry_run and args.sheet_id:
        creds_json = os.environ.get('GOOGLE_SHEETS_CREDENTIALS', '')
        if creds_json:
            existing_asins, worksheet = get_existing_asins(
                args.sheet_id, creds_json)

    # Process each ASIN
    print('\n🔄 Processing products...')
    new_products = []
    skipped = 0
    no_image = 0

    for asin in asins:
        if asin in existing_asins:
            skipped += 1
            continue

        # Extract title and image
        title = extract_title_for_asin(html, asin)
        image_url = extract_image_for_asin(html, asin)

        if not title:
            title = f'Amazon Fashion Product {asin}'

        if not image_url:
            no_image += 1

        # Detect category
        category, sub_category = detect_category(title)
        keywords = build_keywords(title)

        # Assign board
        board_name = assign_board(title, category, sub_category, keywords)

        product = {
            'asin': asin,
            'product_title': title,
            'category': category,
            'sub_category': sub_category,
            'keywords': keywords,
            'posted': 'NO',
            'last_posted': '',
            'pin_id': '',
            'image_url': image_url,
            'board_name': board_name
        }
        new_products.append(product)

    # Summary
    print(f'\n📊 RESULTS')
    print(f'   Total ASINs found:    {len(asins)}')
    print(f'   Duplicates skipped:   {skipped}')
    print(f'   New products:         {len(new_products)}')
    print(f'   Missing image URL:    {no_image}')

    if not new_products:
        print('\n✅ No new products — all already in sheet!')
        return

    # Board breakdown
    from collections import Counter
    boards = Counter(p['board_name'] for p in new_products)
    print('\n   By board:')
    for board, count in sorted(boards.items()):
        imgs = sum(1 for p in new_products
                   if p['board_name'] == board and p['image_url'])
        print(f'     {board:<30} {count} products '
              f'({imgs} with images)')

    # Preview
    print('\n📋 Preview (first 5):')
    for p in new_products[:5]:
        img = '✅' if p['image_url'] else '❌'
        print(f'   {p["asin"]} | {p["board_name"]:<25} | '
              f'img:{img} | {p["product_title"][:40]}')

    if args.dry_run:
        print('\n🧪 DRY RUN — nothing written')
        return

    # Write to sheet
    if worksheet:
        print('\n📝 Writing to Google Sheet...')
        rows = [
            [p['asin'], p['product_title'], p['category'],
             p['sub_category'], p['keywords'], p['posted'],
             p['last_posted'], p['pin_id'], p['image_url'],
             p['board_name']]
            for p in new_products
        ]
        append_to_sheet(worksheet, rows)

    print('\n✅ IMPORT COMPLETE!')
    print('=' * 60)


if __name__ == '__main__':
    main()
