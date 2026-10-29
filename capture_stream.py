import os
import sys
from pathlib import Path
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright

BRAVE = r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe"

CHANNELS = [
    {
        "id": "ec5267347fa50d03edba227906eba679",
        "name": "Наше Аниме",
    },
    {
        "id": "b3019a8983105f5e33f038246f860c32",
        "name": "Анимач — аниме онлайн",
    },
]


def diagnose(browser, channel):
    video_id = channel["id"]
    page_url = f"https://rutube.ru/live/video/{video_id}/"
    page = browser.new_page()
    requests_seen = 0
    stream_candidates = []

    def on_request(request):
        nonlocal requests_seen
        url = request.url
        host = urlparse(url).netloc.lower()

        if "rutube" in host or "rtbcdn" in host:
            requests_seen += 1

            if any(word in url.lower() for word in (
                ".m3u8", ".mpd", ".m4s", ".ts", "hls", "stream"
            )):
                safe_url = url.split("?", 1)[0]
                stream_candidates.append(safe_url)
                print(f"MEDIA REQUEST: {safe_url}", flush=True)

    def on_response(response):
        host = urlparse(response.url).netloc.lower()
        if "rutube" in host and response.status >= 400:
            print(
                f"HTTP ERROR {response.status}: "
                f"{response.url.split('?', 1)[0]}",
                flush=True,
            )

    def on_page_error(error):
        print(f"PAGE JS ERROR: {error}", flush=True)

    page.on("request", on_request)
    page.on("response", on_response)
    page.on("pageerror", on_page_error)

    try:
        print(f"\n=== DIAGNOSIS: {channel['name']} ===", flush=True)
        print(f"Opening: {page_url}", flush=True)

        response = page.goto(
            page_url,
            wait_until="domcontentloaded",
            timeout=90000,
        )

        print(
            f"PAGE RESPONSE: {response.status if response else 'none'}",
            flush=True,
        )
        print(f"FINAL URL: {page.url}", flush=True)

        for _ in range(45):
            page.wait_for_timeout(1000)

        print(f"PAGE TITLE: {page.title()}", flush=True)
        print(f"RUTUBE REQUEST COUNT: {requests_seen}", flush=True)
        print(f"MEDIA CANDIDATES: {len(stream_candidates)}", flush=True)

        screenshot = Path(f"diagnostic-{video_id}.png")
        page.screenshot(path=str(screenshot), full_page=True)
        print(f"SCREENSHOT SAVED: {screenshot}", flush=True)

        text = page.locator("body").inner_text(timeout=10000)
        print("PAGE TEXT:", flush=True)
        print(text[:2500], flush=True)

    except Exception as error:
        print(
            f"DIAGNOSTIC ERROR for {channel['name']}: "
            f"{type(error).__name__}: {error}",
            flush=True,
        )

    finally:
        page.close()


def main():
    is_github = os.getenv("GITHUB_ACTIONS") == "true"

    with sync_playwright() as p:
        if is_github:
            browser = p.chromium.launch(headless=True)
        else:
            browser = p.chromium.launch(
                executable_path=BRAVE,
                headless=False,
            )

        try:
            for channel in CHANNELS:
                diagnose(browser, channel)
        finally:
            browser.close()


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"FATAL ERROR: {error}", file=sys.stderr)
        sys.exit(1)
