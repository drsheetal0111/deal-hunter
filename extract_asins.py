import requests
from bs4 import BeautifulSoup
import json
import time
import os
import sys

# ─── CONFIG ───────────────────────────────────────────────
TEST_MODE = os.environ.get("TEST_MODE", "true").lower() == "true"
MAX_PRODUCTS = 3 if TEST_MODE else 10  # 3 per category in test, 10 in full run

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "en-IN,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

# ─── SEARCH URLS (Amazon India) ───────────────────────────
SEARCH_URLS = {
    "skincare": {
        "url": "https://www.amazon.in/s?k=moringa+face+pack&rh=p_72%3A1318476031",
        "sub_category": "face_packs",
        "keywords": "moringa,face pack,glow,natural skincare"
    },
    "kitchen": {
        "url": "https://www.amazon.in/s?k=stainless+steel+tiffin+box&rh=p_72%3A1318476031",
        "sub_category": "tiffin",
        "keywords": "tiffin,lunchbox,steel,kitchen essentials"
    },
    "health": {
        "url": "https://www.amazon.in/s?k=ayurvedic+health+supplements&rh=p_72%3A1318476031",
        "sub_category": "supplements",
        "keywords": "ayurvedic,health,wellness,immunity,organic"
    },
    "fashion": {
        "url": "https://www.amazon.in/s?k=cotton+kurti+women+printed&rh=p_72%3A1318476031",
        "sub_category": "kurtis",
        "keywords": "kurti,cotton,ethnic wear,women fashion,india"
    },
    "spirituality": {
        "url": "https://www.amazon.in/s?k=pooja+items+set+for+home&rh=p_72%3A1318476031",
        "sub_category": "pooja",
        "keywords": "pooja,spiritual,mandir,diya,incense"
    }
}

# ─── EXTRACTOR ────────────────────────────────────────────
def extract_products(category, config, max_products):
    products = []
    url = config["url"]
    
    print(f"\n🔍 Extracting [{category}]...")
    print(f"   URL: {url[:60]}...")
    
    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        
        if response.status_code != 200:
            print(f"   ❌ HTTP {response.status_code} — skipping")
            return products
            
        soup = BeautifulSoup(response.content, "html.parser")
        items = soup.find_all("div", {"data-asin": True})
        
        print(f"   📦 Found {len(items)} product cards on page")
        
        count = 0
        for item in items:
            if count >= max_products:
                break
                
            asin = item.get("data-asin", "").strip()
            if not asin or len(asin) < 5:
                continue

            # Title
            title_tag = (
                item.find("span", {"class": "a-text-normal"}) or
                item.find("h2")
            )
            title = title_tag.get_text(strip=True) if title_tag else "Unknown Product"
            title = title[:100]

            # Image
            img_tag = item.find("img", {"class": "s-image"})
            image_url = img_tag.get("src", "") if img_tag else ""

            # Price
            price_tag = item.find("span", {"class": "a-price-whole"})
            price = f"₹{price_tag.get_text(strip=True)}" if price_tag else "Check Amazon"

            # Rating
            rating_tag = item.find("span", {"class": "a-icon-alt"})
            rating = rating_tag.get_text(strip=True)[:3] if rating_tag else "N/A"

            affiliate_url = f"https://www.amazon.in/dp/{asin}?tag=pulras0631-21"

            product = {
                "asin": asin,
                "product_title": title,
                "category": category,
                "sub_category": config["sub_category"],
                "keywords": config["keywords"],
                "price": price,
                "rating": rating,
                "image_url": image_url,
                "affiliate_url": affiliate_url,
                "posted": "NO",
                "last_posted": "",
                "pin_id": ""
            }
            
            products.append(product)
            count += 1
            
            if TEST_MODE:
                print(f"   ✅ {count}. ASIN: {asin}")
                print(f"      Title: {title[:60]}...")
                print(f"      Price: {price} | Rating: {rating}")
                print(f"      Image: {'✅ Found' if image_url else '❌ Missing'}")
                print(f"      Link:  {affiliate_url}")

        print(f"   📊 Extracted {len(products)} products from [{category}]")
        
    except requests.exceptions.Timeout:
        print(f"   ⏱️ Timeout — Amazon took too long")
    except requests.exceptions.ConnectionError:
        print(f"   🔌 Connection error — check internet")
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")
    
    return products


# ─── GOOGLE SHEETS WRITER ─────────────────────────────────
def write_to_google_sheets(products):
    try:
        import gspread
        from google.oauth2.service_account import Credentials
        
        # Load credentials from environment
        creds_json = os.environ.get("GOOGLE_SHEETS_CREDENTIALS")
        sheet_id   = os.environ.get("GOOGLE_SHEET_ID")
        
        if not creds_json or not sheet_id:
            print("\n⚠️  Google Sheets credentials not found — saving to JSON only")
            return False
        
        creds_dict = json.loads(creds_json)
        scopes = [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive"
        ]
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        client = gspread.authorize(creds)
        
        sheet = client.open_by_key(sheet_id)
        worksheet = sheet.worksheet("products")
        
        # Get existing ASINs to avoid duplicates
        existing = worksheet.col_values(1)
        existing_asins = set(existing[1:])  # skip header
        
        new_rows = []
        skipped = 0
        
        for p in products:
            if p["asin"] in existing_asins:
                skipped += 1
                continue
            new_rows.append([
                p["asin"],
                p["product_title"],
                p["category"],
                p["sub_category"],
                p["keywords"],
                p["posted"],
                p["last_posted"],
                p["pin_id"]
            ])
        
        if new_rows:
            worksheet.append_rows(new_rows)
            print(f"\n✅ Added {len(new_rows)} new products to Google Sheet")
        
        if skipped:
            print(f"⏭️  Skipped {skipped} already existing ASINs")
            
        return True
        
    except Exception as e:
        print(f"\n❌ Google Sheets error: {str(e)}")
        return False


# ─── MAIN ─────────────────────────────────────────────────
def main():
    print("=" * 55)
    print("🤖 AMAZON ASIN EXTRACTOR")
    print(f"   Mode: {'🧪 TEST (3 products/category)' if TEST_MODE else '🚀 FULL (10 products/category)'}")
    print(f"   Categories: {len(SEARCH_URLS)}")
    print(f"   Expected: ~{MAX_PRODUCTS * len(SEARCH_URLS)} products total")
    print("=" * 55)
    
    all_products = []
    
    for category, config in SEARCH_URLS.items():
        products = extract_products(category, config, MAX_PRODUCTS)
        all_products.extend(products)
        time.sleep(2)  # polite delay between requests
    
    # ── Summary ──
    print("\n" + "=" * 55)
    print("📊 EXTRACTION SUMMARY")
    print("=" * 55)
    
    by_category = {}
    for p in all_products:
        cat = p["category"]
        by_category[cat] = by_category.get(cat, 0) + 1
    
    for cat, count in by_category.items():
        status = "✅" if count > 0 else "❌"
        print(f"  {status} {cat:<15} {count} products")
    
    print(f"\n  Total extracted: {len(all_products)} products")
    
    # ── Save to JSON (always) ──
    output_file = "test_results.json" if TEST_MODE else "products_extracted.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(all_products, f, indent=2, ensure_ascii=False)
    print(f"\n💾 Saved to: {output_file}")
    
    # ── Write to Google Sheets ──
    if not TEST_MODE:
        print("\n📝 Writing to Google Sheets...")
        write_to_google_sheets(all_products)
    else:
        print("\n🧪 TEST MODE — Google Sheets not updated")
        print("   Run with TEST_MODE=false to write to sheet")
    
    # ── Final verdict ──
    print("\n" + "=" * 55)
    if len(all_products) >= len(SEARCH_URLS):
        print("✅ EXTRACTION WORKING CORRECTLY!")
        print("   Ready to run in full mode")
    else:
        print("⚠️  Some categories returned 0 products")
        print("   Amazon may be blocking — try again later")
    print("=" * 55)
    
    # Exit with error code if nothing extracted
    if len(all_products) == 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
