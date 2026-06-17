"""Runs from GitHub Actions to probe site accessibility and extract HTML structure."""
import requests, json, re
from bs4 import BeautifulSoup

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
}


def probe(name, url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=12, allow_redirects=True)
        print(f"\n{'='*60}")
        print(f"{name}: HTTP {r.status_code}  size={len(r.text):,}  url={r.url[:90]}")
        if r.status_code != 200:
            return

        soup = BeautifulSoup(r.text, 'lxml')
        prices = re.findall(r'\$[\d,]+', r.text)
        print(f"  Dollar amounts: {len(prices)}  sample={prices[:5]}")

        # Next.js __NEXT_DATA__
        nd = soup.find('script', id='__NEXT_DATA__')
        if nd and nd.string:
            data = json.loads(nd.string)
            pp = data.get('props', {}).get('pageProps', {})
            print(f"  __NEXT_DATA__ pageProps keys: {list(pp.keys())[:8]}")
            for key in ['inventory', 'vehicles', 'listings', 'results', 'cars', 'data', 'items']:
                if key in pp and isinstance(pp[key], list) and pp[key]:
                    items = pp[key]
                    print(f"  -> '{key}' list: {len(items)} items, first keys: {list(items[0].keys())[:12]}")
                    v = items[0]
                    for f in ['year', 'price', 'mileage', 'make', 'model', 'name', 'title', 'location', 'vin']:
                        if f in v:
                            print(f"       {f}: {v[f]}")
                    return

        # Nuxt
        if 'window.__NUXT__' in r.text:
            print("  Nuxt.js detected")
            prices_raw = re.findall(r'"price"\s*:\s*(\d+)', r.text[:100000])
            print(f"  'price' fields in first 100k: {prices_raw[:5]}")
            years_raw = re.findall(r'"year"\s*:\s*(20\d\d)', r.text[:100000])
            print(f"  'year' fields in first 100k: {years_raw[:5]}")
            titles_raw = re.findall(r'"title"\s*:\s*"([^"]{10,60})"', r.text[:100000])
            print(f"  'title' fields in first 100k: {titles_raw[:3]}")

    except Exception as e:
        print(f"\n{name}: ERROR {type(e).__name__}: {e}")


probe("CarMax",
    "https://www.carmax.com/cars/toyota/camry?minPrice=5000&maxPrice=25000&minYear=2016&zip=94102")
probe("CarsDirect",
    "https://www.carsdirect.com/cars-for-sale/listing/used/toyota/camry?zip=94102&radius=50&min_price=5000&max_price=25000")
