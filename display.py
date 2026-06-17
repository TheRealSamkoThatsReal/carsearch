"""Rich-based terminal display for car listings."""

from __future__ import annotations
import csv
import sys
from scrapers.base import Listing
from rich.console import Console
from rich.table import Table
from rich import box
from rich.text import Text

console = Console()

_SCORE_COLORS = {
    5.0: "bold green",
    4.0: "green",
    3.0: "yellow",
    2.0: "orange3",
    1.0: "red",
    0.0: "dim",
}

_STAR_CHARS = {
    5.0: "★★★★★",
    4.0: "★★★★☆",
    3.0: "★★★☆☆",
    2.0: "★★☆☆☆",
    1.0: "★☆☆☆☆",
    0.0: "—",
}


def _fmt_price(price: int | None) -> str:
    if price is None:
        return "—"
    return f"${price:,}"


def _fmt_mileage(miles: int | None) -> str:
    if miles is None:
        return "—"
    return f"{miles:,} mi"


def _fmt_year(year: int | None) -> str:
    return str(year) if year else "—"


def display_results(listings: list[Listing], output_csv: str | None = None) -> None:
    if not listings:
        console.print("[bold red]No listings found.[/bold red]")
        return

    # Sort: Great Deals first, then by price
    sorted_listings = sorted(
        listings,
        key=lambda l: (-(l.deal_score or 0), l.price or 9_999_999),
    )

    table = Table(
        title=f"[bold]Car Listings — {len(sorted_listings)} results[/bold]",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold cyan",
        expand=True,
    )

    table.add_column("Rating", width=14, no_wrap=True)
    table.add_column("Title", min_width=24)
    table.add_column("Price", width=10, justify="right")
    table.add_column("Year", width=6, justify="center")
    table.add_column("Mileage", width=12, justify="right")
    table.add_column("Source", width=12)
    table.add_column("Location", min_width=14)
    table.add_column("URL", min_width=20, overflow="fold")

    for l in sorted_listings:
        score = l.deal_score or 0.0
        color = _SCORE_COLORS.get(score, "white")
        stars = _STAR_CHARS.get(score, "")
        rating_text = Text(f"{stars}  {l.deal_label or ''}", style=color)

        table.add_row(
            rating_text,
            l.title,
            _fmt_price(l.price),
            _fmt_year(l.year),
            _fmt_mileage(l.mileage),
            l.source,
            l.location or "—",
            l.url,
        )

    console.print(table)
    _print_summary(sorted_listings)

    if output_csv:
        _write_csv(sorted_listings, output_csv)
        console.print(f"\n[green]Results saved to[/green] {output_csv}")


def _print_summary(listings: list[Listing]) -> None:
    priced = [l for l in listings if l.price is not None]
    if not priced:
        return
    prices = [l.price for l in priced]
    avg = sum(prices) / len(prices)
    median = sorted(prices)[len(prices) // 2]
    by_source: dict[str, int] = {}
    for l in listings:
        by_source[l.source] = by_source.get(l.source, 0) + 1

    console.print()
    console.print(
        f"[dim]Avg price: [/dim][bold]${avg:,.0f}[/bold]"
        f"  [dim]Median: [/dim][bold]${median:,}[/bold]"
        f"  [dim]Range: [/dim][bold]${min(prices):,} – ${max(prices):,}[/bold]"
    )
    source_str = "  ".join(f"[cyan]{src}[/cyan]: {n}" for src, n in by_source.items())
    console.print(f"[dim]Sources:[/dim]  {source_str}")


def _write_csv(listings: list[Listing], path: str) -> None:
    fields = [
        "rating",
        "score",
        "title",
        "price",
        "year",
        "mileage",
        "make",
        "model",
        "source",
        "location",
        "url",
    ]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for l in listings:
            writer.writerow(
                {
                    "rating": l.deal_label or "",
                    "score": l.deal_score or "",
                    "title": l.title,
                    "price": l.price or "",
                    "year": l.year or "",
                    "mileage": l.mileage or "",
                    "make": l.make or "",
                    "model": l.model or "",
                    "source": l.source,
                    "location": l.location or "",
                    "url": l.url,
                }
            )
