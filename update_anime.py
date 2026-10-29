
import json
import sys
import uuid
from pathlib import Path

import requests

OUTPUT_FILE = Path("anime.m3u")
API_URL = "https://rutube.ru/api/play/options/{video_id}/"

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


def read_existing():
    result = {}
    if not OUTPUT_FILE.exists():
        return result

    current_name = None

    for line in OUTPUT_FILE.read_text(
        encoding="utf-8-sig"
    ).splitlines():
        line = line.strip()

        if line.startswith("#EXTINF"):
            current_name = next(
                (
                    channel["name"]
                    for channel in CHANNELS
                    if channel["name"] in line
                    or channel["tvg"] in line
                ),
                None,
            )
        elif line and not line.startswith("#") and current_name:
            result[current_name] = line
            current_name = None

    return result


def get_stream_url(session, channel):
    video_id = channel["id"]
    page_url = f"https://rutube.ru/live/video/{video_id}/"

    print(f"Запрашиваю: {channel['name']}")

    session.get(
        "https://rutube.ru/",
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml",
        },
        timeout=30,
    )

    params = {
        "no_404": "true",
        "referer": "https%3A%2F%2Frutube.ru",
        "pver": "v2",
        "client": "wdp",
        "mq": "all",
        "av1": "1",
        "ac_client": "web",
        "ver": "358.0.2",
        "ad_ver": "v2",
        "cvid": uuid.uuid4().hex,
        "ac_request_id": str(uuid.uuid4()),
    }

    response = session.get(
        API_URL.format(video_id=video_id),
        params=params,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/json, text/plain, */*",
            "Referer": page_url,
            "Origin": "https://rutube.ru",
        },
        timeout=30,
    )

    print(f"{channel['name']}: HTTP {response.status_code}")

    try:
        data = response.json()
    except ValueError:
        raise RuntimeError(
            f"{channel['name']}: ответ не JSON: "
            f"{response.text[:300]}"
        )

    if response.status_code != 200:
        raise RuntimeError(
            f"{channel['name']}: HTTP {response.status_code}; "
            f"{json.dumps(data, ensure_ascii=False)[:500]}"
        )

    detail = data.get("detail")
    if isinstance(detail, dict) and detail.get("type") == "blocking_rule":
        raise RuntimeError(
            f"{channel['name']}: RUTUBE blocking_rule"
        )

    streams = data.get("live_streams") or {}
    hls = streams.get("hls", [])

    if isinstance(hls, dict):
        hls = list(hls.values())
    elif isinstance(hls, str):
        hls = [hls]

    for item in hls:
        url = (
            item if isinstance(item, str)
            else item.get("url") if isinstance(item, dict)
            else None
        )
        if isinstance(url, str) and url.startswith("https://"):
            return url

    raise RuntimeError(
        f"{channel['name']}: HLS-ссылка не найдена; "
        f"ключи ответа: {list(data.keys())}"
    )


def main():
    old_urls = read_existing()
    new_urls = {}

    with requests.Session() as session:
        for channel in CHANNELS:
            new_urls[channel["name"]] = get_stream_url(
                session, channel
            )

    # Не заменяем плейлист, если какой-то канал отсутствует.
    if len(new_urls) != len(CHANNELS):
        raise RuntimeError("Получены не все ссылки. Плейлист не изменён.")

    lines = ["#EXTM3U"]

    for channel in CHANNELS:
        url = new_urls[channel["name"]]
        lines.append(
            f'#EXTINF:-1 {channel["tvg"]} '
            f'group-title="Аниме",{channel["name"]}'
        )
        lines.append(url)

    temp_file = OUTPUT_FILE.with_suffix(".m3u.tmp")
    temp_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
    temp_file.replace(OUTPUT_FILE)

    print("Оба потока получены. Плейлист обновлён.")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"ОШИБКА: {error}", file=sys.stderr)
        sys.exit(1)
