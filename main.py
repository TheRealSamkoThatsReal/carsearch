#!/usr/bin/env python3
"""
carsearch — aggregate used-car listings from multiple sites with deal ratings.

Usage examples
  python main.py --make Toyota --model Camry --max-price 25000 --zip 94102
  python main.py --make Ford --model F-150 --style truck --zip 60601 --radius 75
  python main.py --make Honda --model Civic --year-min 2018 --year-max 2022 --csv results.csv
"""

import argparse
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

from rich.console import Console

from scrapers import CraigslistScraper, CarsComScraper
from rater import rate_deals
from display import display_results

console = Console()


def parse_args():
    p = argparse.ArgumentParser(
        description="Search used-car listings across multiple sites.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument("--make", help="Car make, e.g. Toyota")
    p.add_argument("--model", help="Car model, e.g. Camry")
    p.add_argument(
        "--style",
        help="Body style: sedan, suv, truck, pickup, coupe, hatchback, wagon, convertible, van, minivan",
    )
    p.add_argument("--max-price", type=int, help="Maximum price ($)")
    p.add_argument("--min-price", type=int, default=500, help="Minimum price (default: $500)")
    p.add_argument("--year-min", type=int, help="Earliest model year")
    p.add_argument("--year-max", type=int, help="Latest model year")
    p.add_argument("--zip", default="94102", help="ZIP code for location-based search (default: 94102)")
    p.add_argument("--radius", type=int, default=50, help="Search radius in miles (default: 50)")
    p.add_argument(
        "--cl-area",
        help=(
            "Override Craigslist subdomain area, e.g. sfbay, chicago, newyork. "
            "Auto-detected from --zip when omitted."
        ),
    )
    p.add_argument("--csv", metavar="FILE", help="Also save results to a CSV file")
    p.add_argument("--no-cl", action="store_true", help="Skip Craigslist")
    p.add_argument("--no-cars", action="store_true", help="Skip Cars.com")
    return p.parse_args()


def main():
    args = parse_args()

    if not args.make and not args.model:
        console.print("[red]Error:[/red] Provide at least --make or --model.")
        sys.exit(1)

    filters = {
        "make": args.make,
        "model": args.model,
        "style": args.style,
        "max_price": args.max_price,
        "min_price": args.min_price,
        "year_min": args.year_min,
        "year_max": args.year_max,
        "zip": args.zip,
        "radius": args.radius,
        "cl_area": args.cl_area,
    }

    active_scrapers = []
    if not args.no_cl:
        active_scrapers.append(CraigslistScraper())
    if not args.no_cars:
        active_scrapers.append(CarsComScraper())

    if not active_scrapers:
        console.print("[red]All scrapers disabled.[/red]")
        sys.exit(1)

    query_desc = " ".join(filter(None, [args.make, args.model, args.style]))
    console.print(f"\n[bold cyan]Searching for:[/bold cyan] {query_desc or '(any)'}")
    if args.max_price:
        console.print(f"[dim]Max price:[/dim] ${args.max_price:,}")
    if args.year_min or args.year_max:
        yr = f"{args.year_min or ''}–{args.year_max or ''}"
        console.print(f"[dim]Years:[/dim] {yr}")
    console.print(f"[dim]ZIP:[/dim] {args.zip}  [dim]Radius:[/dim] {args.radius} mi\n")

    all_listings = []
    with ThreadPoolExecutor(max_workers=len(active_scrapers)) as pool:
        futures = {pool.submit(s.search, filters): s.name for s in active_scrapers}
        for future in as_completed(futures):
            name = futures[future]
            try:
                results = future.result()
                all_listings.extend(results)
                console.print(
                    f"  [green]✓[/green] [bold]{name}[/bold]: {len(results)} listing(s) found"
                )
            except Exception as exc:
                console.print(f"  [red]✗[/red] [bold]{name}[/bold]: {exc}")

    if not all_listings:
        console.print("\n[yellow]No listings found. Try broadening your filters.[/yellow]")
        sys.exit(0)

    console.print(f"\n[dim]Rating {len(all_listings)} listing(s)…[/dim]\n")
    rated = rate_deals(all_listings)
    display_results(rated, output_csv=args.csv)


if __name__ == "__main__":
    main()
