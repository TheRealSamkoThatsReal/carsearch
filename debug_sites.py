"""Runs from GitHub Actions to probe site accessibility and extract HTML structure."""
import requests, json, re

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

        prices = re.findall(r'\$[\d,]+', r.text)
        print(f"  Dollar amounts: {len(prices)}  sample={prices[:5]}")

        # Next.js __NEXT_DATA__
        m = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.+?)</script>', r.text, re.DOTALL)
        if m:
            data = json.loads(m.group(1))
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
        if "window.__NUXT__" in r.text:
            print("  Nuxt.js detected")
            prices_raw = re.findall(r'"price"\s*:\s*(\d+)', r.text[:100000])
            print(f"  'price' fields in first 100k: {prices_raw[:5]}")
            years_raw = re.findall(r'"year"\s*:\s*(20\d\d)', r.text[:100000])
            print(f"  'year' fields in first 100k: {years_raw[:5]}")
            titles_raw = re.findall(r'"title"\s*:\s*"([^"]{10,60})"', r.text[:100000])
            print(f"  'title' fields in first 100k: {titles_raw[:3]}")

    except Exception as e:
        print(f"\n{name}: ERROR {type(e).__name__}: {e}")


def probe_carsdirect():
    HEADERS2 = {
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
    }
    r = requests.get('https://www.carsdirect.com/cars-for-sale/listing/used/toyota/camry?zip=94102&radius=50&min_price=5000&max_price=25000',
        headers=HEADERS2, timeout=15)
    html = r.text

    # Find context around first dollar price
    idx = html.find('$10,000')
    if idx == -1:
        idx = html.find('$15,000')
    if idx != -1:
        snippet = html[max(0, idx-300):idx+300]
        print("\nCarsDirect context around first price:")
        print(snippet[:600])

    # Look for JSON with listing arrays in the full text
    for pattern in [r'"listings"\s*:\s*\[', r'"vehicles"\s*:\s*\[', r'"inventory"\s*:\s*\[',
                    r'"cars"\s*:\s*\[', r'"results"\s*:\s*\[']:
        m = re.search(pattern, html)
        if m:
            print(f"\nFound pattern '{pattern}' at position {m.start()}")
            snippet = html[m.start():m.start()+500]
            print(snippet[:500])
            break

probe_carsdirect()
