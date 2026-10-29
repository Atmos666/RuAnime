
import json
import sys
import urllib.request
import urllib.error
from urllib.parse import urlencode

VIDEO_ID = "ec5267347fa50d03edba227906eba679"
PAGE_URL = f"https://rutube.ru/live/video/{VIDEO_ID}/"

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

def show_structure(obj, path="$", depth=0):
    if depth > 5:
        return

    if isinstance(obj, dict):
        for key, value in obj.items():
            current = f"{path}.{key}"
            print(f"{current}: {type(value).__name__}")

            if isinstance(value, (dict, list)):
                show_structure(value, current, depth + 1)

    elif isinstance(obj, list):
        print(f"{path}: list length={len(obj)}")
        if obj:
            show_structure(obj[0], f"{path}[0]", depth + 1)

try:
    request = urllib.request.Request(api_url, headers=headers)

    with urllib.request.urlopen(request, timeout=30) as response:
        status = response.status
        content_type = response.headers.get("Content-Type", "")
        body = response.read()

    print(f"HTTP status: {status}")
    print(f"Content-Type: {content_type}")
    print(f"Response size: {len(body)} bytes")

    try:
        data = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        print("Response is not valid JSON.")
        print("Check whether the server returned HTML or an access error.")
        sys.exit(1)

    print("JSON structure:")
    show_structure(data)

    streams = data.get("live_streams", {}).get("hls", [])

    if isinstance(streams, list):
        urls = [
            item["url"]
            for item in streams
            if isinstance(item, dict) and item.get("url")
        ]
    elif isinstance(streams, str) and streams.startswith("https://"):
        urls = [streams]
    else:
        urls = []

    if not urls:
        print("No HLS URL found at live_streams.hls.")
        sys.exit(1)

    playlist = (
        "#EXTM3U\n"
        "#EXTINF:-1,Our Anime\n"
        f"{urls[0]}\n"
    )

    with open("anime.m3u", "w", encoding="utf-8") as file:
        file.write(playlist)

    print("Playlist generated successfully.")

except urllib.error.HTTPError as error:
    print(f"HTTP error: {error.code}")
    print(f"Content-Type: {error.headers.get('Content-Type', '')}")
    print("The server refused or rejected the API request.")
    sys.exit(1)

except Exception as error:
    print(f"Request failed: {type(error).__name__}: {error}")
    sys.exit(1)
