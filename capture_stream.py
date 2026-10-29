```python
import os
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

PLAYLIST = Path(__file__).with_name("anime.m3u")
BRAVE = r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe"

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


def capture_stream(browser, channel):
    video_id = channel["id"]
    page_url = f"https://rutube.ru/live/video/{video_id}/"
    page = browser.new_page()
    found = []

    def on_request(request):
        url = request.url.lower()

        if (
            ".m3u8" in url
            and video_id in url
            and "rtbcdn.ru" in url
        ):
            found.append(request.url)

    page.on("request", on_request)

    try:
        print(f"\nOpening: {channel['name']}", flush=True)

        page.goto(
            page_url,
            wait_until="domcontentloaded",
            timeout=60000,
        )

        for _ in range(180):
            page.wait_for_timeout(1000)

            if found:
                print(
                    f"Stream captured: {channel['name']}",
                    flush=True,
                )
                return found[0]

        raise RuntimeError(
            f"Stream not found: {channel['name']}"
        )

    except PlaywrightTimeoutError as error:
        raise RuntimeError(
            f"Timed out: {channel['name']}"
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
                urls[channel["id"]] = capture_stream(
                    browser,
                    channel,
                )
        finally:
            browser.close()

    if len(urls) != len(CHANNELS):
        raise RuntimeError(
            "Not all streams were captured; playlist unchanged."
        )

    update_playlist(urls)

    print("\nSUCCESS: both stream URLs updated.")
    print("Playlist saved as UTF-8 with readable Russian names.")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"\nERROR: {error}", file=sys.stderr)
        print(
            "Playlist was not rewritten unless update had completed.",
            file=sys.stderr,
        )
        sys.exit(1)
```
