"""
NBA Media Harvester
===================
Intelligent visual asset harvesting, 2048px watermark restoration,
and YouTube documentary footage collection suite for NBA & sports documentaries.
"""

from .watermark_restorer import restore_watermark, restore_by_asset_id
from .getty_harvester import harvest_player_assets, search_getty_editorial, parse_photo_metadata
from .youtube_harvester import harvest_player_videos, search_youtube_videos

__all__ = [
    "restore_watermark",
    "restore_by_asset_id",
    "harvest_player_assets",
    "search_getty_editorial",
    "parse_photo_metadata",
    "harvest_player_videos",
    "search_youtube_videos",
]
