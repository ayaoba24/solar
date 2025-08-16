22#!/usr/bin/env python3
"""
nigeria_solar_scraper.py

Scrapes solar panels, solar batteries, and inverters from Jumia, Konga, and Jiji.
Supports:
 - list page scraping
 - product detail page visits for structured specs
 - Playwright (Chromium) for JS-heavy pages, with aiohttp fallback
 - simple rate limiting and concurrency control
 - CSV output per site

Usage:
  python nigeria_solar_scraper.py    # runs an interactive menu
"""

import asyncio
import json
import logging
import os
import random
import re
import time
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import aiofiles
import aiohttp
import pandas as pd
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
from tenacity import retry, stop_after_attempt, wait_exponential

# Optional playwright import — script will detect if available
try:
    from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
    PLAYWRIGHT_AVAILABLE = True
except Exception:
    PLAYWRIGHT_AVAILABLE = False

# For notebooks/Colab: allow nested event loops when needed
try:
    import nest_asyncio
    nest_asyncio.apply()
except Exception:
    pass

# Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# --------------- Data models ----------------
@dataclass
class ScrapedItem:
    name: Optional[str] = None
    brand: Optional[str] = None
    model: Optional[str] = None
    price_raw: Optional[str] = None
    price_cleaned: Optional[float] = None
    currency: Optional[str] = None
    product_url: Optional[str] = None
    image_url: Optional[str] = None
    all_image_urls: Optional[List[str]] = None
    description: Optional[str] = None
    specs: Optional[Dict[str, Any]] = None
    rating: Optional[float] = None
    reviews_count: Optional[int] = None
    availability: Optional[str] = None
    seller: Optional[str] = None
    location: Optional[str] = None
    condition: Optional[str] = None
    scraped_at: Optional[str] = None
    source_site: Optional[str] = None
    raw_html_path: Optional[str] = None

    def __post_init__(self):
        if self.scraped_at is None:
            self.scraped_at = datetime.utcnow().isoformat()
        if self.price_raw and (self.price_cleaned is None):
            self.price_cleaned, self.currency = self._extract_price(self.price_raw)
        if self.specs is None:
            self.specs = {}
        if self.all_image_urls is None:
            self.all_image_urls = []

    def _extract_price(self, price_str: str) -> Tuple[Optional[float], Optional[str]]:
        if not price_str:
            return None, None
        # detect currency
        currency = "NGN"
        if "$" in price_str:
            currency = "USD"
        if "₦" in price_str:
            currency = "NGN"
        # strip non-numeric except dot and comma, then remove commas
        only_nums = re.sub(r"[^\d.,]", "", price_str).replace(",", "")
        try:
            return float(only_nums) if only_nums else None, currency
        except Exception:
            return None, currency

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        # keep specs as json string for CSV compatibility
        d["specs"] = json.dumps(d.get("specs") or {}, ensure_ascii=False)
        return d

# --------------- Site configuration ----------------
@dataclass
class SiteConfig:
    name: str
    start_urls: List[str]
    list_selector: str
    selectors: Dict[str, str]             # selectors relative to list item
    requires_js: bool = False
    max_pages: int = 2
    delay_range: Tuple[float, float] = (1.5, 3.5)
    concurrent_requests: int = 3
    rate_limit_per_minute: int = 30       # tokens

# --------------- Rate limiter ----------------
class RateLimiter:
    def __init__(self, rate_per_minute: int):
        self.tokens = rate_per_minute
        self.max_tokens = rate_per_minute
        self.refill_period = 60.0
        self.last_refill = time.time()

    async def acquire(self):
        while True:
            now = time.time()
            elapsed = now - self.last_refill
            if elapsed >= self.refill_period:
                self.tokens = self.max_tokens
                self.last_refill = now
            if self.tokens > 0:
                self.tokens -= 1
                return
            await asyncio.sleep(1.0)

# --------------- Scraper class ----------------
class NigeriaSolarScraper:
    def __init__(self, output_dir: str = "./scraped_data"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.ua = UserAgent()
        self.rate_limiters: Dict[str, RateLimiter] = {}
        self.session: Optional[aiohttp.ClientSession] = None

    def _headers(self):
        return {
            "User-Agent": self.ua.random,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5"
        }

    async def _fetch_static(self, url: str) -> Optional[str]:
        if not self.session:
            timeout = aiohttp.ClientTimeout(total=30)
            self.session = aiohttp.ClientSession(timeout=timeout)
        try:
            async with self.session.get(url, headers=self._headers()) as resp:
                if resp.status != 200:
                    logger.warning(f"Non-200 {resp.status} for {url}")
                    return None
                return await resp.text()
        except Exception as e:
            logger.error(f"Static fetch error for {url}: {e}")
            return None

    async def _fetch_playwright(self, browser, url: str, block_images: bool = True) -> Optional[str]:
        try:
            context = await browser.new_context(user_agent=self.ua.random, viewport={"width":1280,"height":800})
            page = await context.new_page()
            if block_images:
                await page.route("**/*.{png,jpg,jpeg,gif,svg}", lambda r: r.abort())
            await page.goto(url, wait_until="domcontentloaded", timeout=45000)
            await asyncio.sleep(1.0)  # small wait for dynamic loads
            content = await page.content()
            await context.close()
            return content
        except Exception as e:
            logger.error(f"Playwright fetch error for {url}: {e}")
            return None

    def _extract_from_list_item(self, item_soup: BeautifulSoup, config: SiteConfig, base_url: str) -> ScrapedItem:
        s = config.selectors
        def safe_select_text(sel):
            el = item_soup.select_one(sel) if sel else None
            return el.get_text(strip=True) if el else None

        def safe_select_attr(sel, attr="href"):
            el = item_soup.select_one(sel) if sel else None
            if not el:
                return None
            return el.get(attr) or None

        name = safe_select_text(s.get("name"))
        price_raw = safe_select_text(s.get("price"))
        product_rel = safe_select_attr(s.get("product_url"), "href")
        product_url = None
        if product_rel:
            if product_rel.startswith("http"):
                product_url = product_rel
            else:
                product_url = base_url.rstrip("/") + "/" + product_rel.lstrip("/")

        image = safe_select_attr(s.get("image"), "src") or safe_select_attr(s.get("image"), "data-src")
        if image and image.startswith("//"):
            image = "https:" + image

        item = ScrapedItem(
            name=name,
            price_raw=price_raw,
            product_url=product_url,
            image_url=image,
            source_site=config.name
        )
        return item

    def _parse_product_detail(self, html: str, base_url: str, item: ScrapedItem) -> ScrapedItem:
        soup = BeautifulSoup(html, "lxml")
        # description
        desc_tag = soup.select_one("meta[name='description']") or soup.select_one(".description") or soup.select_one(".product-description")
        if desc_tag:
            item.description = desc_tag.get("content") if desc_tag.has_attr("content") else desc_tag.get_text(" ", strip=True)
        # images — find many images
        imgs = []
        for img in soup.select("img"):
            src = img.get("data-src") or img.get("src") or ""
            if src and src not in imgs and len(src) > 10:
                if src.startswith("//"):
                    src = "https:" + src
                imgs.append(src)
        item.all_image_urls = imgs[:10]
        if not item.image_url and imgs:
            item.image_url = imgs[0]
        # specs tables
        specs = {}
        # Common patterns: <table class="specs">, <ul class="specs">, <div class="specs">
        # Table-based
        for table in soup.select("table"):
            # try to parse key/value rows
            for tr in table.select("tr"):
                tds = tr.select("td")
                if len(tds) >= 2:
                    k = tds[0].get_text(" ", strip=True)
                    v = tds[1].get_text(" ", strip=True)
                    if k:
                        specs[k] = v
        # list-based key/value
        for li in soup.select("ul li"):
            text = li.get_text(" ", strip=True)
            if ":" in text:
                k, v = text.split(":", 1)
                specs[k.strip()] = v.strip()
        # specific key heuristics from description
        text_blob = (item.description or "") + " " + " ".join(img.get_text(" ", strip=True) for img in soup.select("p"))
        # Extract simple fields via regex heuristics (wattage, Ah, V, type)
        watt_match = re.search(r"(\d{2,4})\s*[Ww]\b", text_blob)
        if watt_match and "Watt" not in specs:
            specs["Watt"] = watt_match.group(1) + " W"
        ah_match = re.search(r"(\d{2,4})\s*(Ah|ah)\b", text_blob)
        if ah_match and "Capacity" not in specs:
            specs["Capacity"] = ah_match.group(1) + " Ah"
        type_match = re.search(r"(mono(?:crystalline)?|poly(?:crystalline)?|monocrystalline|polycrystalline|PERC)", text_blob, re.I)
        if type_match and "Type" not in specs:
            specs["Type"] = type_match.group(1)
        # brand/model heuristics from title
        if item.name:
            bm = re.split(r"[-|/]", item.name)
            if len(bm) >= 2:
                item.brand = bm[0].strip()
                item.model = bm[1].strip() if len(bm) > 1 else item.model
        item.specs.update(specs)
        return item

    async def _save_item_html(self, html: str, site_name: str, slug: str) -> str:
        fn = self.output_dir / f"{site_name}_{slug}_{int(time.time())}.html"
        try:
            async with aiofiles.open(fn, "w", encoding="utf-8") as f:
                await f.write(html)
            return str(fn)
        except Exception:
            return ""

    async def scrape_site(self, config: SiteConfig, search_keyword: str = None) -> List[ScrapedItem]:
        logger.info(f"Starting scrape for {config.name}")
        # rate limiter for site
        rl = RateLimiter(config.rate_limit_per_minute)
        self.rate_limiters[config.name] = rl
        items: List[ScrapedItem] = []

        # optionally substitute search keywords in start_urls
        start_urls = []
        for u in config.start_urls:
            if "{q}" in u:
                start_urls.append(u.replace("{q}", (search_keyword or "solar").replace(" ", "+")))
            else:
                start_urls.append(u)

        # Decide whether to use Playwright or static
        playwright_context = None
        browser = None

        if config.requires_js and PLAYWRIGHT_AVAILABLE:
            try:
                playwright_context = await async_playwright().start()
                browser = await playwright_context.chromium.launch(headless=True)
                logger.info("Playwright launched for JS site")
            except Exception as e:
                logger.warning(f"Playwright failed to start: {e}. Falling back to static fetches.")
                browser = None

        sem = asyncio.Semaphore(config.concurrent_requests)

        async def process_list_page(url: str):
            async with sem:
                await rl.acquire()
                logger.info(f"Fetching list page: {url}")
                content = None
                if browser:
                    content = await self._fetch_playwright(browser, url)
                else:
                    content = await self._fetch_static(url)
                if not content:
                    return
                soup = BeautifulSoup(content, "lxml")
                list_nodes = soup.select(config.list_selector)
                logger.info(f"Found {len(list_nodes)} list nodes on {url}")
                for node in list_nodes:
                    item = self._extract_from_list_item(node, config, base_url=url)
                    # only items with at least a name or product_url
                    if item.name or item.product_url:
                        items.append(item)

        # fetch list pages (concurrently but limited)
        tasks = []
        for url in start_urls[: config.max_pages]:
            tasks.append(asyncio.create_task(process_list_page(url)))
            await asyncio.sleep(random.uniform(*config.delay_range))
        await asyncio.gather(*tasks)

        # visit detail pages for richer info
        async def process_detail(item: ScrapedItem):
            if not item.product_url:
                return
            async with sem:
                await rl.acquire()
                logger.info(f"Visiting detail: {item.product_url}")
                content = None
                if browser:
                    content = await self._fetch_playwright(browser, item.product_url)
                else:
                    content = await self._fetch_static(item.product_url)
                if not content:
                    logger.warning(f"No content for detail: {item.product_url}")
                    return
                # save HTML optionally
                slug = re.sub(r"[^a-zA-Z0-9_-]", "_", (item.name or "product"))[:40]
                raw_path = await self._save_item_html(content, config.name, slug)
                if raw_path:
                    item.raw_html_path = raw_path
                # parse detail
                self._parse_product_detail(content, base_url=item.product_url, item=item)
                await asyncio.sleep(random.uniform(0.5, 1.7))

        detail_tasks = [asyncio.create_task(process_detail(it)) for it in items if it.product_url]
        # limit concurrency
        if detail_tasks:
            # process in batches
            batch_size = config.concurrent_requests * 2
            for i in range(0, len(detail_tasks), batch_size):
                await asyncio.gather(*detail_tasks[i : i + batch_size])

        # close Playwright if used
        if playwright_context:
            try:
                await browser.close()
                await playwright_context.stop()
            except Exception:
                pass

        # close aiohttp session
        if self.session:
            try:
                await self.session.close()
            except Exception:
                pass
            self.session = None

        # deduplicate by product_url or name+price
        unique = {}
        final_items = []
        for it in items:
            key = it.product_url or f"{it.name}_{it.price_cleaned}"
            if key and key not in unique:
                unique[key] = True
                final_items.append(it)
        logger.info(f"Scraping finished for {config.name}. Items collected: {len(final_items)}")
        return final_items

    async def save_to_csv(self, items: List[ScrapedItem], site_name: str) -> str:
        if not items:
            logger.warning("No items to save")
            return ""
        df = pd.DataFrame([i.to_dict() for i in items])
        fn = self.output_dir / f"{site_name}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"
        df.to_csv(fn, index=False)
        logger.info(f"Saved {len(items)} items to {fn}")
        return str(fn)


# --------------- Site configs (Jumia, Konga, Jiji) ---------------
def get_default_configs() -> List[SiteConfig]:
    return [
        SiteConfig(
            name="jumia",
            start_urls=[
                "https://www.jumia.com.ng/catalog/?q=solar+battery/",
                "https://www.jumia.com.ng/catalog/?q=solar+panel/",
                "https://www.jumia.com.ng/catalog/?q=solar+inverter/"
            ],
            list_selector="article.prd",
            selectors={
                "name": ".info .name, .name",
                "price": ".prc, .price",
                "product_url": "a.core, a[href]",
                "image": ".img img"
            },
            requires_js=False,
            max_pages=3,
            delay_range=(1.0, 2.5),
            concurrent_requests=3,
            rate_limit_per_minute=100
        ),
        SiteConfig(
            name="konga",
            start_urls=[
                "https://www.konga.com/search?search={q}"
            ],
            list_selector=".product",
            selectors={
                "name": ".name, .product-title",
                "price": ".price, .sale-price",
                "product_url": "a",
                "image": "img"
            },
            requires_js=True,
            max_pages=2,
            delay_range=(2.5, 4.0),
            concurrent_requests=2,
            rate_limit_per_minute=30
        ),
        SiteConfig(
            name="jiji",
            start_urls=[
                "https://jiji.ng/search?query={q}",
                "https://jiji.ng/solar-panels"
            ],
            list_selector=".qa-advert-list-item, [data-cy='ad-card']",
            selectors={
                "name": ".qa-advert-list-title, [data-cy='ad-title']",
                "price": ".qa-advert-price, [data-cy='ad-price']",
                "product_url": "a[href*='/ad/']",
                "image": ".qa-advert-list-photo img"
            },
            requires_js=True,
            max_pages=2,
            delay_range=(3.0, 5.0),
            concurrent_requests=2,
            rate_limit_per_minute=25
        )
    ]

# --------------- CLI / main ----------------
async def main():
    print("Nigeria Solar Scraper")
    print("Running full scrape for Jumia, Konga, Jiji")
    ch = "2"

    scraper = NigeriaSolarScraper(output_dir="./scraped_data")
    configs = get_default_configs()

    if ch == "1":
        conf = configs[0]  # jumia quick
        items = await scraper.scrape_site(conf, search_keyword="solar panel")
        await scraper.save_to_csv(items, conf.name)
    elif ch == "2":
        all_results = {}
        for conf in configs:
            items = await scraper.scrape_site(conf, search_keyword="solar panel")
            out = await scraper.save_to_csv(items, conf.name)
            all_results[conf.name] = {"count": len(items), "file": out}
            # polite gap between sites
            await asyncio.sleep(2.0)
        print(json.dumps(all_results, indent=2))
    elif ch == "3":
        conf = configs[0]
        items = await scraper.scrape_site(conf, search_keyword="solar panel")
        await scraper.save_to_csv(items, conf.name)
    else:
        print("Invalid choice.")

if __name__ == "__main__":
    # handle running inside Jupyter/Colab where an event loop may already be active.
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # running inside notebook — create task
            loop.create_task(main())
            # give time for task to run (user can await in notebook)
        else:
            asyncio.run(main())
    except RuntimeError:
        # fallback
        asyncio.run(main())