from dataclasses import dataclass, field
from typing import Optional
import requests
import time
import re


@dataclass
class Listing:
    title: str
    price: Optional[int]
    url: str
    source: str
    make: Optional[str] = None
    model: Optional[str] = None
    year: Optional[int] = None
    mileage: Optional[int] = None
    location: Optional[str] = None
    deal_score: Optional[float] = None  # 1.0 – 5.0
    deal_label: Optional[str] = None

    def year_bucket(self) -> Optional[str]:
        if self.year is None:
            return None
        bucket = (self.year // 3) * 3
        return f"{bucket}-{bucket + 2}"

    def group_key(self) -> str:
        parts = [
            (self.make or "").lower(),
            (self.model or "").lower(),
            self.year_bucket() or "unknown",
        ]
        return "|".join(parts)


YEAR_RE = re.compile(r"\b(19[5-9]\d|20[0-2]\d)\b")
MILEAGE_RE = re.compile(r"([\d,]+)\s*(?:mi(?:les?)?|k\s*miles?)", re.IGNORECASE)


def extract_year(text: str) -> Optional[int]:
    m = YEAR_RE.search(text)
    return int(m.group(1)) if m else None


def extract_mileage(text: str) -> Optional[int]:
    m = MILEAGE_RE.search(text)
    if not m:
        return None
    raw = m.group(1).replace(",", "")
    value = int(raw)
    if "k" in m.group(0).lower() and value < 1000:
        value *= 1000
    return value


class BaseScraper:
    name = "Base"

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
                ),
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
            }
        )

    def get(self, url: str, params: dict = None, **kwargs):
        try:
            time.sleep(0.75)
            resp = self.session.get(url, params=params, timeout=15, **kwargs)
            resp.raise_for_status()
            return resp
        except requests.RequestException:
            return None

    def search(self, filters: dict) -> list[Listing]:
        raise NotImplementedError
