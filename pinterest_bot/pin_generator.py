#!/usr/bin/env python3
"""
SINDHOOR ETHNIC — Pinterest Pin Generator v2
============================================
Smart template selection based on image type:
- White/plain background → Template A (warm canvas + centered product)
- Lifestyle/model photo  → Template B (full bleed + bottom overlay)
"""

import os
import sys
import json
import time
import argparse
import requests
from io import BytesIO
from pathlib import Path

# ── Brand Config ──────────────────────────────────────────────────────────────
BRAND_NAME    = "SINDHOOR"
BRAND_SUB     = "ETHNIC"
BRAND_COLOR   = (139, 26, 43)      # Deep maroon
GOLD_COLOR    = (201, 168, 76)     # Gold
CREAM_BG      = (250, 242, 230)    # Warm cream
WHITE         = (255, 255, 255)
DARK_TEXT     = (45, 30, 20)       # Dark brown text

PIN_W, PIN_H  = 1000, 1500

AFFILIATE_TAG = os.environ.get('AMAZON_AFFILIATE_TAG', 'pulras0631-21')
CLOUDINARY_CLOUD = os.environ.get('CLOUDINARY_CLOUD_NAME', '')
CLOUDINARY_KEY   = os.environ.get('CLOUDINARY_API_KEY', '')
CLOUDINARY_SEC   = os.environ.get('CLOUDINARY_API_SECRET', '')


# ── IMAGE DOWNLOAD ─────────────────────────────────────────────────────────────
def download_image(url):
    try:
        from PIL import Image
        print(f'   Downloading: {url[:80]}')
        r = requests.get(url, timeout=60, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
        })
        if r.status_code == 200 and len(r.content) > 2000:
            img = Image.open(BytesIO(r.content)).convert('RGB')
            print(f'   Size: {img.size}')
            return img
        print(f'   Failed: status {r.status_code}')
        return None
    except Exception as e:
        print(f'   Error: {e}')
        return None


def get_product_image(asin, image_url):
    """Try provided URL first, then Amazon fallbacks."""
    # Try provided URL
    if image_url and image_url.startswith('http'):
        img = download_image(image_url)
        if img:
            return img

    # Amazon fallbacks
    fallbacks = [
        f'https://m.media-amazon.com/images/P/{asin}.jpg',
        f'https://images-in.ssl-images-amazon.com/images/P/{asin}.01._SCLZZZZZZZ_.jpg',
    ]
    for url in fallbacks:
        img = download_image(url)
        if img:
            print('   Using Amazon fallback image')
            return img

    print('   No image found — using plain background')
    return None


# ── IMAGE TYPE DETECTION ───────────────────────────────────────────────────────
def detect_image_type(img):
    """
    Detect if image is white/plain background or lifestyle photo.
    Returns: 'white_bg' or 'lifestyle'
    """
    import numpy as np
    from PIL import Image

    # Sample corners and edges for white/light pixels
    w, h = img.size
    sample_regions = [
        img.crop((0, 0, w//4, h//4)),           # top left
        img.crop((3*w//4, 0, w, h//4)),          # top right
        img.crop((0, 3*h//4, w//4, h)),          # bottom left
        img.crop((3*w//4, 3*h//4, w, h)),        # bottom right
    ]

    white_pixel_count = 0
    total_pixels = 0

    for region in sample_regions:
        arr = list(region.getdata())
        for pixel in arr:
            r, g, b = pixel[0], pixel[1], pixel[2]
            # Count near-white pixels (all channels > 220)
            if r > 220 and g > 220 and b > 220:
                white_pixel_count += 1
            total_pixels += 1

    white_ratio = white_pixel_count / total_pixels if total_pixels > 0 else 0
    print(f'   White pixel ratio in corners: {white_ratio:.2f}')

    if white_ratio > 0.5:
        print('   Detected: WHITE BACKGROUND → Template A')
        return 'white_bg'
    else:
        print('   Detected: LIFESTYLE PHOTO → Template B')
        return 'lifestyle'


# ── FONT LOADER ────────────────────────────────────────────────────────────────
def load_fonts():
    from PIL import ImageFont

    font_paths = [
        '/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf',
        '/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf',
        '/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf',
        '/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf',
        '/usr/share/fonts/truetype/freefont/FreeSerif.ttf',
    ]

    def try_font(size, bold=True):
        paths = [p for p in font_paths if ('Bold' in p or 'bold' in p) == bold]
        for path in paths:
            try:
                return ImageFont.truetype(path, size)
            except:
                continue
        return ImageFont.load_default()

    return {
        'brand':    try_font(40, bold=True),
        'subtitle': try_font(20, bold=False),
        'title':    try_font(44, bold=True),
        'detail':   try_font(30, bold=False),
        'cta':      try_font(28, bold=True),
    }


# ── HELPER: Draw Centered Text ─────────────────────────────────────────────────
def draw_centered(draw, text, y, font, color):
    bbox = draw.textbbox((0, 0), text, font=font)
    w = bbox[2] - bbox[0]
    draw.text(((PIN_W - w) // 2, y), text, fill=color, font=font)
    return bbox[3] - bbox[1]  # return height


# ── TEMPLATE A: White Background ───────────────────────────────────────────────
def template_a(img, title, occasion, fabric, keywords, fonts):
    """
    Warm cream canvas with product centered.
    Best for white background Amazon product shots.
    """
    from PIL import Image, ImageDraw
    import textwrap

    pin = Image.new('RGB', (PIN_W, PIN_H), CREAM_BG)
    draw = ImageDraw.Draw(pin)

    # ── Warm background texture (subtle) ──────────────────────────────────────
    # Add slight gradient from cream to slightly darker at bottom
    for y in range(PIN_H):
        darkness = int(y / PIN_H * 15)
        color = (
            max(0, CREAM_BG[0] - darkness),
            max(0, CREAM_BG[1] - darkness),
            max(0, CREAM_BG[2] - darkness)
        )
        draw.line([(0, y), (PIN_W, y)], fill=color)

    # ── Brand header ──────────────────────────────────────────────────────────
    draw.rectangle([(0, 0), (PIN_W, 90)], fill=CREAM_BG)
    draw_centered(draw, BRAND_NAME, 10, fonts['brand'], BRAND_COLOR)
    draw_centered(draw, BRAND_SUB, 55, fonts['subtitle'], GOLD_COLOR)

    # Gold divider
    draw.line([(PIN_W//2 - 90, 78), (PIN_W//2 - 18, 78)], fill=GOLD_COLOR, width=1)
    draw.line([(PIN_W//2 + 18, 78), (PIN_W//2 + 90, 78)], fill=GOLD_COLOR, width=1)

    # ── Product image (centered, top portion) ─────────────────────────────────
    if img:
        # Remove white background by making it transparent
        img_area_h = int(PIN_H * 0.58)
        img_area_w = PIN_W - 80

        # Resize maintaining aspect ratio
        img_copy = img.copy()
        img_copy.thumbnail((img_area_w, img_area_h - 90), Image.LANCZOS)
        iw, ih = img_copy.size

        # Paste centered
        paste_x = (PIN_W - iw) // 2
        paste_y = 100 + (img_area_h - 90 - ih) // 2
        pin.paste(img_copy, (paste_x, paste_y))

    # ── Maroon accent bar ──────────────────────────────────────────────────────
    bar_y = int(PIN_H * 0.62)
    draw.rectangle([(0, bar_y), (PIN_W, bar_y + 5)], fill=BRAND_COLOR)

    # ── Text section (bottom 38%) ──────────────────────────────────────────────
    text_start = bar_y + 5
    draw.rectangle([(0, text_start), (PIN_W, PIN_H)], fill=(248, 238, 224))

    y = text_start + 28

    # Title
    wrapped = textwrap.wrap(title, width=22)
    for line in wrapped[:2]:
        draw_centered(draw, line, y, fonts['title'], BRAND_COLOR)
        y += 52

    y += 8

    # Gold thin divider
    draw.line([(80, y), (PIN_W - 80, y)], fill=GOLD_COLOR, width=1)
    y += 18

    # Details
    details = []
    if occasion and occasion.strip():
        details.append(occasion.strip())
    if fabric and fabric.strip():
        details.append(fabric.strip())
    if keywords:
        kws = [k.strip().title() for k in keywords.split(',')[:2]]
        details.append(' & '.join(kws))

    for detail in details:
        # Small gold dot before detail
        dot_x = PIN_W // 2 - 180
        draw.ellipse([(dot_x, y + 10), (dot_x + 8, y + 18)], fill=GOLD_COLOR)
        draw.text((dot_x + 16, y), detail, fill=DARK_TEXT, font=fonts['detail'])
        y += 40

    # ── CTA Button ────────────────────────────────────────────────────────────
    cta = 'Shop on Amazon India'
    bbox = draw.textbbox((0, 0), cta, font=fonts['cta'])
    cta_w = bbox[2] - bbox[0]
    cta_h = bbox[3] - bbox[1]
    btn_x = (PIN_W - cta_w - 60) // 2
    btn_y = PIN_H - 85

    draw.rounded_rectangle(
        [(btn_x, btn_y), (btn_x + cta_w + 60, btn_y + cta_h + 22)],
        radius=30, fill=BRAND_COLOR
    )
    draw.text((btn_x + 30, btn_y + 11), cta, fill=WHITE, font=fonts['cta'])

    return pin


# ── TEMPLATE B: Lifestyle Photo ────────────────────────────────────────────────
def template_b(img, title, occasion, fabric, keywords, fonts):
    """
    Full bleed lifestyle image with elegant bottom overlay.
    Best for model photos with colored backgrounds.
    """
    from PIL import Image, ImageDraw
    import textwrap

    pin = Image.new('RGB', (PIN_W, PIN_H), CREAM_BG)
    draw = ImageDraw.Draw(pin)

    # ── Full bleed product image ───────────────────────────────────────────────
    if img:
        img_resized = img.resize((PIN_W, PIN_H), Image.LANCZOS)
        pin.paste(img_resized, (0, 0))

    # ── Semi-transparent brand header ─────────────────────────────────────────
    header = Image.new('RGBA', (PIN_W, 90), (250, 242, 230, 210))
    pin.paste(header.convert('RGB'), (0, 0), header)
    draw = ImageDraw.Draw(pin)
    draw_centered(draw, BRAND_NAME, 10, fonts['brand'], BRAND_COLOR)
    draw_centered(draw, BRAND_SUB, 55, fonts['subtitle'], GOLD_COLOR)
    draw.line([(PIN_W//2 - 90, 78), (PIN_W//2 - 18, 78)], fill=GOLD_COLOR, width=1)
    draw.line([(PIN_W//2 + 18, 78), (PIN_W//2 + 90, 78)], fill=GOLD_COLOR, width=1)

    # ── Dark gradient overlay (bottom 42%) ───────────────────────────────────
    overlay_start = int(PIN_H * 0.58)
    overlay_h = PIN_H - overlay_start

    overlay = Image.new('RGBA', (PIN_W, overlay_h), (0, 0, 0, 0))
    ov_draw = ImageDraw.Draw(overlay)

    for i in range(overlay_h):
        progress = i / overlay_h
        # Gradual increase in opacity
        alpha = int(progress * progress * 220)
        ov_draw.line([(0, i), (PIN_W, i)], fill=(20, 10, 5, alpha))

    pin.paste(overlay.convert('RGB'), (0, overlay_start), overlay)
    draw = ImageDraw.Draw(pin)

    # ── Gold accent line ──────────────────────────────────────────────────────
    accent_y = overlay_start + 20
    draw.line([(60, accent_y), (PIN_W - 60, accent_y)], fill=GOLD_COLOR, width=2)

    # ── Text on dark overlay ───────────────────────────────────────────────────
    y = accent_y + 20

    wrapped = textwrap.wrap(title, width=22)
    for line in wrapped[:2]:
        draw_centered(draw, line, y, fonts['title'], WHITE)
        y += 52

    y += 8

    # Details in gold
    details = []
    if occasion and occasion.strip():
        details.append(occasion.strip())
    if fabric and fabric.strip():
        details.append(fabric.strip())

    for detail in details:
        draw_centered(draw, detail, y, fonts['detail'], GOLD_COLOR)
        y += 40

    # ── CTA Button ────────────────────────────────────────────────────────────
    cta = 'Shop on Amazon India'
    bbox = draw.textbbox((0, 0), cta, font=fonts['cta'])
    cta_w = bbox[2] - bbox[0]
    cta_h = bbox[3] - bbox[1]
    btn_x = (PIN_W - cta_w - 60) // 2
    btn_y = PIN_H - 85

    # Gold CTA for lifestyle template
    draw.rounded_rectangle(
        [(btn_x, btn_y), (btn_x + cta_w + 60, btn_y + cta_h + 22)],
        radius=30, fill=GOLD_COLOR
    )
    draw.text((btn_x + 30, btn_y + 11), cta, fill=DARK_TEXT, font=fonts['cta'])

    return pin


# ── CLOUDINARY UPLOAD ──────────────────────────────────────────────────────────
def upload_cloudinary(image_path):
    if not all([CLOUDINARY_CLOUD, CLOUDINARY_KEY, CLOUDINARY_SEC]):
        print('⚠️  Cloudinary not configured')
        return None
    try:
        import cloudinary
        import cloudinary.uploader
        cloudinary.config(
            cloud_name=CLOUDINARY_CLOUD,
            api_key=CLOUDINARY_KEY,
            api_secret=CLOUDINARY_SEC
        )
        result = cloudinary.uploader.upload(
            image_path,
            folder='sindhoor_pins',
            public_id=f'pin_{int(time.time())}',
            overwrite=True
        )
        url = result.get('secure_url', '')
        print(f'✅ Uploaded: {url}')
        return url
    except Exception as e:
        print(f'❌ Cloudinary error: {e}')
        return None


# ── MAIN ──────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--asin',     required=True)
    parser.add_argument('--title',    required=True)
    parser.add_argument('--category', default='fashion')
    parser.add_argument('--keywords', default='')
    parser.add_argument('--occasion', default='Festive & Casual')
    parser.add_argument('--fabric',   default='Premium Fabric')
    parser.add_argument('--colors',   default='')
    parser.add_argument('--image-url', default='')
    parser.add_argument('--output',   default='pin_output.jpg')
    args = parser.parse_args()

    print('=' * 60)
    print('🎨 SINDHOOR ETHNIC — Pin Generator v2')
    print(f'   ASIN:  {args.asin}')
    print(f'   Title: {args.title[:50]}')
    print('=' * 60)

    # Step 1: Get product image
    print('\n📥 Getting product image...')
    img = get_product_image(args.asin, args.image_url)

    # Step 2: Detect image type
    image_type = 'lifestyle'
    if img:
        try:
            image_type = detect_image_type(img)
        except Exception as e:
            print(f'   Detection failed: {e} — defaulting to lifestyle')

    # Step 3: Load fonts
    print('\n🔤 Loading fonts...')
    fonts = load_fonts()

    # Step 4: Generate pin with correct template
    print(f'\n🎨 Generating pin with Template {"A" if image_type == "white_bg" else "B"}...')
    try:
        if image_type == 'white_bg':
            pin = template_a(img, args.title, args.occasion,
                           args.fabric, args.keywords, fonts)
        else:
            pin = template_b(img, args.title, args.occasion,
                           args.fabric, args.keywords, fonts)

        pin.save(args.output, 'JPEG', quality=95)
        print(f'✅ Pin saved: {args.output}')

    except Exception as e:
        print(f'❌ Pin generation failed: {e}')
        import traceback
        traceback.print_exc()
        sys.exit(1)

    # Step 5: Upload to Cloudinary
    print('\n☁️  Uploading to Cloudinary...')
    url = upload_cloudinary(args.output)

    if url:
        print(f'\n📌 PIN URL: {url}')
        with open('pin_url.txt', 'w') as f:
            f.write(url)
    else:
        github_user = os.environ.get('GITHUB_REPOSITORY_OWNER', 'drsheetal0111')
        filename = Path(args.output).name
        fallback = f'https://{github_user}.github.io/deal-hunter/pins/{filename}'
        print(f'\n📌 PIN URL (fallback): {fallback}')
        with open('pin_url.txt', 'w') as f:
            f.write(fallback)

    print('\n' + '=' * 60)
    print('✅ DONE!')


if __name__ == '__main__':
    main()
