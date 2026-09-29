import asyncio
from pathlib import Path
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()

        # Capture console errors
        errors = []
        page.on("pageerror", lambda err: errors.append(err))

        await page.goto((Path(__file__).resolve().parent / "index.html").as_uri())

        title = await page.title()
        print(f"Page title: {title}")

        prompt = await page.locator("#promptOutput").text_content()
        await browser.close()
        if errors:
            raise RuntimeError("JavaScript errors: " + "; ".join(map(str, errors)))
        if not prompt or not prompt.startswith("[CONCEPT]:"):
            raise RuntimeError("The initial prompt did not render.")
        print("No JavaScript errors found; initial prompt rendered.")

if __name__ == "__main__":
    asyncio.run(main())
