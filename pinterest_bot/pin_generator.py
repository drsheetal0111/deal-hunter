#!/usr/bin/env python3
"""
SINDHOOR ETHNIC — Pinterest Pin Generator
==========================================
Generates styled Pinterest pins using:
1. DALL-E 3 for boutique-style product image
2. PIL/Pillow for text overlay + branding
3. Uploads to GitHub Pages for URL access

Usage:
  python pin_generator.py \
    --asin B0XXXXX \
    --title "Embroidered Anarkali Kurta Set" \
    --category "fashion" \
    --keywords "anarkali,kurta,ethnic,festive" \
    --occasion "Wedding, Festive, Party" \
    --fabric "Cotton Silk Blend" \
    --colors "Deep Maroon" \
    --output "output_pin.jpg"
"""

import os
import sys
import json
import time
import argparse
import requests
import base64
from io import BytesIO
from pathlib import Path

# ── Brand Config ──────────────────────────────────────────────────────────────
BRAND_NAME = "SINDHOOR"
BRAND_SUBTITLE = "ETHNIC"
BRAND_COLOR = (139, 26, 43)       # Deep maroon #8B1A2B
GOLD_COLOR = (201, 168, 76)       # Gold #C9A84C
CREAM_BG = (250, 240, 230)        # Cream #FAF0E6
WHITE = (255, 255, 255)
DARK_OVERLAY = (30, 20, 15)       # Dark brown for gradient

# ── Pinterest Pin Dimensions ──────────────────────────────────────────────────
PIN_WIDTH = 1000
PIN_HEIGHT = 1500

# ── OpenAI Config ─────────────────────────────────────────────────────────────
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY', '')


def build_dalle_prompt(title, category, keywords, occasion, fabric, colors):
    """Build an optimized DALL-E 3 prompt for ethnic fashion product."""

    # Extract key product type from title
    product_type = title.lower()
    style_elements = []

    if any(w in product_type for w in ['saree', 'sari']):
        style_elements = ['saree draped elegantly on a mannequin',
                         'matching blouse visible', 'fabric flowing naturally']
        setting = 'traditional Indian boutique'
    elif any(w in product_type for w in ['kurti', 'kurta', 'anarkali']):
        style_elements = ['kurta set displayed on wooden hangers',
                         'dupatta draped alongside', 'palazzo pants visible']
        setting = 'elegant ethnic fashion boutique'
    elif any(w in product_type for w in ['lehenga', 'sharara']):
        style_elements = ['lehenga set on display stand',
                         'dupatta arranged gracefully', 'embroidery details visible']
        setting = 'bridal boutique showroom'
    elif any(w in product_type for w in ['jewelry', 'necklace', 'earring']):
        style_elements = ['jewelry displayed on velvet stand',
                         'soft lighting highlighting details', 'elegant arrangement']
        setting = 'luxury jewelry boutique'
    else:
        style_elements = ['outfit displayed on wooden hangers',
                         'fabric details clearly visible']
        setting = 'ethnic fashion boutique'

    style_str = ', '.join(style_elements)

    prompt = (
        f"Professional product photography of a {title}. "
        f"Color: {colors}. "
        f"{style_str}. "
        f"Setting: {setting} with warm beige background (#E8D5B7). "
        f"Soft palm leaf shadows on background wall. "
        f"Lifestyle props: dried pampas grass arrangement, ceramic pot. "
        f"Warm golden hour lighting from left. "
        f"Fabric texture clearly visible. "
        f"Suitable for {occasion} occasions. "
        f"Made from {fabric}. "
        f"Editorial fashion photography style. "
        f"High end boutique aesthetic. "
        f"No text, no watermarks, no people, no models. "
        f"Clean professional composition. "
        f"Shot on medium format camera. "
        f"Warm earthy color palette."
    )

    return prompt


def generate_dalle_image(prompt):
    """Call DALL-E 3 API to generate product image."""

    if not OPENAI_API_KEY:
        print('❌ OPENAI_API_KEY not set')
        return None

    print(f'🎨 Generating DALL-E image...')
    print(f'   Prompt: {prompt[:100]}...')

    headers = {
        'Authorization': f'Bearer {OPENAI_API_KEY}',
        'Content-Type': 'application/json'
    }

    payload = {
        'model': 'dall-e-3',
        'prompt': prompt,
        'n': 1,
        'size': '1024x1024',
        'quality': 'standard',
        'response_format': 'url'
    }

    try:
        response = requests.post(
            'https://api.openai.com/v1/images/generations',
            headers=headers,
            json=payload,
            timeout=60
        )

        if response.status_code == 200:
            data = response.json()
            image_url = data['data'][0]['url']
            print(f'✅ DALL-E image generated')
            return image_url
        else:
            print(f'❌ DALL-E error: {response.status_code}')
            print(f'   {response.text[:200]}')
            return None

    except Exception as e:
        print(f'❌ DALL-E request failed: {e}')
        return None


def download_image(url):
    """Download image from URL and return as PIL Image."""
    try:
        from PIL import Image
        response = requests.get(url, timeout=30)
        img = Image.open(BytesIO(response.content))
        return img
    except Exception as e:
        print(f'❌ Image download failed: {e}')
        return None


def create_pin(
    product_image,
    title,
    occasion,
    fabric,
    keywords,
    output_path
):
    """
    Create final Pinterest pin with branding and text overlay.
    Combines DALL-E product image with SINDHOOR ETHNIC branding.
    """
    try:
        from PIL import Image, ImageDraw, ImageFont, ImageFilter
        import textwrap
    except ImportError:
        print('❌ PIL not installed. Run: pip install Pillow')
        return False

    # ── Create Base Canvas ────────────────────────────────────────────────────
    pin = Image.new('RGB', (PIN_WIDTH, PIN_HEIGHT), CREAM_BG)
    draw = ImageDraw.Draw(pin)

    # ── Place Product Image (top 65% of pin) ─────────────────────────────────
    if product_image:
        img_height = int(PIN_HEIGHT * 0.65)
        img_width = PIN_WIDTH

        # Resize product image to fit
        product_image = product_image.convert('RGB')
        product_image = product_image.resize(
            (img_width, img_height),
            Image.LANCZOS
        )
        pin.paste(product_image, (0, 0))

        # Add subtle gradient overlay at bottom of image
        gradient = Image.new('RGBA', (PIN_WIDTH, 200), (0, 0, 0, 0))
        grad_draw = ImageDraw.Draw(gradient)
        for i in range(200):
            alpha = int((i / 200) * 180)
            grad_draw.line(
                [(0, i), (PIN_WIDTH, i)],
                fill=(30, 20, 15, alpha)
            )
        pin.paste(
            gradient.convert('RGB'),
            (0, img_height - 200),
            gradient
        )

    # ── Brand Header (top of pin) ─────────────────────────────────────────────
    # Brand background bar
    draw.rectangle([(0, 0), (PIN_WIDTH, 80)], fill=CREAM_BG)

    # Try to load fonts, fall back to default
    try:
        font_brand = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf', 36)
        font_subtitle = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf', 18)
        font_title = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf', 42)
        font_detail = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf', 28)
        font_cta = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf', 30)
    except:
        font_brand = ImageFont.load_default()
        font_subtitle = font_brand
        font_title = font_brand
        font_detail = font_brand
        font_cta = font_brand

    # Brand name
    brand_bbox = draw.textbbox((0, 0), BRAND_NAME, font=font_brand)
    brand_w = brand_bbox[2] - brand_bbox[0]
    draw.text(
        ((PIN_WIDTH - brand_w) // 2, 12),
        BRAND_NAME,
        fill=BRAND_COLOR,
        font=font_brand
    )

    # Subtitle "ETHNIC"
    sub_bbox = draw.textbbox((0, 0), BRAND_SUBTITLE, font=font_subtitle)
    sub_w = sub_bbox[2] - sub_bbox[0]
    draw.text(
        ((PIN_WIDTH - sub_w) // 2, 50),
        BRAND_SUBTITLE,
        fill=GOLD_COLOR,
        font=font_subtitle
    )

    # Gold divider lines
    draw.line(
        [(PIN_WIDTH//2 - 80, 65), (PIN_WIDTH//2 - 15, 65)],
        fill=GOLD_COLOR, width=1
    )
    draw.line(
        [(PIN_WIDTH//2 + 15, 65), (PIN_WIDTH//2 + 80, 65)],
        fill=GOLD_COLOR, width=1
    )

    # ── Text Section (bottom 35%) ─────────────────────────────────────────────
    text_start_y = int(PIN_HEIGHT * 0.65)
    text_bg_color = (245, 235, 220)  # Slightly darker cream

    # Text background
    draw.rectangle(
        [(0, text_start_y), (PIN_WIDTH, PIN_HEIGHT)],
        fill=text_bg_color
    )

    # Gold top border line
    draw.rectangle(
        [(0, text_start_y), (PIN_WIDTH, text_start_y + 4)],
        fill=GOLD_COLOR
    )

    # Product title
    y_pos = text_start_y + 30

    # Wrap title to fit
    wrapped_title = textwrap.wrap(title, width=25)
    for line in wrapped_title[:2]:  # Max 2 lines
        title_bbox = draw.textbbox((0, 0), line, font=font_title)
        title_w = title_bbox[2] - title_bbox[0]
        draw.text(
            ((PIN_WIDTH - title_w) // 2, y_pos),
            line,
            fill=BRAND_COLOR,
            font=font_title
        )
        y_pos += 50

    y_pos += 10

    # Gold divider
    draw.line(
        [(60, y_pos), (PIN_WIDTH - 60, y_pos)],
        fill=GOLD_COLOR, width=1
    )
    y_pos += 20

    # Product details with gold bullets
    details = []
    if occasion and occasion != 'N/A':
        details.append(f'✦  {occasion}')
    if fabric and fabric != 'N/A':
        details.append(f'✦  {fabric}')
    if keywords:
        kw_list = keywords.split(',')[:2]
        kw_str = ' · '.join([k.strip().title() for k in kw_list])
        details.append(f'✦  {kw_str}')

    for detail in details:
        detail_bbox = draw.textbbox((0, 0), detail, font=font_detail)
        detail_w = detail_bbox[2] - detail_bbox[0]
        draw.text(
            ((PIN_WIDTH - detail_w) // 2, y_pos),
            detail,
            fill=(80, 60, 40),
            font=font_detail
        )
        y_pos += 42

    y_pos += 10

    # CTA Button
    cta_text = 'Shop on Amazon India  →'
    cta_bbox = draw.textbbox((0, 0), cta_text, font=font_cta)
    cta_w = cta_bbox[2] - cta_bbox[0]
    cta_h = cta_bbox[3] - cta_bbox[1]
    cta_x = (PIN_WIDTH - cta_w - 40) // 2
    cta_y = PIN_HEIGHT - 80

    # CTA background
    draw.rounded_rectangle(
        [(cta_x - 20, cta_y - 10),
         (cta_x + cta_w + 20, cta_y + cta_h + 10)],
        radius=25,
        fill=BRAND_COLOR
    )
    draw.text(
        (cta_x, cta_y),
        cta_text,
        fill=WHITE,
        font=font_cta
    )

    # ── Save ──────────────────────────────────────────────────────────────────
    pin.save(output_path, 'JPEG', quality=95)
    print(f'✅ Pin saved: {output_path}')
    return True


def upload_to_cloudinary(image_path):
    """Upload pin image to Cloudinary free tier."""
    cloud_name = os.environ.get('CLOUDINARY_CLOUD_NAME', '')
    api_key = os.environ.get('CLOUDINARY_API_KEY', '')
    api_secret = os.environ.get('CLOUDINARY_API_SECRET', '')

    if not all([cloud_name, api_key, api_secret]):
        print('⚠️  Cloudinary not configured — using local path')
        return None

    try:
        import cloudinary
        import cloudinary.uploader

        cloudinary.config(
            cloud_name=cloud_name,
            api_key=api_key,
            api_secret=api_secret
        )

        result = cloudinary.uploader.upload(
            image_path,
            folder='sindhoor_pins',
            public_id=f'pin_{int(time.time())}',
            overwrite=True
        )

        url = result.get('secure_url', '')
        print(f'✅ Uploaded to Cloudinary: {url}')
        return url

    except Exception as e:
        print(f'❌ Cloudinary upload failed: {e}')
        return None


# ── MAIN ──────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description='SINDHOOR ETHNIC Pinterest Pin Generator'
    )
    parser.add_argument('--asin', required=True)
    parser.add_argument('--title', required=True)
    parser.add_argument('--category', default='fashion')
    parser.add_argument('--keywords', default='')
    parser.add_argument('--occasion', default='Festive & Casual')
    parser.add_argument('--fabric', default='Premium Fabric')
    parser.add_argument('--colors', default='Beautiful Colors')
    parser.add_argument('--output', default='pin_output.jpg')
    args = parser.parse_args()

    print('=' * 60)
    print('🎨 SINDHOOR ETHNIC — Pin Generator')
    print(f'   ASIN: {args.asin}')
    print(f'   Title: {args.title[:50]}')
    print('=' * 60)

    # Step 1: Build DALL-E prompt
    prompt = build_dalle_prompt(
        args.title,
        args.category,
        args.keywords,
        args.occasion,
        args.fabric,
        args.colors
    )

    # Step 2: Generate product image
    image_url = generate_dalle_image(prompt)

    product_image = None
    if image_url:
        product_image = download_image(image_url)
    else:
        print('⚠️  DALL-E failed — using plain background')

    # Step 3: Create Pinterest pin
    success = create_pin(
        product_image=product_image,
        title=args.title,
        occasion=args.occasion,
        fabric=args.fabric,
        keywords=args.keywords,
        output_path=args.output
    )

    if not success:
        print('❌ Pin creation failed')
        sys.exit(1)

    # Step 4: Upload and return URL
    upload_url = upload_to_cloudinary(args.output)

    if upload_url:
        print(f'\n📌 PIN URL: {upload_url}')
        # Write URL to file for GitHub Actions to read
        with open('pin_url.txt', 'w') as f:
            f.write(upload_url)
    else:
        # Fallback — use GitHub Pages URL
        github_user = os.environ.get('GITHUB_REPOSITORY_OWNER', 'drsheetal0111')
        filename = Path(args.output).name
        github_url = f'https://{github_user}.github.io/deal-hunter/pins/{filename}'
        print(f'\n📌 PIN URL (GitHub Pages): {github_url}')
        with open('pin_url.txt', 'w') as f:
            f.write(github_url)

    print('=' * 60)
    print('✅ DONE!')


if __name__ == '__main__':
    main()
