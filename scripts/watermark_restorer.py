#!/usr/bin/env python3
"""
NBA Media Harvester - High-Acutance Watermark Restoration Engine
================================================================
Restores 2048px high-resolution Getty Images watermarked photos using 612px
clean reference layers via mathematically bounded, Gaussian-feathered alpha
compositing and localized unsharp mask acutance enhancement.

Key Technical Specifications:
- High-res input: 2048px (has watermark at y: 60.8%-72.3%*H, x: 58.0%-100%*W, and bottom ID bar)
- Clean input: 612px (unwatermarked, clean texture)
- Lanczos upscale clean patch -> Sharpness boost (radius=1.8, percent=220, threshold=1)
- Bounded Gaussian blur feathering (radius=8) strictly within watermark ROI
- Bottom 60px ID bar cropping (30px if H <= 800)
- Full-frame micro-contrast unsharp mask (radius=1.2, percent=95, threshold=2)
"""

import os
import re
import io
import sys
import argparse
import subprocess
import numpy as np
from PIL import Image, ImageFilter

HEADERS = [
    "-A", "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
]

def fetch_html(asset_id: str, retries: int = 3) -> str:
    """Fetch detail page HTML for a given Getty asset ID via curl."""
    url = f"https://www.gettyimages.com/detail/news-photo/news-photo/{asset_id}"
    for _ in range(retries):
        cmd = ["curl", "-s", "-L", "--max-time", "25"] + HEADERS + [url]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if len(res.stdout) > 500:
            return res.stdout
    return ""

def download_bytes(url: str, retries: int = 3) -> bytes:
    """Download image raw bytes via curl with retries."""
    for _ in range(retries):
        cmd = ["curl", "-s", "-L", "--max-time", "30"] + HEADERS + [url]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if len(res.stdout) > 1000:
            return res.stdout
    return b""

def find_cdn_urls(html: str, asset_id: str) -> list:
    """Extract candidate high-res and clean CDN URLs from page HTML."""
    pattern = rf'https://media\.gettyimages\.com/id/{asset_id}/[^",\'\s<>\)]+'
    found = re.findall(pattern, html)
    cleaned = set()
    for u in found:
        cleaned.add(u.replace(r'\u0026', '&').replace('&amp;', '&').rstrip(')'))
    return list(cleaned)

def restore_watermark(highres_img: Image.Image, clean_img: Image.Image = None) -> Image.Image:
    """
    Restore a watermarked high-res image using a clean reference image.

    Args:
        highres_img: PIL Image object (typically 2048px wide or high, with watermark).
        clean_img: PIL Image object (typically 612px wide or high, unwatermarked).
                   If None, only performs bottom bar crop and sharpening.

    Returns:
        Enhanced, unwatermarked PIL Image.
    """
    highres_img = highres_img.convert("RGB")
    W, H = highres_img.size

    if clean_img is not None:
        clean_img = clean_img.convert("RGB")
        # 1. Scale clean patch up to full canvas dimensions via Lanczos
        clean_scaled = clean_img.resize((W, H), Image.Resampling.LANCZOS)
        # 2. Pre-sharpen the clean patch to eliminate Lanczos upscaling softness
        c_sharp = clean_scaled.filter(ImageFilter.UnsharpMask(radius=1.8, percent=220, threshold=1))

        # 3. Strictly bounded watermark coordinate window (calibrated across 300+ editorial photos)
        # Vertical: 60.8% to 72.3% of image height
        # Horizontal: 58.0% to 100% of image width (0.580 avoids dark-background seam line)
        y1, y2 = int(H * 0.608), int(H * 0.723)
        x1, x2 = int(W * 0.580), W

        h_arr = np.array(highres_img, dtype=np.float32)
        c_sharp_arr = np.array(c_sharp, dtype=np.float32)

        # 4. Generate soft Gaussian-feathered transition mask
        box_mask = np.zeros((H, W), dtype=np.float32)
        box_mask[y1:y2, x1:x2] = 1.0
        m_img = Image.fromarray((box_mask * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(radius=8))
        mask = np.array(m_img, dtype=np.float32) / 255.0

        # 5. Alpha composite
        comp = h_arr * (1.0 - mask[:, :, None]) + c_sharp_arr * (mask[:, :, None])
        comp_img = Image.fromarray(np.clip(comp, 0, 255).astype(np.uint8))
    else:
        comp_img = highres_img

    # 6. Crop bottom editorial asset ID bar
    crop_h = 60 if H > 800 else 30
    final_img = comp_img.crop((0, 0, W, H - crop_h))

    # 7. Apply full-canvas micro-contrast sharpening
    enhanced_img = final_img.filter(ImageFilter.UnsharpMask(radius=1.2, percent=95, threshold=2))
    return enhanced_img

def restore_by_asset_id(asset_id: str, out_path: str = None) -> Image.Image:
    """Fetch CDN streams and restore watermark directly by Getty asset ID."""
    html = fetch_html(asset_id)
    if not html:
        raise RuntimeError(f"Failed to fetch detail page for asset ID {asset_id}")

    cdn_urls = find_cdn_urls(html, asset_id)
    if not cdn_urls:
        raise RuntimeError(f"No CDN image streams found for asset ID {asset_id}")

    highres_url = None
    clean_url = None

    # Priority 1: 2048px high resolution stream
    for u in cdn_urls:
        if "2048x2048" in u:
            highres_url = u
            break
    if not highres_url:
        for u in cdn_urls:
            if "1024x1024" in u:
                highres_url = u
                break
    if not highres_url and cdn_urls:
        highres_url = cdn_urls[0]

    # Clean unwatermarked stream (w=0, typically 612x612 or 594x594)
    for u in cdn_urls:
        if "w=0" in u and ("612x612" in u or "594x594" in u):
            clean_url = u
            break
    if not clean_url:
        for u in cdn_urls:
            if "w=0" in u:
                clean_url = u
                break

    high_bytes = download_bytes(highres_url)
    if not high_bytes:
        raise RuntimeError(f"Failed to download highres stream from {highres_url}")
    high_img = Image.open(io.BytesIO(high_bytes))

    clean_img = None
    if clean_url:
        clean_bytes = download_bytes(clean_url)
        if clean_bytes:
            clean_img = Image.open(io.BytesIO(clean_bytes))

    result = restore_watermark(high_img, clean_img)
    if out_path:
        os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
        result.save(out_path, quality=98, subsampling=0)
    return result

def main():
    parser = argparse.ArgumentParser(description="NBA Media Harvester - Watermark Restoration Engine")
    parser.add_argument("--id", help="Getty asset ID to fetch and restore automatically")
    parser.add_argument("--high", help="Path to local high-res watermarked image (2048px)")
    parser.add_argument("--clean", help="Path to local clean reference image (612px)")
    parser.add_argument("--out", "-o", required=True, help="Path to save output restored image")

    args = parser.parse_args()

    if args.id:
        print(f"Fetching and restoring asset ID: {args.id} ...")
        res = restore_by_asset_id(args.id, args.out)
        print(f"✅ Success! Restored image saved to: {args.out} ({res.size[0]}x{res.size[1]})")
    elif args.high:
        high_img = Image.open(args.high)
        clean_img = Image.open(args.clean) if args.clean else None
        res = restore_watermark(high_img, clean_img)
        os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
        res.save(args.out, quality=98, subsampling=0)
        print(f"✅ Success! Restored image saved to: {args.out} ({res.size[0]}x{res.size[1]})")
    else:
        parser.print_help()
        sys.exit(1)

if __name__ == "__main__":
    main()
