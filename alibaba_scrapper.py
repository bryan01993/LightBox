import csv
import os
import re
import asyncio
import urllib.request
from urllib.parse import urljoin
from playwright.async_api import async_playwright

OUTPUT_CSV = "alibaba_scrap.csv"
IMAGE_DIR = "alibaba_images"
URL = "https://www.alibaba.com/picture/search.htm?imageType=oss&escapeQp=true&imageAddress=%2Ficbuimgsearch%2FimageBase64_1745173241595_109.jpeg%40%40oss_us&sourceFrom=imageupload&uploadType=pasteImg&SearchScene=the-new-header%40%40FY23SearchBar&spm=a2700.picsearch"

async def scrape():
    os.makedirs(IMAGE_DIR, exist_ok=True)
    print("Iniciando navegador...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, slow_mo=100)
        context = await browser.new_context()
        await context.add_cookies([{
            "name": "x-segment",
            "value": "es",
            "domain": ".alibaba.com",
            "path": "/"
        }])
        page = await context.new_page()
        await page.set_extra_http_headers({
            "Accept-Language": "es-ES,es;q=0.9"
        })

        print(f"Navegando a: {URL}")
        await page.goto(URL, timeout=60000)

        print("Capturando pantalla inicial para debugging...")
        await page.screenshot(path="before_scroll.png")

        print("Haciendo scroll para cargar productos...")
        for i in range(10):
            print(f"\tScroll {i + 1}...")
            await page.mouse.wheel(0, 3000)
            await asyncio.sleep(2)

        print("Capturando pantalla después del scroll...")
        await page.screenshot(path="after_scroll.png")

        print("Buscando tarjetas de producto reales...")
        cards = await page.query_selector_all("div[data-spm-anchor-id][class*='search-card']")
        print(f"Se encontraron {len(cards)} tarjetas.")

        data = []
        idx = 0
        for card in cards:
            try:
                # TODO: Validar si la tarjeta contiene información de producto real antes de guardar la imagen
                img = await card.query_selector("img")
                link = await card.query_selector("a")
                price = await card.query_selector(".search-card-e-price-main")
                shop = await card.query_selector(".store-name")
                min_order = await card.query_selector("div.search-card-m-sale-features__item:has-text('Orden mín:')")
                delivery = await card.query_selector("div.search-card-m-sale-features__item:has-text('Entrega est.')")
                rating_container = await card.query_selector(".search-card-e-review")
                rating_value = await rating_container.query_selector("strong") if rating_container else None
                # TODO: Extraer también la cantidad de valoraciones (ej: "(28)")

                image_url = await img.get_attribute("src") if img else ""
                product_url = await link.get_attribute("href") if link else ""
                title = await link.inner_text() if link else ""
                price_text = await price.inner_text() if price else ""
                shop_name = await shop.inner_text() if shop else ""
                min_order_text = await min_order.inner_text() if min_order else ""
                delivery_text = await delivery.inner_text() if delivery else "undefined"
                rating_text = await rating_value.inner_text() if rating_value else ""

                if image_url.startswith("//"):
                    image_url = urljoin("https://", image_url)

                image_name = f"{idx:03d}.jpg"
                image_path = os.path.join(IMAGE_DIR, image_name)
                if image_url:
                    urllib.request.urlretrieve(image_url, image_path)
                    print(f"\t[{idx}] Imagen guardada: {image_name}")

                data.append({
                    "index": idx,
                    "title": title.strip(),
                    "url": product_url,
                    "price": price_text.strip(),
                    "image": image_name,
                    "shop": shop_name.strip(),
                    "min_order": min_order_text.strip(),
                    "delivery": delivery_text.strip(),
                    "rating": rating_text.strip(),
                })
                idx += 1
            except Exception as e:
                print(f"\tError: {e}")
                continue

        with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
            fieldnames = ["index", "title", "url", "price", "image", "shop", "min_order", "delivery", "rating"]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(data)

        print(f"Scraping completado. {len(data)} productos guardados en {OUTPUT_CSV}.")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(scrape())
