#!/usr/bin/env python3
"""
NBA Media Harvester - YouTube Documentary & B-Roll Harvester
============================================================
Automated search and batch downloader for NBA player non-game documentary footage:
- Draft night podium walk & official jersey unveilings
- Offseason private high-intensity workouts (Chris Johnson, Rico Hines, Drew Hanlen)
- Official press conferences & media day interviews
- In-depth player podcasts & player-to-player conversations
- Mic'd up court-side & trophy presentations

Powered by yt-dlp with automatic MP4 merging and chapter categorization.
"""

import os
import sys
import json
import shutil
import urllib.parse
import urllib.request
import argparse
import subprocess

def search_youtube_videos(query: str, max_results: int = 5) -> list:
    """Search YouTube and extract video metadata without API key."""
    url = f"https://www.youtube.com/results?search_query={urllib.parse.quote(query)}"
    headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=12) as resp:
            html = resp.read().decode("utf-8", errors="ignore")
    except Exception as e:
        print(f"Error querying YouTube: {e}")
        return []

    import re
    m = re.search(r'var ytInitialData = ({.*?});</script>', html) or re.search(r'ytInitialData = ({.*?});', html)
    if not m:
        return []

    try:
        data = json.loads(m.group(1))
        contents = data['contents']['twoColumnSearchResultsRenderer']['primaryContents']['sectionListRenderer']['contents']
        items = []
        for c in contents:
            item_sec = c.get('itemSectionRenderer', {})
            for it in item_sec.get('contents', []):
                vr = it.get('videoRenderer')
                if vr:
                    vid = vr.get('videoId')
                    title = ''.join([t['text'] for t in vr.get('title', {}).get('runs', [])])
                    channel = ''.join([t['text'] for t in vr.get('ownerText', {}).get('runs', [])])
                    dur = vr.get('lengthText', {}).get('simpleText', '')
                    if vid and title:
                        items.append({
                            "id": vid,
                            "url": f"https://www.youtube.com/watch?v={vid}",
                            "title": title,
                            "channel": channel,
                            "duration": dur
                        })
                        if len(items) >= max_results:
                            return items
        return items
    except Exception as e:
        print(f"Error parsing YouTube JSON: {e}")
        return []

def download_video_item(video_url: str, output_path: str, retries: int = 5) -> bool:
    """Download single video at best resolution up to 1080P/4K merged into MP4."""
    if os.path.exists(output_path) and os.path.getsize(output_path) > 1024 * 1024:
        size_mb = os.path.getsize(output_path) / (1024 * 1024)
        print(f"  ✅ 文件已存在且完整，跳过: {os.path.basename(output_path)} ({size_mb:.1f} MB)")
        return True

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    cmd = [
        "yt-dlp",
        "-f", "bv*+ba/b",
        "--merge-output-format", "mp4",
        "--no-playlist",
        "--continue",
        "--retries", str(retries),
        "--fragment-retries", str(retries),
        "-o", output_path,
        video_url
    ]

    print(f"  📥 正在下载: {os.path.basename(output_path)}")
    res = subprocess.run(cmd)
    if res.returncode == 0 and os.path.exists(output_path):
        size_mb = os.path.getsize(output_path) / (1024 * 1024)
        print(f"  🎉 下载成功: {os.path.basename(output_path)} ({size_mb:.1f} MB)")
        return True
    else:
        print(f"  ❌ 下载失败 (exit code {res.returncode})")
        return False

def harvest_player_videos(
    player_name: str,
    en_name: str,
    base_dir: str,
    tasks: list = None
):
    """
    Harvest player documentary video clips across narrative chapters.
    """
    os.makedirs(base_dir, exist_ok=True)
    print(f"🎬 开始采编: {player_name} ({en_name}) 精选视频素材...")

    if not tasks:
        # Generate default curated tasks across 4 core documentary angles
        tasks = [
            # 章节一：选秀与生涯起点
            {
                "cat": "01_关键词一_顺位起点",
                "name": f"01_{player_name}_选秀首轮大会宣布与登台致辞.mp4",
                "query": f"{en_name} NBA Draft pick announcement speech"
            },
            {
                "cat": "01_关键词一_顺位起点",
                "name": f"02_{player_name}_官方新秀亮相发布会手持战袍.mp4",
                "query": f"{en_name} rookie introductory press conference"
            },
            # 章节二：拼搏特训与自律
            {
                "cat": "02_关键词二_拼搏自律",
                "name": f"01_{player_name}_休赛期私人魔鬼特训原片.mp4",
                "query": f"{en_name} private offseason workout Chris Johnson"
            },
            {
                "cat": "02_关键词二_拼搏自律",
                "name": f"02_{player_name}_对抗终结与投篮专项细节打磨.mp4",
                "query": f"{en_name} basketball workout drills 4K"
            },
            # 章节三：球风与技术特写
            {
                "cat": "03_关键词三_招牌球风",
                "name": f"01_{player_name}_技术动作慢动作细节分解.mp4",
                "query": f"{en_name} slow motion highlights 4K 60fps"
            },
            # 章节四：专访播客与领袖门面
            {
                "cat": "04_关键词四_领袖门面",
                "name": f"01_{player_name}_球员官方媒体日深度采访.mp4",
                "query": f"{en_name} media day interview"
            },
            {
                "cat": "04_关键词四_领袖门面",
                "name": f"02_{player_name}_长篇播客对谈生涯转折.mp4",
                "query": f"{en_name} podcast interview Paul George OR Redick"
            }
        ]

    downloaded_records = []
    for idx, t in enumerate(tasks, 1):
        target_dir = os.path.join(base_dir, t.get("cat", "未分类素材"))
        os.makedirs(target_dir, exist_ok=True)
        target_file = os.path.join(target_dir, t["name"])

        video_url = t.get("url")
        if not video_url and "query" in t:
            print(f"\n🔍 [{idx}/{len(tasks)}] 正在检索最佳原片: {t['query']}")
            results = search_youtube_videos(t["query"], max_results=3)
            if results:
                video_url = results[0]["url"]
                print(f"  🎯 命中最佳候选: {results[0]['title']} ({results[0]['channel']} | {results[0]['duration']})")
            else:
                print(f"  ⚠️ 未检索到可用结果: {t['query']}")
                continue

        if video_url:
            success = download_video_item(video_url, target_file)
            if success:
                size_mb = os.path.getsize(target_file) / (1024 * 1024) if os.path.exists(target_file) else 0
                downloaded_records.append({
                    "cat": t.get("cat", "未分类"),
                    "name": t["name"],
                    "path": target_file,
                    "url": video_url,
                    "size_mb": size_mb
                })

    # Generate Markdown Catalog
    catalog_path = os.path.join(base_dir, f"{player_name}_精选视频素材清单.md")
    print(f"\n📝 正在生成视频素材清单: {catalog_path} ...")
    with open(catalog_path, "w", encoding="utf-8") as f:
        f.write(f"# {player_name} ({en_name}) 精选纪录片视频素材索引\n\n")
        f.write("> **规格说明**：聚焦非比赛、高反差纪实素材（选秀盛典、私人特训、长篇播客、赛后发布会），最高画质合并立体声原声，提供即开即用的剪辑工程物料。\n\n")
        f.write("| 章节分类 | 素材文件名 | 文件体积 | 原始视频链接 |\n")
        f.write("| :--- | :--- | :---: | :--- |\n")
        for rec in downloaded_records:
            f.write(f"| {rec['cat']} | [`{rec['name']}`](file://{rec['path']}) | **{rec['size_mb']:.1f} MB** | [YouTube]({rec['url']}) |\n")

    print(f"✨ 全部视频素材采编完成！已存至: {base_dir}")
    print(f"📄 清单已生成: {catalog_path}")
    return catalog_path

def main():
    parser = argparse.ArgumentParser(description="NBA Media Harvester - YouTube Documentary Video Harvester")
    parser.add_argument("--player", required=True, help="Player Chinese name (e.g. '沃克·凯斯勒')")
    parser.add_argument("--en-name", required=True, help="Player English name (e.g. 'Walker Kessler')")
    parser.add_argument("--out-dir", default=None, help="Output destination folder")
    parser.add_argument("--tasks-json", default=None, help="Path to JSON file containing specific video task definitions")

    args = parser.parse_args()
    out_dir = args.out_dir or os.path.expanduser(f"~/Downloads/{args.player}_精选视频素材")

    tasks = None
    if args.tasks_json and os.path.exists(args.tasks_json):
        with open(args.tasks_json, "r", encoding="utf-8") as f:
            tasks = json.load(f)

    harvest_player_videos(
        player_name=args.player,
        en_name=args.en_name,
        base_dir=out_dir,
        tasks=tasks
    )

if __name__ == "__main__":
    main()
