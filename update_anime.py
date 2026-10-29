
import json
import sys
from pathlib import Path
from urllib.parse import urlencode

import requests

OUTPUT_FILE = Path("anime.m3u")

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

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
}


def read_existing():
    """Сохраняем прежние URL как резерв, если API недоступен."""
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
                    c["name"]
                    for c in CHANNELS
                    if c["name"] in line
                    or c["tvg"] in line
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

    params = {
        "format": "json",
        "no_404": "true",
    }

    headers = {
        **HEADERS,
        "Referer": page_url,
    }

    response = session.get(
        f"https://rutube.ru/api/play/options/{video_id}/",
        params=params,
        headers=headers,
        timeout=30,
    )

    print(f'{channel["name"]}: HTTP {response.status_code}')

    if response.status_code != 200:
        raise RuntimeError(
            f'API недоступен для {channel["name"]}: '
            f'HTTP {response.status_code}; '
            "старый плейлист не будет перезаписан."
        )

    data = response.json()

    if isinstance(data.get("detail"), dict):
        if data["detail"].get("type") == "blocking_rule":
            raise RuntimeError(
                "RUTUBE вернул blocking_rule. "
                "Плейлист оставлен без изменений."
            )

    streams = data.get("live_streams", {})
    hls = streams.get("hls", [])

    if isinstance(hls, dict):
        hls = list(hls.values())

    for stream in hls:
        if isinstance(stream, dict):
            url = stream.get("url")
            if url and url.startswith("https://"):
                return url

    raise RuntimeError(
        f'В API не найден HLS-поток: {channel["name"]}'
    )


def main():
    old_urls = read_existing()
    new_urls = {}

    with requests.Session() as session:
        # Сначала получаем все ссылки. Файл пока не трогаем.
        for channel in CHANNELS:
            new_urls[channel["name"]] = get_stream_url(
                session, channel
            )

    # Записываем только если оба канала обновились успешно.
    lines = ["#EXTM3U"]

    for channel in CHANNELS:
        url = new_urls[channel["name"]]
        lines.append(
            f'#EXTINF:-1 {channel["tvg"]} '
            f'group-title="Аниме",{channel["name"]}'
        )
        lines.append(url)

    OUTPUT_FILE.write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )

    print("Оба потока получены. Плейлист обновлён.")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"ОШИБКА: {error}")
        sys.exit(1)
