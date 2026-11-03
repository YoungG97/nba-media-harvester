#!/usr/bin/env python3
"""
NBA Media Harvester - Quickstart Example
========================================
Demonstrates programmatic usage of the watermark restoration engine
and photo asset harvester.
"""

import os
import sys

# Add parent directory to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.watermark_restorer import restore_by_asset_id
from scripts.getty_harvester import harvest_player_assets

def demo_single_restore():
    """Demo restoring a single 2048px high-resolution image by Getty Asset ID."""
    print("--- [Demo 1] Restoring Single Asset ID ---")
    asset_id = "2297624955"  # Yaxel Lendeborg Warriors Media Day Portrait
    out_file = os.path.expanduser("~/Downloads/demo_restore_2297624955.jpg")
    try:
        res = restore_by_asset_id(asset_id, out_file)
        print(f"✅ Restored Image Saved: {out_file} (Dimensions: {res.size[0]}x{res.size[1]})")
    except Exception as e:
        print(f"Skipping single restore demo: {e}")

def demo_player_harvest():
    """Demo harvesting photo assets for a player."""
    print("\n--- [Demo 2] Harvesting Player Assets ---")
    out_dir = os.path.expanduser("~/Downloads/demo_player_harvest")
    # Define sample timeline milestones
    sample_milestones = [
        {
            "asset_id": "2297627218",
            "name": "01_2026-09-28_活塞队官方媒体日2号球衣正式定妆横版大片_2297627218",
            "desc": "底特律活塞队身披2号球衣正式定妆大片",
            "date": "2026-09-28"
        }
    ]
    # Harvest only 2 solos for quick demo
    harvest_player_assets(
        player_name="坎宁安",
        en_name="Cade Cunningham",
        output_dir=out_dir,
        milestones=sample_milestones,
        solo_count=2
    )

if __name__ == "__main__":
    demo_single_restore()
