from bs4 import BeautifulSoup
from .base import BaseScraper, Listing, extract_year, extract_mileage

# Maps first 3 digits of ZIP code to Craigslist subdomain.
# Falls back to "sfbay" when no match is found.
_ZIP_PREFIX_TO_AREA = {
    **{str(z): "newyork" for z in [*range(100, 120), *range(110, 120)]},
    **{str(z): "newjersey" for z in range(70, 90)},
    **{str(z): "philadelphia" for z in range(190, 199)},
    **{str(z): "washingtondc" for z in [*range(200, 206), 219, 220]},
    **{str(z): "baltimore" for z in [*range(210, 213), 214, *range(216, 218), 443]},
    **{str(z): "charlotte" for z in range(280, 284)},
    **{str(z): "atlanta" for z in [*range(300, 304), *range(306, 316), 398]},
    **{str(z): "jacksonville" for z in [*range(320, 323), 326, 328, 329]},
    **{str(z): "miami" for z in [*range(330, 335), 339, 349]},
    **{str(z): "tampa" for z in [*range(335, 339), 346, 347]},
    "336": "orlando",
    **{str(z): "nashville" for z in [*range(370, 386)]},
    **{str(z): "louisville" for z in [*range(400, 403), *range(410, 414), *range(502, 504)]},
    **{str(z): "cleveland" for z in [*range(440, 449)]},
    **{str(z): "columbus" for z in [*range(430, 440)]},
    **{str(z): "cincinnati" for z in [*range(450, 460)]},
    **{str(z): "indianapolis" for z in [*range(460, 480)]},
    **{str(z): "detroit" for z in [*range(480, 492)]},
    **{str(z): "grandrapids" for z in [*range(493, 500)]},
    **{str(z): "milwaukee" for z in [*range(530, 549)]},
    **{str(z): "chicago" for z in [*range(600, 630)]},
    **{str(z): "neworleans" for z in [*range(700, 710)]},
    **{str(z): "dallas" for z in [*range(750, 760), *range(760, 770)]},
    **{str(z): "sanantonio" for z in [*range(780, 786)]},
    **{str(z): "austin" for z in [786, 787]},
    **{str(z): "houston" for z in [*range(770, 780), *range(788, 792)]},
    **{str(z): "denver" for z in [*range(800, 817)]},
    **{str(z): "phoenix" for z in [*range(850, 866)]},
    **{str(z): "albuquerque" for z in [*range(870, 885)]},
    **{str(z): "elpaso" for z in [885, 886, 887, 799]},
    **{str(z): "lasvegas" for z in [*range(889, 899)]},
    **{str(z): "losangeles" for z in [*range(900, 913)]},
    **{str(z): "sandiego" for z in [*range(919, 925), *range(917, 919)]},
    **{str(z): "sfbay" for z in [*range(940, 960)]},
    **{str(z): "sacramento" for z in [*range(956, 960), *range(930, 940)]},
    **{str(z): "portland" for z in [*range(970, 979)]},
    **{str(z): "seattle" for z in [*range(980, 995)]},
    "907": "anchorage",
    "967": "honolulu",
    "968": "honolulu",
}

_BODY_STYLE_MAP = {
    "convertible": 1,
    "coupe": 2,
    "hatchback": 3,
    "minivan": 4,
    "offroad": 5,
    "pickup": 6,
    "truck": 6,
    "sedan": 7,
    "suv": 9,
    "wagon": 10,
    "van": 11,
    "other": 12,
}


class CraigslistScraper(BaseScraper):
    name = "Craigslist"

    def _area_for_zip(self, zip_code: str) -> str:
        if not zip_code:
            return "sfbay"
        return _ZIP_PREFIX_TO_AREA.get(zip_code[:3], "sfbay")

    def search(self, filters: dict) -> list[Listing]:
        area = filters.get("cl_area") or self._area_for_zip(filters.get("zip", ""))
        url = f"https://{area}.craigslist.org/search/cta"

        query_parts = [p for p in [filters.get("make"), filters.get("model")] if p]
        params = {
            "auto_make_model": " ".join(query_parts),
            "min_price": filters.get("min_price", 1),
        }
        if filters.get("max_price"):
            params["max_price"] = filters["max_price"]
        if filters.get("year_min"):
            params["min_auto_year"] = filters["year_min"]
        if filters.get("year_max"):
            params["max_auto_year"] = filters["year_max"]
        style = (filters.get("style") or "").lower()
        if style in _BODY_STYLE_MAP:
            params["auto_bodytype"] = _BODY_STYLE_MAP[style]

        resp = self.get(url, params=params)
        if not resp:
            return []

        soup = BeautifulSoup(resp.text, "lxml")
        listings = []

        items = soup.select("li.cl-static-search-result")
        for item in items:
            try:
                listing = self._parse_item(item, filters)
                if listing:
                    listings.append(listing)
            except Exception:
                continue

        return listings

    def _parse_item(self, item, filters: dict) -> Listing | None:
        link_el = item.select_one("a")
        if not link_el:
            return None
        href = link_el.get("href", "")

        # Current CL markup: <li title="…"><a …><div class="title">…</div></a></li>
        title_el = item.select_one(".title")
        title = title_el.get_text(strip=True) if title_el else item.get("title", "")
        if not title:
            return None

        price_el = item.select_one(".price")
        price = None
        if price_el:
            raw = price_el.get_text(strip=True).replace("$", "").replace(",", "").strip()
            price = int(raw) if raw.isdigit() else None

        loc_el = item.select_one(".location")
        location = loc_el.get_text(strip=True) if loc_el else None

        year = extract_year(title)
        mileage = extract_mileage(title)

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
