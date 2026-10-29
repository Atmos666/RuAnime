
import os
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

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

IS_GITHUB = os.getenv("GITHUB_ACTIONS") == "true"

BRAVE_WINDOWS = (
    r"C:\Program Files\BraveSoftware\Brave-Browser"
    r"\Application\brave.exe"
)
BRAVE_LINUX = "/usr/bin/brave-browser"


def capture_stream(browser, channel):
    video_id = channel["id"]
    page_url = f"https://rutube.ru/live/video/{video_id}/"

    page = browser.new_page()
    found = []
    blocked = []

    def on_request(request):
        url = request.url.lower()

        if (
            ".m3u8" in url
            and video_id in url
            and "rtbcdn.ru" in url
        ):
            if request.url not in found:
                found.append(request.url)
                print(
                    f"STREAM CAPTURED: {channel['name']}",
                    flush=True,
                )

    def on_response(response):
        url = response.url
        if "/api/play/options/" in url:
            print(
                f"PLAYER API STATUS: {response.status} "
                f"({channel['name']})",
                flush=True,
            )
            if response.status == 244:
                blocked.append(response.status)

    page.on("request", on_request)
    page.on("response", on_response)

    try:
        print(f"\nOpening: {channel['name']}", flush=True)
        print(f"Browser: {'Brave on GitHub' if IS_GITHUB else 'Local Brave'}", flush=True)

        response = page.goto(
            page_url,
            wait_until="domcontentloaded",
            timeout=60000,
        )

        print(
            f"PAGE STATUS: {response.status if response else 'unknown'}",
            flush=True,
        )

        for _ in range(180):
            page.wait_for_timeout(1000)

            if found:
                return found[0]

        if blocked:
            raise RuntimeError(
                f"RUTUBE blocked the player API for {channel['name']} "
                f"(HTTP 244); no stream URL was captured."
            )

        raise RuntimeError(
            f"Stream not found for {channel['name']} after 180 seconds."
        )

    except PlaywrightTimeoutError as error:
        raise RuntimeError(
            f"Timed out while opening {channel['name']}."
        ) from error

    finally:
        page.close()


def update_playlist(urls):
    lines = ["#EXTM3U"]

    for channel in CHANNELS:
        url = urls[channel["id"]]
        lines.append(
            f'#EXTINF:-1 {channel["tvg"]} '
            f'group-title="Аниме",{channel["name"]}'
        )
        lines.append(url)
        lines.append("")

    content = "\n".join(lines).rstrip() + "\n"
    temp = PLAYLIST.with_suffix(".m3u.tmp")
    temp.write_text(content, encoding="utf-8")
    os.replace(temp, PLAYLIST)


def main():
    urls = {}

    with sync_playwright() as p:
        if IS_GITHUB:
            browser = p.chromium.launch(
                executable_path=BRAVE_LINUX,
                headless=True,
                args=["--no-sandbox", "--disable-dev-shm-usage"],
            )
        else:
            browser = p.chromium.launch(
                executable_path=BRAVE_WINDOWS,
                headless=False,
            )

        try:
            for channel in CHANNELS:
                urls[channel["id"]] = capture_stream(browser, channel)
        finally:
            browser.close()

    if len(urls) != len(CHANNELS):
        raise RuntimeError(
            "Not all streams were captured; playlist unchanged."
        )

    update_playlist(urls)

    print("\nSUCCESS: both stream URLs updated.", flush=True)
    print("Playlist saved as UTF-8.", flush=True)


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"\nERROR: {error}", file=sys.stderr, flush=True)
        print(
            "Playlist was not rewritten unless the update completed.",
            file=sys.stderr,
            flush=True,
        )
        sys.exit(1)
