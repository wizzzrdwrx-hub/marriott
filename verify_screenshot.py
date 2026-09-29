import asyncio
from playwright.async_api import async_playwright
from pathlib import Path

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()

        root = Path(__file__).resolve().parent
        await page.goto((root / "index.html").as_uri())

        output = root / "verification"
        output.mkdir(exist_ok=True)
        screenshot_path = output / "index_verification.png"

        await page.screenshot(path=screenshot_path, full_page=True)
        print(f"Screenshot saved to {screenshot_path}")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
