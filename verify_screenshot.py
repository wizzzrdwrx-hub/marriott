import asyncio
from playwright.async_api import async_playwright
import os

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()

        await page.goto("file:///app/index.html")
        await page.wait_for_load_state("networkidle")

        os.makedirs("/home/jules/verification", exist_ok=True)
        screenshot_path = "/home/jules/verification/index_verification.png"

        await page.screenshot(path=screenshot_path, full_page=True)
        print(f"Screenshot saved to {screenshot_path}")

        await browser.close()

asyncio.run(main())
