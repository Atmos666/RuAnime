
import json
import os
import sys
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright

BRAVE = (
    r"C:\Program Files\BraveSoftware\Brave-Browser"
    r"\Application\brave.exe"
)

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


def inspect_response(response, channel_id):
    url = response.url
    path = urlparse(url).path.lower()

    relevant = (
        f"/api/v2/video/stream/{channel_id}/info/" in path
        or "/api/play/options/" in path
        or "/api/v2/video/stream/tvbroadcastinfo" in path
    )

    if not relevant:
        return

    print("\n" + "=" * 70, flush=True)
    print(f"API URL: {url.split('?', 1)[0]}", flush=True)
    print(f"HTTP STATUS: {response.status}", flush=True)

    try:
        body = response.text()
    except Exception as error:
        print(f"BODY READ ERROR: {error}", flush=True)
        return

    try:
        data = json.loads(body)
        print("JSON RESPONSE:", flush=True)
        print(
            json.dumps(data, ensure_ascii=False, indent=2)[:10000],
            flush=True,
        )
    except json.JSONDecodeError:
        print("TEXT RESPONSE:", flush=True)
        print(body[:5000], flush=True)

    print("=" * 70, flush=True)


def diagnose(browser, channel):
    channel_id = channel["id"]
    page_url = f"https://rutube.ru/live/video/{channel_id}/"

    print("\n" + "#" * 70, flush=True)
    print(f"CHANNEL: {channel['name']}", flush=True)
    print(f"PAGE: {page_url}", flush=True)

    page = browser.new_page()
    seen_urls = set()

    def on_response(response):
        url = response.url
        path = urlparse(url).path.lower()

        if (
            f"/api/v2/video/stream/{channel_id}/info/" in path
            or "/api/play/options/" in path
            or "/api/v2/video/stream/tvbroadcastinfo" in path
        ):
            if url not in seen_urls:
                seen_urls.add(url)
                inspect_response(response, channel_id)

        if (
            "rutube" in urlparse(url).netloc.lower()
            and response.status >= 400
        ):
            print(
                f"HTTP ERROR {response.status}: "
                f"{url.split('?', 1)[0]}",
                flush=True,
            )

    page.on("response", on_response)

    try:
        response = page.goto(
            page_url,
            wait_until="domcontentloaded",
            timeout=90000,
        )

        print(
            f"PAGE STATUS: {response.status if response else 'unknown'}",
            flush=True,
        )
        print(f"FINAL URL: {page.url}", flush=True)

        for second in range(30):
            page.wait_for_timeout(1000)

            if second in (9, 19, 29):
                print(
                    f"Waiting for player/API: {second + 1}/30 seconds",
                    flush=True,
                )

        print(f"PAGE TITLE: {page.title()}", flush=True)

        try:
            print(
                "PAGE TEXT:",
                page.locator("body").inner_text(timeout=10000)[:2000],
                flush=True,
            )
        except Exception as error:
            print(f"PAGE TEXT ERROR: {error}", flush=True)

        print(
            f"RELEVANT API RESPONSES: {len(seen_urls)}",
            flush=True,
        )

        print("Trying to inspect video/player elements...", flush=True)
        try:
            elements = page.locator(
                "video, iframe, [class*='player'], "
                "[class*='Player'], [data-testid*='player']"
            )
            count = min(elements.count(), 20)

            for index in range(count):
                element = elements.nth(index)
                try:
                    print(
                        f"ELEMENT {index}: "
                        f"{element.evaluate('el => el.tagName')} "
                        f"{element.get_attribute('class')} "
                        f"src={element.get_attribute('src')}",
                        flush=True,
                    )
                except Exception:
                    pass
        except Exception as error:
            print(f"ELEMENT INSPECTION ERROR: {error}", flush=True)

    except Exception as error:
        print(
            f"DIAGNOSTIC ERROR: {type(error).__name__}: {error}",
            flush=True,
        )
    finally:
        page.close()


def main():
    is_github = os.getenv("GITHUB_ACTIONS") == "true"

    with sync_playwright() as playwright:
        if is_github:
            browser = playwright.chromium.launch(headless=True)
        else:
            browser = playwright.chromium.launch(
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
        print(f"FATAL ERROR: {type(error).__name__}: {error}", file=sys.stderr)
        sys.exit(1)
