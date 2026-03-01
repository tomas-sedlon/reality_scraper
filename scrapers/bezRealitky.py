import requests
import json
import re
from bs4 import BeautifulSoup
from model.flat import Flat
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'cs,en;q=0.9',
}

# Map disposition codes to room strings
DISPOSITION_MAP = {
    'DISP_1_KK': '1+kk', 'DISP_1_1': '1+1',
    'DISP_2_KK': '2+kk', 'DISP_2_1': '2+1',
    'DISP_3_KK': '3+kk', 'DISP_3_1': '3+1',
    'DISP_4_KK': '4+kk', 'DISP_4_1': '4+1',
    'DISP_5_KK': '5+kk', 'DISP_5_1': '5+1',
}

# Map condition codes to Czech strings
CONDITION_MAP = {
    'VERY_GOOD': 'Velmi dobrý',
    'GOOD': 'Dobrý',
    'NEW_BUILDING': 'Novostavba',
    'AFTER_RECONSTRUCTION': 'Po rekonstrukci',
    'BEFORE_RECONSTRUCTION': 'Před rekonstrukcí',
    'BAD': 'Špatný',
    'UNDER_CONSTRUCTION': 'Ve výstavbě',
    'DEMOLITION': 'K demolici',
}


class Scraper:
    BASE_URL = "https://www.bezrealitky.cz"

    def __init__(self, cfg):
        self.flats = []
        self.base_listing_url = cfg['bezrealitky_url']
        self.pages = cfg.get('bezrealitky_pages', 5)

    def start_workflow(self):
        self.parse_pages()
        return self.flats

    def parse_pages(self):
        for page in range(0, self.pages):
            url = self.base_listing_url
            if page > 0:
                sep = '&' if '?' in url else '?'
                url = f"{url}{sep}page={page}"
            try:
                print(f"INFO -- bezrealitky: parsing page {page + 1}")
                response = requests.get(url, headers=HEADERS, verify=False, timeout=30)
                response.raise_for_status()
                listings = self._extract_listings(response.text)
                if not listings:
                    print(f"  No listings found on page {page + 1}, stopping.")
                    break
                self.parse_posts(listings)
            except Exception as e:
                print(f"Error fetching bezrealitky page {page + 1}: {repr(e)}")

    def _extract_listings(self, html):
        """Extract listing data from __NEXT_DATA__ JSON in the page."""
        soup = BeautifulSoup(html, 'html.parser')
        script = soup.find('script', id='__NEXT_DATA__')
        if not script:
            return []

        data = json.loads(script.string)
        listings = []

        page_props = data.get('props', {}).get('pageProps', {})

        # Try apolloCache (current structure)
        apollo_cache = page_props.get('apolloCache', {})
        if apollo_cache:
            for key, val in apollo_cache.items():
                if isinstance(val, dict) and val.get('__typename') == 'Advert':
                    listings.append(val)

        # Fallback: __APOLLO_STATE__
        if not listings:
            apollo_state = page_props.get('__APOLLO_STATE__', {})
            for key, val in apollo_state.items():
                if isinstance(val, dict) and val.get('__typename') == 'Advert':
                    listings.append(val)

        return listings

    def parse_posts(self, listings):
        for listing in listings:
            try:
                price = listing.get('price', 0)
                if not price or price <= 0:
                    continue

                # Address may be stored with locale param key like address({"locale":"CS"})
                address = listing.get('address', '')
                if not address:
                    for k, v in listing.items():
                        if k.startswith('address') and isinstance(v, str):
                            address = v
                            break
                if not address:
                    address = listing.get('locality', '')
                surface = listing.get('surface', 0)
                disposition = listing.get('disposition', '')
                uri = listing.get('uri', '')
                listing_id = listing.get('id', '')

                rooms = DISPOSITION_MAP.get(disposition, disposition)
                room_coeff = self._calc_room_coeff(rooms)
                meters = int(surface) if surface else 0
                price_per_meter = price / meters if meters > 0 else 999999

                link = f"{self.BASE_URL}/nemovitosti-byty-domy/{uri}" if uri else f"{self.BASE_URL}/nemovitosti-byty-domy/{listing_id}"

                floor, penb, state = self.parse_post(link)

                flat = Flat(
                    price=price,
                    title=address,
                    link=link,
                    rooms=rooms,
                    size=room_coeff,
                    meters=meters,
                    price_per_meter=price_per_meter,
                    floor=floor,
                    penb=penb,
                    state=state
                )
                self.flats.append(flat.get_cmp_dict())
            except Exception as e:
                print(f"Error parsing bezrealitky listing: {repr(e)}")

    def parse_post(self, link):
        """Fetch detail page and extract floor, PENB, condition from __NEXT_DATA__."""
        floor = 1000
        penb = "N/A"
        state = "neutral"

        try:
            response = requests.get(link, headers=HEADERS, verify=False, timeout=30)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')
            script = soup.find('script', id='__NEXT_DATA__')
            if not script:
                return floor, penb, state

            data = json.loads(script.string)
            page_props = data.get('props', {}).get('pageProps', {})

            # origAdvert has full detail data
            advert = page_props.get('origAdvert', {})

            if advert:
                # Floor — etage is the floor number
                etage = advert.get('etage') or advert.get('floor')
                if etage is not None:
                    try:
                        floor = int(etage)
                    except (ValueError, TypeError):
                        floor = 1000

                # PENB
                penb_val = advert.get('penb', '')
                if penb_val:
                    penb = str(penb_val).split('-')[0].strip()

                # Condition
                condition = advert.get('condition', '')
                if condition:
                    state = CONDITION_MAP.get(condition, condition)

        except Exception as e:
            print(f"Error fetching bezrealitky detail {link}: {repr(e)}")

        return floor, penb, state

    @staticmethod
    def _calc_room_coeff(rooms):
        try:
            parts = rooms.split('+')
            base = int(parts[0])
            addon = 0.0 if 'kk' in parts[1].lower() else 0.5
            return base + addon
        except (IndexError, ValueError):
            return 0.0
