import requests, sys

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
}

sites = [
    ("Autolist",   "https://www.autolist.com/toyota-camry?zip=94102&price_min=5000&price_max=25000"),
    ("CarsDirect", "https://www.carsdirect.com/cars-for-sale/listing/used/toyota/camry?zip=94102"),
    ("TrueCar",    "https://www.truecar.com/used-cars-for-sale/listings/toyota/camry/?zip=94102"),
    ("CarGurus",   "https://www.cargurus.com/Cars/new/nl_New_Cars_d.html?zip=94102"),
    ("CarMax",     "https://www.carmax.com/cars/toyota/camry?maxPrice=25000"),
]

for name, url in sites:
    try:
        r = requests.get(url, headers=HEADERS, timeout=8, allow_redirects=True)
        body_len = len(r.text)
        has_price = '$' in r.text and ',' in r.text
        print(f"{name:12s}: HTTP {r.status_code}  size={body_len:7d}  has_price={has_price}  final_url={r.url[:70]}")
    except Exception as e:
        print(f"{name:12s}: ERROR {type(e).__name__}: {str(e)[:60]}")
