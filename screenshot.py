import asyncio
from playwright.async_api import async_playwright
URL = "http://localhost:8080/"
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch()
        for name, vp, mobile in [("desktop", {"width":1440,"height":900}, False), ("mobile", {"width":390,"height":844}, True)]:
            ctx = await b.new_context(viewport=vp, device_scale_factor=2 if mobile else 1, is_mobile=mobile, has_touch=mobile, locale="ru-RU", color_scheme="light")
            pg = await ctx.new_page()
            await pg.goto(URL, wait_until="networkidle", timeout=60000)
            await pg.wait_for_timeout(1500)
            await pg.screenshot(path=f"screenshot_{name}.png", full_page=False)
            await ctx.close()
        await b.close()
asyncio.run(main())
