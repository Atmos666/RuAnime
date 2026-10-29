
import json
import urllib.request
from pathlib import Path
from urllib.parse import urlencode

VIDEO_ID = "ec5267347fa50d03edba227906eba679"
PAGE_URL = f"https://rutube.ru/live/video/{VIDEO_ID}/"
OUTPUT = Path(__file__).with_name("anime.m3u")

api_url = (
    f"https://rutube.ru/api/play/options/{VIDEO_ID}/?"
    + urlencode({
        "format": "json",
        "no_404": "true",
        "referer": PAGE_URL,
    })
)

headers = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/130.0.0.0 Safari/537.36"
    ),
    "Referer": PAGE_URL,
}

try:
    request = urllib.request.Request(api_url, headers=headers)

    with urllib.request.urlopen(request, timeout=20) as response:
        data = json.loads(response.read().decode("utf-8"))

    streams = data.get("live_streams", {}).get("hls", [])

    urls = [
        item["url"]
        for item in streams
        if isinstance(item, dict) and item.get("url")
    ]

    if not urls:
        raise RuntimeError(
            "API did not return live_streams.hls. "
            "The response structure may be different."
        )

    stream_url = urls[0]

    playlist = (
        "#EXTM3U\n"
        "#EXTINF:-1,Our Anime\n"
        f"{stream_url}\n"
    )

    OUTPUT.write_text(playlist, encoding="utf-8")

    print(f"URL updated successfully: {OUTPUT}")
    print("Open anime.m3u in VLC.")

except Exception as error:
    print(f"Failed to update URL: {error}")

input("Press Enter to exit...")
