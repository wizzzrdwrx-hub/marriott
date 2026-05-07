import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()

        # Capture console errors
        errors = []
        page.on("pageerror", lambda err: errors.append(err))

        await page.goto("file:///app/index.html")
        await page.wait_for_load_state("networkidle")

        title = await page.title()
        print(f"Page title: {title}")

        if errors:
            print("Errors found:")
            for err in errors:
                print(f"- {err}")
        else:
            print("No JavaScript errors found.")

        await browser.close()

asyncio.run(main())
