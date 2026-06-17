"""
Deal rating logic.

Groups listings by make + model + year bucket (3-year bands), then ranks
each listing by price within its group.  When mileage is available the
price is adjusted so that a high-mileage car at the same sticker price
scores slightly worse than a low-mileage one.

Rating scale
  5.0  Great Deal   – bottom ~15 % of group
  4.0  Good Deal    – 15–35 %
  3.0  Fair         – 35–65 %
  2.0  High Price   – 65–85 %
  1.0  Overpriced   – top ~15 %
"""

from __future__ import annotations
import statistics
from scrapers.base import Listing


_AVERAGE_MILEAGE_PER_YEAR = 12_000  # miles per year, used for mileage adjustment


def _adjusted_price(listing: Listing) -> float | None:
    """Return mileage-adjusted price or raw price."""
    if listing.price is None:
        return None

    if listing.mileage is None or listing.year is None:
        return float(listing.price)

    # Expected mileage for the vehicle's age vs. current year
    age = max(2026 - listing.year, 1)
    expected_miles = age * _AVERAGE_MILEAGE_PER_YEAR
    delta = listing.mileage - expected_miles  # positive = more miles than expected

    # Each 10 000 miles over/under expected shifts value by ~2 %
    adjustment_factor = 1 + (delta / 10_000) * 0.02
    adjustment_factor = max(0.7, min(1.5, adjustment_factor))  # clamp

    return listing.price * adjustment_factor


def _score_from_percentile(pct: float) -> tuple[float, str]:
    """Convert a 0-1 percentile (lower = cheaper) to a score + label."""
    if pct <= 0.15:
        return 5.0, "Great Deal"
    if pct <= 0.35:
        return 4.0, "Good Deal"
    if pct <= 0.65:
        return 3.0, "Fair"
    if pct <= 0.85:
        return 2.0, "High Price"
    return 1.0, "Overpriced"


def rate_deals(listings: list[Listing]) -> list[Listing]:
    """Mutate listings in-place with deal_score and deal_label; return them."""
    # Group by make/model/year-bucket
    groups: dict[str, list[Listing]] = {}
    for listing in listings:
        key = listing.group_key()
        groups.setdefault(key, []).append(listing)

    # Also keep a global fallback group for small groups
    all_prices = [_adjusted_price(l) for l in listings if l.price is not None]

    for group_listings in groups.values():
        adj_prices = [
            (_adjusted_price(l), l)
            for l in group_listings
            if l.price is not None
        ]
        if not adj_prices:
            continue

        # Use group prices when there are ≥3 data points; otherwise fall back
        # to global prices so we still produce a rating.
        pool = [p for p, _ in adj_prices]
        if len(pool) < 3:
            pool = [p for p in all_prices if p is not None]

        if not pool:
            continue

        pool_sorted = sorted(pool)
        n = len(pool_sorted)

        for adj_price, listing in adj_prices:
            # Rank = position in sorted pool (ties share the lower rank)
            rank = sum(1 for p in pool_sorted if p < adj_price)
            pct = rank / n
            listing.deal_score, listing.deal_label = _score_from_percentile(pct)

    # Listings with no price get an unrated label
    for listing in listings:
        if listing.deal_score is None:
            listing.deal_score = 0.0
            listing.deal_label = "No Price"

    return listings
