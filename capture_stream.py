
import json
import os
import sys
import traceback
from pathlib import Path
from urllib.request import Request, build_opener, ProxyHandler
from urllib.error import HTTPError, URLError

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

    print(f"\n{'=' * 55}", flush=True)
    print(f"Checking: {channel['name']}", flush=True)
    print(f"Video ID: {video_id}", flush=True)
    print("Starting request...", flush=True)

    request = Request(
        api_url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "ru-RU,ru;q=0.9",
            "Referer": page_url,
        },
    )

    try:
        print(f"Requesting API: {api_url}", flush=True)

        with OPENER.open(request, timeout=60) as response:
            status = response.status
            body = response.read().decode(
                "utf-8",
                errors="replace"
            )

        print(f"Response received: HTTP {status}", flush=True)

    except HTTPError as error:
        status = error.code
        body = error.read().decode(
            "utf-8",
            errors="replace"
        )
        print(f"HTTP ERROR: {status}", flush=True)
        print(body[:4000], flush=True)

    except URLError as error:
        print(f"URL ERROR: {error}", flush=True)
        traceback.print_exc()
        return None

    except Exception as error:
        print(f"REQUEST FAILED: {error}", flush=True)
        traceback.print_exc()
        return None

    print(f"API STATUS: {status}", flush=True)

    try:
        data = json.loads(body)
    except json.JSONDecodeError as error:
        print(f"INVALID JSON: {error}", flush=True)
        print(body[:4000], flush=True)
        return None

    print("RESPONSE KEYS:", list(data.keys()), flush=True)

    if "detail" in data:
        print("RUTUBE BLOCK DETAILS:", flush=True)
        print(
            json.dumps(
                data["detail"],
                ensure_ascii=False,
                indent=2
            )[:4000],
            flush=True
        )
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
        print("No HLS URLs found.", flush=True)
        print(
            json.dumps(
                data,
                ensure_ascii=False,
                indent=2
            )[:5000],
            flush=True
        )
        return None

    print(f"HLS URLS FOUND: {len(urls)}", flush=True)
    print("Stream successfully captured.", flush=True)

    return urls[0]


def get_channel_title(block):
    for line in block:
        if line.startswith("#EXTINF:"):
            if "," in line:
                return line.split(",", 1)[1].strip()
    return None


def replace_stream_url(block, new_url):
    result = list(block)

    for index, line in enumerate(result):
        if line.strip() and not line.lstrip().startswith("#"):
            result[index] = new_url
            return result

    result.append(new_url)
    return result


def update_playlist(urls):
    if PLAYLIST.exists():
        lines = PLAYLIST.read_text(
            encoding="utf-8-sig"
        ).splitlines()
    else:
        lines = ["#EXTM3U"]

    if not lines:
        lines = ["#EXTM3U"]

    if lines[0].strip() != "#EXTM3U":
        lines.insert(0, "#EXTM3U")

    # Разделяем плейлист на вступительную часть и блоки каналов.
    prefix = []
    blocks = []
    current_block = None

    for line in lines:
        if line.startswith("#EXTINF:"):
            if current_block is not None:
                blocks.append(current_block)

            current_block = [line]

        elif current_block is not None:
            current_block.append(line)

        else:
            prefix.append(line)

    if current_block is not None:
        blocks.append(current_block)

    updated_channels = set()

    # Обновляем только два указанных канала.
    for index, block in enumerate(blocks):
        title = get_channel_title(block)

        for channel in CHANNELS:
            channel_id = channel["id"]
            channel_name = channel["name"]

            if title == channel_name and channel_id not in updated_channels:
                blocks[index] = replace_stream_url(
                    block,
                    urls[channel_id]
                )

                updated_channels.add(channel_id)

                print(
                    f"Updated existing channel: {channel_name}",
                    flush=True
                )

                break

    # Если одного из управляемых каналов ещё нет, добавляем его.
    for channel in CHANNELS:
        channel_id = channel["id"]

        if channel_id not in updated_channels:
            blocks.append([
                f'#EXTINF:-1 {channel["tvg"]} '
                f'group-title="Аниме",{channel["name"]}',
                urls[channel_id]
            ])

            print(
                f"Added missing channel: {channel['name']}",
                flush=True
            )

    # Собираем плейлист обратно.
    output = list(prefix)

    for block in blocks:
        output.extend(block)

    content = "\n".join(output).rstrip() + "\n"

    temp = PLAYLIST.with_suffix(".m3u.tmp")
    temp.write_text(content, encoding="utf-8")
    os.replace(temp, PLAYLIST)

    print("Playlist updated without touching other channels.", flush=True)


def main():
    print("Starting RUTUBE stream capture.", flush=True)
    print(f"Using proxy: {PROXY}", flush=True)

    streams = {}

    for channel in CHANNELS:
        try:
            url = get_stream(channel)

            if url:
                streams[channel["id"]] = url
            else:
                print(
                    f"FAILED: {channel['name']} — stream not found.",
                    flush=True
                )

        except Exception as error:
            print(
                f"UNEXPECTED ERROR for {channel['name']}: "
                f"{type(error).__name__}: {error}",
                flush=True
            )
            traceback.print_exc()

    # Не изменяем плейлист, если хотя бы один поток не получен.
    if len(streams) != len(CHANNELS):
        print(
            "\nFAILED: not all streams were found. "
            "Existing playlist was not changed.",
            file=sys.stderr,
            flush=True
        )
        sys.exit(1)

    update_playlist(streams)

    print(
        "\nSUCCESS: managed streams updated. "
        "All other channels preserved.",
        flush=True
    )


if __name__ == "__main__":
    main()
