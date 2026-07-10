import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

from django.core.management.base import BaseCommand
from django.utils import timezone

from core.models import News
from core import fmp_client

TECH_KEYWORDS = [
    "tech", "software", "ai ", "artificial intelligence", "semiconductor",
    "chip", "cloud", "cybersecurity", "apple", "microsoft", "google",
    "nvidia", "meta", "amazon", "openai", "machine learning",
]
COMMODITY_KEYWORDS = [
    "oil", "gold", "silver", "copper", "wheat", "corn", "commodity",
    "crude", "natural gas", "platinum", "palladium", "energy", "brent",
]
ETF_KEYWORDS = [
    "etf", "exchange-traded fund", "index fund", "vanguard", "blackrock etf",
    "spdr", "ishares", "invesco",
]
MACRO_KEYWORDS = [
    "fed", "federal reserve", "interest rate", "inflation", "cpi", "gdp",
    "recession", "central bank", "treasury", "yield", "monetary policy",
    "economy", "fiscal",
]

FEEDS = [
    {"type": "stock",  "default_category": "Stocks", "limit": 30},
    {"type": "forex",  "default_category": "Forex",  "limit": 15},
    {"type": "crypto", "default_category": "Crypto", "limit": 15},
]


def _classify(feed_category, title, text):
    combined = (title + " " + (text or "")).lower()
    # Crypto and Forex feeds keep their category unless overridden by macro keywords
    if feed_category == "Crypto":
        return "Crypto"
    if feed_category == "Forex":
        for kw in MACRO_KEYWORDS:
            if kw in combined:
                return "Macro"
        return "Forex"
    # Stock feed: try to sub-classify
    for kw in ETF_KEYWORDS:
        if kw in combined:
            return "ETF"
    for kw in TECH_KEYWORDS:
        if kw in combined:
            return "Tech"
    for kw in COMMODITY_KEYWORDS:
        if kw in combined:
            return "Commodities"
    for kw in MACRO_KEYWORDS:
        if kw in combined:
            return "Macro"
    return "Stocks"


def _parse_date(date_str):
    if not date_str:
        return timezone.now()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%SZ"):
        try:
            dt = datetime.datetime.strptime(date_str, fmt)
            return timezone.make_aware(dt) if timezone.is_naive(dt) else dt
        except ValueError:
            continue
    return timezone.now()


class Command(BaseCommand):
    help = "Fetch latest financial news from FMP and store in the News model."

    def _fetch_feed(self, feed):
        try:
            articles = fmp_client.get_news(feed_type=feed["type"], limit=feed["limit"])
            if not isinstance(articles, list):
                return feed, Exception(f"Unexpected response type: {type(articles)}")
            return feed, articles
        except Exception as exc:
            return feed, exc

    def handle(self, *args, **options):
        created = skipped = errors = 0

        feed_results = []
        with ThreadPoolExecutor(max_workers=3) as pool:
            futures = {pool.submit(self._fetch_feed, feed): feed for feed in FEEDS}
            for future in as_completed(futures):
                feed_results.append(future.result())

        for feed, articles in feed_results:
            if isinstance(articles, Exception):
                self.stderr.write(f"  Error fetching {feed['type']} feed: {articles}")
                errors += 1
                continue

            for article in articles:
                title = (article.get("title") or "").strip()[:500]
                if not title:
                    continue

                url       = (article.get("url") or "").strip()
                text      = article.get("text") or article.get("content") or ""
                site      = article.get("site") or article.get("publisher") or ""
                image     = article.get("image") or ""
                symbol    = article.get("symbol") or ""
                published = _parse_date(article.get("publishedDate", ""))

                # Deduplicate by source_url (skip articles without URL using title)
                if url:
                    if News.objects.filter(source_url=url).exists():
                        skipped += 1
                        continue
                else:
                    if News.objects.filter(title=title).exists():
                        skipped += 1
                        continue

                category = _classify(feed["default_category"], title, text)
                summary  = text[:300] if text else title

                News.objects.create(
                    title=title,
                    summary=summary,
                    content=text,
                    category=category,
                    source=site[:200],
                    symbol=symbol[:50],
                    image_url=image,
                    source_url=url,
                    published_at=published,
                )
                created += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"News sync: {created} created, {skipped} skipped, {errors} feed error(s)"
            )
        )
