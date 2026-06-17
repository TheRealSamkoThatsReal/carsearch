"""
Craigslist Regional scraper — searches multiple major metros in parallel to
supplement the local search and provide geographically diverse results.

Named CarsComScraper for import-compatibility with run.py / main.py.
"""
from concurrent.futures import ThreadPoolExecutor, as_completed
from .craigslist import CraigslistScraper
from .base import Listing

# Major Craigslist metros that are always searched for national coverage
_REGIONAL_AREAS = [
    "losangeles",
    "chicago",
    "newyork",
    "houston",
    "phoenix",
    "seattle",
    "denver",
    "atlanta",
    "dallas",
    "miami",
]


class CarsComScraper:
    """Searches several major Craigslist metros for broader national coverage."""

    name = "Craigslist (National)"

    def search(self, filters: dict) -> list[Listing]:
        local_area = CraigslistScraper()._area_for_zip(filters.get("zip", ""))

        # Pick 4 metros that aren't the user's local area
        areas = [a for a in _REGIONAL_AREAS if a != local_area][:4]

        all_listings: list[Listing] = []
        scraper = CraigslistScraper()
        scraper.name = self.name  # label with this scraper's name

        with ThreadPoolExecutor(max_workers=len(areas)) as pool:
            future_to_area = {
                pool.submit(self._search_area, scraper, area, filters): area
                for area in areas
            }
            for future in as_completed(future_to_area):
                try:
                    all_listings.extend(future.result())
                except Exception:
                    pass

        return all_listings

    @staticmethod
    def _search_area(scraper: CraigslistScraper, area: str, filters: dict) -> list[Listing]:
        patched = {**filters, "cl_area": area}
        listings = scraper.search(patched)
        for l in listings:
            l.source = CarsComScraper.name  # tag them so the UI groups them correctly
        return listings
