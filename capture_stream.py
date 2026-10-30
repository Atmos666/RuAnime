
import json
import os
import sys
from pathlib import Path
from urllib.request import Request, build_opener, ProxyHandler
from urllib.error import HTTPError

PLAYLIST = Path(__file__).with_name("anime.m3u")

PROXY = "http://127.0.0.1:10809"

OPENER = build_opener(
    ProxyHandler({
        "http": PROXY,
        "https": PROXY,
    })
)

CHANNELS = [
    {
        "id": "ec5267347fa50d03edba227906eba679",
        "name": "Наше Аниме",
        "tvg": 'tvg-name="Наше Аниме"',
    },
    {
        "id": "b3019a8983105f5e33f038246f860c32",
        "name": "Анимач — аниме онлайн",
        "tvg": 'tvg-id="animach"',
    },
]

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)


def get_stream(channel):
    video_id = channel["id"]
    page_url = f"https://rutube.ru/live/video/{video_id}/"
    api_url = f"https://rutube.ru/api/play/options/{video_id}/"

    request = Request(
        api_url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "ru-RU,ru;q=0.9",
            "Referer": page_url,
        },
    )

    print(f"\nChecking: {channel['name']}", flush=True)

    try:
        with OPENER.open(request, timeout=40) as response:
            status = response.status
            body = response.read().decode(
                "utf-8", errors="replace"
            )

    except HTTPError as error:
        status = error.code
        body = error.read().decode(
            "utf-8", errors="replace"
        )

    except Exception as error:
        print(f"REQUEST FAILED: {error}")
        return None

    print(f"API STATUS: {status}")

    try:
        data = json.loads(body)
    except json.JSONDecodeError:
        print("Invalid JSON response:")
        print(body[:2000])
        return None

    print("RESPONSE KEYS:", list(data.keys()))

    if "detail" in data:
        print("RUTUBE BLOCK DETAILS:")
        print(json.dumps(
            data["detail"],
            ensure_ascii=False,
            indent=2
        )[:4000])
        return None

    urls = []

    live = data.get("live_streams") or {}
    hls = live.get("hls") or []

    if isinstance(hls, list):
        for item in hls:
            if isinstance(item, dict) and item.get("url"):
                urls.append(item["url"])

    balancer = data.get("video_balancer") or {}

    if isinstance(balancer, dict):
        for value in balancer.values():
            if isinstance(value, str) and ".m3u8" in value.lower():
                urls.append(value)

    urls = list(dict.fromkeys(urls))

    if not urls:
        print("No HLS URLs found.")
        print(json.dumps(
            data,
            ensure_ascii=False,
            indent=2
        )[:5000])
        return None

    print(f"HLS URLS FOUND: {len(urls)}")
    return urls[0]


def update_playlist(urls):
    lines = ["#EXTM3U"]

    for channel in CHANNELS:
        lines.append(
            f'#EXTINF:-1 {channel["tvg"]} '
            f'group-title="Аниме",{channel["name"]}'
        )
        lines.append(urls[channel["id"]])

    content = "\n".join(lines) + "\n"

    temp = PLAYLIST.with_suffix(".m3u.tmp")
    temp.write_text(content, encoding="utf-8")
    os.replace(temp, PLAYLIST)


def main():
    streams = {}

    for channel in CHANNELS:
        url = get_stream(channel)

        if url:
            streams[channel["id"]] = url

    if len(streams) != len(CHANNELS):
        print(
            "\nFAILED: not all streams were found. "
            "Existing playlist was not changed.",
            file=sys.stderr,
        )
        sys.exit(1)

    update_playlist(streams)
    print("\nSUCCESS: both streams saved to anime.m3u")


if __name__ == "__main__":
    main()
