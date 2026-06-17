#!/usr/bin/env python3
"""GitHub Actions entry point — reads search params from env vars, writes data/results.json."""
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

from scrapers import CraigslistScraper, CarsComScraper
from rater import rate_deals


def env(key, default=None):
    v = os.environ.get(key, "").strip()
    return v if v else default


def main():
    filters = {
        "make":      env("MAKE"),
        "model":     env("MODEL"),
        "style":     env("STYLE"),
        "max_price": int(env("MAX_PRICE", "0") or 0) or None,
        "min_price": int(env("MIN_PRICE", "500") or 500),
        "year_min":  int(env("YEAR_MIN", "0") or 0) or None,
        "year_max":  int(env("YEAR_MAX", "0") or 0) or None,
        "zip":       env("ZIP", "94102"),
        "radius":    int(env("RADIUS", "50") or 50),
        "cl_area":   env("CL_AREA"),
    }

    scrapers = [CraigslistScraper(), CarsComScraper()]
    all_listings = []
    errors = []

    with ThreadPoolExecutor(max_workers=len(scrapers)) as pool:
        futures = {pool.submit(s.search, filters): s.name for s in scrapers}
        for future in as_completed(futures):
            name = futures[future]
            try:
                results = future.result()
                all_listings.extend(results)
                print(f"✓ {name}: {len(results)} listings")
            except Exception as exc:
                errors.append(f"{name}: {exc}")
                print(f"✗ {name}: {exc}", file=sys.stderr)

    rated = rate_deals(all_listings)

    output = {
        "searched_at": datetime.now(timezone.utc).isoformat(),
        "filters": {k: v for k, v in filters.items() if v is not None},
        "count": len(rated),
        "errors": errors,
        "listings": [
            {
                "title":      l.title,
                "price":      l.price,
                "url":        l.url,
                "source":     l.source,
                "make":       l.make,
                "model":      l.model,
                "year":       l.year,
                "mileage":    l.mileage,
                "location":   l.location,
                "deal_score": l.deal_score,
                "deal_label": l.deal_label,
            }
            for l in rated
        ],
    }

    os.makedirs("data", exist_ok=True)
    with open("data/results.json", "w") as f:
        json.dump(output, f, indent=2)

    print(f"\n✓ Saved {len(rated)} listings to data/results.json")


if __name__ == "__main__":
    main()
