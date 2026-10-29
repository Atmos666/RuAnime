
import json
import os
import sys
from pathlib import Path

import yt_dlp

PLAYLIST = Path(__file__).with_name("anime.m3u")

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


def get_stream(channel):
    url = f"https://rutube.ru/live/video/{channel['id']}/?no_404=true"

    options = {
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "skip_download": True,
        "extractor_retries": 1,
        "socket_timeout": 20,
    }

    print(f"\nTesting yt-dlp: {channel['name']}", flush=True)

    try:
        with yt_dlp.YoutubeDL(options) as ydl:
            info = ydl.extract_info(url, download=False)
    except Exception as error:
        print(f"EXTRACTION FAILED: {type(error).__name__}: {error}")
        return None

    if not info:
        print("No video information returned.")
        return None

    formats = info.get("formats") or []

    hls_formats = [
        item for item in formats
        if item.get("url")
        and (
            "m3u8" in (item.get("protocol") or "").lower()
            or ".m3u8" in item["url"].lower()
        )
    ]

    if not hls_formats:
        print("No HLS format found.")
        print("Available formats:")
        for item in formats[:15]:
            print(
                f"  id={item.get('format_id')} "
                f"protocol={item.get('protocol')} "
                f"ext={item.get('ext')}"
            )
        return None

    hls_formats.sort(
        key=lambda item: (
            item.get("height") or 0,
            item.get("tbr") or 0,
        )
    )

    chosen = hls_formats[-1]
    stream_url = chosen["url"]

    print("HLS FOUND")
    print(f"Format: {chosen.get('format_id')}")
    print(f"Protocol: {chosen.get('protocol')}")
    print(f"Resolution: {chosen.get('height') or 'unknown'}")
    print(f"Title: {info.get('title', channel['name'])}")

    return stream_url


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
    urls = {}

    for channel in CHANNELS:
        stream = get_stream(channel)
        if stream:
            urls[channel["id"]] = stream

    if len(urls) != len(CHANNELS):
        print(
            "\nTEST FAILED: both channels were not extracted. "
            "Existing playlist remains unchanged.",
            file=sys.stderr,
        )
        sys.exit(1)

    update_playlist(urls)
    print("\nSUCCESS: both HLS streams found; playlist updated.")


if __name__ == "__main__":
    main()
