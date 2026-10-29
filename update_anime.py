
import json
import sys
import urllib.request
import urllib.error
from pathlib import Path

VIDEO_ID = "ec5267347fa50d03edba227906eba679"
PAGE_URL = f"https://rutube.ru/live/video/{VIDEO_ID}/"
OUTPUT = Path(__file__).with_name("anime.m3u")

api_url = (
    f"https://rutube.ru/api/play/options/{VIDEO_ID}/"
    "?format=json"
    "&no_404=true"
    "&referer=https%253A%252F%252Frutube.ru%252Ffeeds%252Flive%252F"
    "&pver=v2"
    "&platform=player-carousel"
)

headers = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:131.0) "
        "Gecko/20100101 Firefox/131.0"
    ),
    "Referer": PAGE_URL,
    "Accept": "application/json",
}

try:
    request = urllib.request.Request(api_url, headers=headers)

    with urllib.request.urlopen(request, timeout=30) as response:
        print(f"HTTP status: {response.status}")
        data = json.loads(response.read().decode("utf-8"))

    live_streams = data.get("live_streams") or {}
    hls = live_streams.get("hls") or []

    if isinstance(hls, dict):
        hls = list(hls.values())

    urls = []
    for item in hls:
        if isinstance(item, dict) and item.get("url"):
            urls.append(item["url"])
        elif isinstance(item, str) and item.startswith("https://"):
            urls.append(item)

    if not urls:
        video_balancer = data.get("video_balancer") or {}
        m3u8 = video_balancer.get("m3u8")

        if isinstance(m3u8, str) and m3u8.startswith("https://"):
            urls.append(m3u8)

    if not urls:
        print("No HLS stream found.")
        print("Top-level JSON keys:", list(data.keys()))

        detail = data.get("detail")
        if isinstance(detail, dict):
            print("Detail keys:", list(detail.keys()))
            print("Detail type:", detail.get("type"))
            print("Detail name:", detail.get("name"))

        sys.exit(1)

    playlist = (
        "#EXTM3U\n"
        "#EXTINF:-1,Our Anime\n"
        f"{urls[0]}\n"
    )

    OUTPUT.write_text(playlist, encoding="utf-8")
    print(f"Playlist updated: {OUTPUT}")

except urllib.error.HTTPError as error:
    print(f"HTTP error: {error.code}")
    sys.exit(1)

except Exception as error:
    print(f"Request failed: {type(error).__name__}: {error}")
    sys.exit(1)
