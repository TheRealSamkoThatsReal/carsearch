"""
Autolist scraper (replaces Cars.com / eBay Motors, which block requests).

Autolist embeds all listing data as Next.js page props JSON, so no HTML
parsing is needed — we just pull the JSON out of the page and iterate.
"""
import json
import re
from bs4 import BeautifulSoup
from .base import BaseScraper, Listing

_STYLE_MAP = {
    "sedan":       "Sedan",
    "suv":         "SUV",
    "truck":       "Truck",
    "pickup":      "Truck",
    "coupe":       "Coupe",
    "hatchback":   "Hatchback",
    "wagon":       "Wagon",
    "convertible": "Convertible",
    "van":         "Van",
    "minivan":     "Minivan",
}


class CarsComScraper(BaseScraper):
    """Named CarsComScraper for import-compatibility; actually scrapes Autolist."""

    name = "Autolist"

    def search(self, filters: dict) -> list[Listing]:
        make  = (filters.get("make")  or "").lower().replace(" ", "-")
        model = (filters.get("model") or "").lower().replace(" ", "-")

        # Autolist URL: /toyota-camry or /toyota (no model) or /used-cars (no make)
        if make and model:
            path = f"{make}-{model}"
        elif make:
            path = make
        else:
            path = "used-cars"

        params: dict = {}
        if filters.get("zip"):
            params["zip"] = filters["zip"]
        if filters.get("radius"):
            params["radius"] = filters["radius"]
        if filters.get("min_price"):
            params["price_min"] = filters["min_price"]
        if filters.get("max_price"):
            params["price_max"] = filters["max_price"]
        if filters.get("year_min"):
            params["year_min"] = filters["year_min"]
        if filters.get("year_max"):
            params["year_max"] = filters["year_max"]
        style = (filters.get("style") or "").lower()
        if style in _STYLE_MAP:
            params["body_type"] = _STYLE_MAP[style]

        resp = self.get(f"https://www.autolist.com/{path}", params=params)
        if not resp:
            return []

        soup = BeautifulSoup(resp.text, "lxml")

        # Data lives in <script id="__NEXT_DATA__"> or the first script tag with "vehicles"
        data_tag = soup.find("script", id="__NEXT_DATA__")
        if not data_tag:
            data_tag = next(
                (t for t in soup.find_all("script")
                 if t.string and '"vehicles"' in t.string),
                None,
            )
        if not data_tag or not data_tag.string:
            return []

        try:
            data = json.loads(data_tag.string)
            vehicles = data["props"]["pageProps"]["vehicles"]
        except (json.JSONDecodeError, KeyError):
            return []

        listings = []
        for v in vehicles:
            try:
                listing = self._vehicle_to_listing(v, filters)
                if listing:
                    listings.append(listing)
            except Exception:
                continue

        return listings

    def _vehicle_to_listing(self, v: dict, filters: dict) -> Listing | None:
        title_parts = [str(v.get("year", "")), v.get("make", ""), v.get("model", ""), v.get("trim", "")]
        title = " ".join(p for p in title_parts if p).strip()
        if not title:
            return None

        price   = v.get("price")
        mileage = v.get("mileage")
        year    = v.get("year")
        loc     = v.get("location") or f"{v.get('city', '')}, {v.get('state', '')}".strip(", ")
        vdp     = v.get("vdpUrl", "")
        if vdp and not vdp.startswith("http"):
            vdp = "https://www.autolist.com" + vdp

        return Listing(
            title=title,
            price=int(price) if price else None,
            url=vdp,
            source=self.name,
            make=v.get("make") or filters.get("make"),
            model=v.get("model") or filters.get("model"),
            year=int(year) if year else None,
            mileage=int(mileage) if mileage else None,
            location=loc or None,
        )
