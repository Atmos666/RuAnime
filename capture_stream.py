
import json
import os
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

PLAYLIST = Path(__file__).with_name("anime.m3u")
BRAVE_LINUX = "/usr/bin/brave-browser"

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

def capture_stream(context, channel):
    video_id = channel["id"]
    page_url = f"https://rutube.ru/live/video/{video_id}/"
    page = context.new_page()
    found = []
    api_statuses = []

    def on_request(request):
        url = request.url.lower()
        if ".m3u8" in url and video_id in url and "rtbcdn.ru" in url:
            if request.url not in found:
                found.append(request.url)

    def on_response(response):
        url = response.url.lower()

        if "/api/play/options/" in url and video_id in url:
            api_statuses.append(response.status)
            print(f"PLAYER API STATUS: {response.status} ({channel['name']})")

            if response.status == 244:
                try:
                    data = response.json()
                    detail = data.get("detail", data)
                    print("RUTUBE BLOCK DETAILS:")
                    print(json.dumps(detail, ensure_ascii=False, indent=2)[:5000])
                except Exception as error:
                    print(f"Could not read block response: {error}")

        if ".m3u8" in url and video_id in url and "rtbcdn.ru" in url:
            print(f"M3U8 RESPONSE: {response.status} ({channel['name']})")

    page.on("request", on_request)
    page.on("response", on_response)

    try:
        print(f"\nOpening: {channel['name']}")
        response = page.goto(
            page_url,
            wait_until="domcontentloaded",
            timeout=60000,
        )
        print(f"PAGE STATUS: {response.status if response else 'unknown'}")

        for _ in range(90):
            page.wait_for_timeout(1000)
            if found:
                print(f"STREAM CAPTURED: {channel['name']}")
                return found[0]

        if 244 in api_statuses:
            raise RuntimeError(
                f"RUTUBE returned HTTP 244 for {channel['name']}; "
                "see RUTUBE BLOCK DETAILS above."
            )

        raise RuntimeError(
            f"No HLS stream captured for {channel['name']}. "
            f"API statuses: {api_statuses}"
        )
    except PlaywrightTimeoutError as error:
        raise RuntimeError(f"Timed out loading {channel['name']}") from error
    finally:
        page.close()

def update_playlist(urls):
    lines = ["#EXTM3U"]

    for channel in CHANNELS:
        url = urls[channel["id"]]
        lines.append(
            f'#EXTINF:-1 {channel["tvg"]} group-title="Аниме",'
            f'{channel["name"]}'
        )
        lines.append(url)
        lines.append("")

    content = "\n".join(lines).rstrip() + "\n"
    temp = PLAYLIST.with_suffix(".m3u.tmp")
    temp.write_text(content, encoding="utf-8")
    os.replace(temp, PLAYLIST)

def main():
    if not Path(BRAVE_LINUX).exists():
        raise RuntimeError(f"Brave not found at {BRAVE_LINUX}")

    urls = {}

    with sync_playwright() as p:
        browser = p.chromium.launch(
            executable_path=BRAVE_LINUX,
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-blink-features=AutomationControlled",
                "--lang=ru-RU",
            ],
        )

        context = browser.new_context(
            locale="ru-RU",
            timezone_id="Europe/Moscow",
            user_agent=(
                "Mozilla/5.0 (X11; Linux x86_64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/131.0.0.0 Safari/537.36"
            ),
            extra_http_headers={
                "Accept-Language": "ru-RU,ru;q=0.9",
            },
        )

        try:
            for channel in CHANNELS:
                urls[channel["id"]] = capture_stream(context, channel)
        finally:
            context.close()
            browser.close()

    if len(urls) != len(CHANNELS):
        raise RuntimeError("Not all streams captured; playlist not updated.")

    update_playlist(urls)
    print("\nSUCCESS: both stream URLs updated.")
    print(f"Playlist: {PLAYLIST}")

if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"\nERROR: {error}", file=sys.stderr)
        print("Existing playlist was not overwritten.")
        sys.exit(1)
