import json
import re
from bs4 import BeautifulSoup
from .base import BaseScraper, Listing, extract_year, extract_mileage

_STYLE_MAP = {
    "convertible": "convertible",
    "coupe": "coupe",
    "hatchback": "hatchback",
    "minivan": "minivan",
    "pickup": "pickup-truck",
    "truck": "pickup-truck",
    "sedan": "sedan",
    "suv": "suv",
    "wagon": "wagon",
    "van": "cargo-van",
}

_JSON_LD_RE = re.compile(r'type="application/ld\+json"')


class CarsComScraper(BaseScraper):
    name = "Cars.com"

    def search(self, filters: dict) -> list[Listing]:
        make = (filters.get("make") or "").lower().replace(" ", "-")
        model = (filters.get("model") or "").lower().replace(" ", "-")

        params = {
            "stock_type": "used",
            "page_size": 20,
            "sort": "best_match_desc",
        }
        if make:
            params["makes[]"] = make
        if model and make:
            params["models[]"] = f"{make}-{model}"
        if filters.get("max_price"):
            params["list_price_max"] = filters["max_price"]
        if filters.get("min_price"):
            params["list_price_min"] = filters["min_price"]
        if filters.get("zip"):
            params["zip"] = filters["zip"]
        if filters.get("radius"):
            params["maximum_distance"] = filters["radius"]
        if filters.get("year_min"):
            params["year_min"] = filters["year_min"]
        if filters.get("year_max"):
            params["year_max"] = filters["year_max"]
        style = (filters.get("style") or "").lower()
        if style in _STYLE_MAP:
            params["body_style_slugs[]"] = _STYLE_MAP[style]

        resp = self.get("https://www.cars.com/shopping/results/", params=params)
        if not resp:
            return []

        soup = BeautifulSoup(resp.text, "lxml")
        listings = []

        # Primary: article.vehicle-card elements
        for card in soup.select("article.vehicle-card, div.vehicle-card"):
            try:
                listing = self._parse_card(card, filters)
                if listing:
                    listings.append(listing)
            except Exception:
                continue

        # Fallback: JSON-LD structured data
        if not listings:
            listings = self._parse_json_ld(soup, filters)

        return listings

    def _parse_card(self, card, filters: dict) -> Listing | None:
        link_el = card.select_one("a[href]")
        href = link_el["href"] if link_el else ""
        if href and not href.startswith("http"):
            href = "https://www.cars.com" + href

        title_el = card.select_one(
            ".vehicle-card__title, .title, h2, [data-qa='vehicle-name']"
        )
        title = title_el.get_text(strip=True) if title_el else ""
        if not title:
            return None

        price_el = card.select_one(
            ".primary-price, .price, [data-qa='price'], .vehicle-card__price"
        )
        price = None
        if price_el:
            raw = re.sub(r"[^\d]", "", price_el.get_text())
            price = int(raw) if raw else None

        mileage_el = card.select_one(".mileage, [data-qa='mileage']")
        mileage = extract_mileage(mileage_el.get_text()) if mileage_el else None

        dealer_el = card.select_one(".dealer-name, [data-qa='dealer-name']")
        location = dealer_el.get_text(strip=True) if dealer_el else None

        year = extract_year(title)

        return Listing(
            title=title,
            price=price,
            url=href,
            source=self.name,
            make=filters.get("make"),
            model=filters.get("model"),
            year=year,
            mileage=mileage,
            location=location,
        )

    def _parse_json_ld(self, soup: BeautifulSoup, filters: dict) -> list[Listing]:
        listings = []
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(script.string or "")
                if isinstance(data, list):
                    items = data
                elif data.get("@type") == "ItemList":
                    items = [e.get("item", e) for e in data.get("itemListElement", [])]
                else:
                    items = [data]

                for item in items:
                    if item.get("@type") not in ("Car", "Vehicle", "Product"):
                        continue
                    name = item.get("name", "")
                    url = item.get("url", "")
                    offers = item.get("offers", {})
                    price_raw = offers.get("price") if isinstance(offers, dict) else None
                    price = int(float(str(price_raw))) if price_raw else None
                    year = extract_year(name)
                    listings.append(
                        Listing(
                            title=name,
                            price=price,
                            url=url,
                            source=self.name,
                            make=filters.get("make"),
                            model=filters.get("model"),
                            year=year,
                        )
                    )
            except Exception:
                continue
        return listings
