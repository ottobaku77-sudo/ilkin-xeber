import asyncio, sys
from playwright.async_api import async_playwright
BASE = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8080/"
SHOTS = [("futbol.html?world=1", "screenshot_futbol_world"), ("", "screenshot"), ("futbol.html", "screenshot_futbol"), ("futbol.html?club=Real+Madrid", "screenshot_real")]
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch()
        for path, prefix in SHOTS:
            for name, vp, mobile in [("desktop", {"width":1440,"height":900}, False), ("mobile", {"width":390,"height":844}, True)]:
                if prefix == "screenshot_real" and mobile: continue
                ctx = await b.new_context(viewport=vp, device_scale_factor=2 if mobile else 1, is_mobile=mobile, has_touch=mobile, locale="az-AZ", color_scheme="light")
                pg = await ctx.new_page()
                await pg.goto(BASE + path, wait_until="domcontentloaded", timeout=60000)
                await pg.wait_for_timeout(5000)
                await pg.screenshot(path=f"{prefix}_{name}.png", full_page=False)
                await ctx.close()
        await b.close()
asyncio.run(main())
