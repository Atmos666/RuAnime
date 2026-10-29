
import json
import sys
from pathlib import Path

import requests

VIDEO_ID = "ec5267347fa50d03edba227906eba679"
PAGE_URL = f"https://rutube.ru/live/video/{VIDEO_ID}/"

API_URL = (
    f"https://rutube.ru/api/play/options/{VIDEO_ID}/"
    "?format=json&no_404=true"
)

OUTPUT_FILE = Path("anime.m3u")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json",
    "Referer": PAGE_URL,
}


def get_stream_url():
    print("Запрашиваю актуальный поток RUTUBE...")

    response = requests.get(
        API_URL,
        headers=HEADERS,
        timeout=25,
    )

    print(f"HTTP status: {response.status_code}")

    try:
        data = response.json()
    except ValueError:
        raise RuntimeError(
            "RUTUBE вернул не JSON. "
            f"Ответ: {response.text[:300]}"
        )

    # В том числе обрабатываем блокировку RUTUBE
    if response.status_code != 200:
        detail = data.get("detail", data)
        raise RuntimeError(
            f"RUTUBE вернул HTTP {response.status_code}: "
            f"{json.dumps(detail, ensure_ascii=False)[:500]}"
        )

    if isinstance(data.get("detail"), dict):
        detail = data["detail"]
        if detail.get("type") == "blocking_rule":
            raise RuntimeError(
                "RUTUBE заблокировал API-запрос. "
                "GitHub Actions не сможет обновить ссылку "
                "этим способом, пока запросы отклоняются."
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

    # Иногда API может вернуть другую структуру
    print("Не найдены live_streams.hls.")
    print("Ключи ответа:", list(data.keys()))

    raise RuntimeError(
        "Прямая ссылка на HLS-поток не найдена."
    )


def main():
    try:
        stream_url = get_stream_url()

        playlist = (
            "#EXTM3U\n"
            "#EXTINF:-1 tvg-name=\"Наше Аниме\" "
            "group-title=\"Аниме\",Наше Аниме\n"
            f"{stream_url}\n"
        )

        OUTPUT_FILE.write_text(playlist, encoding="utf-8")

        print(f"Плейлист обновлён: {OUTPUT_FILE.resolve()}")

    except Exception as error:
        print(f"ОШИБКА: {error}")
        sys.exit(1)


if __name__ == "__main__":
    main()
