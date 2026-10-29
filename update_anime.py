
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



def get_stream_url():
    import uuid

    print("Запрашиваю поток «Наше Аниме»...")

    with requests.Session() as session:
        # Сначала открываем страницу, чтобы получить cookies.
        page = session.get(
            "https://rutube.ru/",
            headers={
                "User-Agent": HEADERS["User-Agent"],
                "Accept": "text/html,application/xhtml+xml",
            },
            timeout=30,
        )
        print(f"Страница RUTUBE: HTTP {page.status_code}")

        params = {
            "no_404": "true",
            # Двойное кодирование соответствует наблюдавшемуся
            # в браузере формату параметра referer.
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

        headers = {
            **HEADERS,
            "Referer": "https://rutube.ru/",
            "Origin": "https://rutube.ru",
        }

        response = session.get(
            API_URL,
            params=params,
            headers=headers,
            timeout=30,
        )

        print(f"Наше Аниме: HTTP {response.status_code}")

        try:
            data = response.json()
        except ValueError:
            raise RuntimeError(
                f"RUTUBE вернул не JSON: {response.text[:300]}"
            )

        if response.status_code != 200:
            raise RuntimeError(
                f"API недоступен: HTTP {response.status_code}; "
                f"ответ: {json.dumps(data, ensure_ascii=False)[:500]}. "
                "Старый плейлист не изменён."
            )

        detail = data.get("detail")
        if isinstance(detail, dict) and detail.get("type") == "blocking_rule":
            raise RuntimeError(
                "RUTUBE заблокировал запрос (blocking_rule). "
                "Старый плейлист не изменён."
            )

        streams = data.get("live_streams") or {}
        hls = streams.get("hls", [])

        if isinstance(hls, dict):
            hls = list(hls.values())
        elif isinstance(hls, str):
            hls = [hls]

        for item in hls:
            url = item if isinstance(item, str) else (
                item.get("url") if isinstance(item, dict) else None
            )
            if isinstance(url, str) and url.startswith("https://"):
                return url

        raise RuntimeError(
            "RUTUBE ответил, но ссылка HLS не найдена. "
            f"Ключи ответа: {list(data.keys())}"
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
