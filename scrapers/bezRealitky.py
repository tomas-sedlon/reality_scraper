import requests
import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from bs4 import BeautifulSoup
from model.flat import Flat
from model.property import HouseProperty, LotProperty
from scrapers.geo import haversine_km
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

# Map building type codes to Czech strings
BUILDING_TYPE_MAP = {
    'DETACHED': 'Samostatný',
    'SEMI_DETACHED': 'Řadový',
    'TERRACED': 'Řadový',
    'FARM': 'Usedlost',
    'VILLA': 'Vila',
    'OTHER': 'Ostatní',
}


class Scraper:
    BASE_URL = "https://www.bezrealitky.cz"

    def __init__(self, cfg, property_type='flat'):
        self.flats = []
        self.property_type = property_type
        self.base_listing_url = cfg.get('bezrealitky_url', '')
        self.pages = cfg.get('bezrealitky_pages', 5)
        self.location = cfg.get('location', {})

    def start_workflow(self):
        if not self.base_listing_url:
            print(f"INFO -- bezrealitky ({self.property_type}): no URL configured, skipping")
            return self.flats
        self.parse_pages()
        return self.flats

    def parse_pages(self):
        type_label = self.property_type
        for page in range(0, self.pages):
            url = self.base_listing_url
            if page > 0:
                sep = '&' if '?' in url else '?'
                url = f"{url}{sep}page={page}"
            try:
                print(f"INFO -- bezrealitky ({type_label}): parsing page {page + 1}")
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
        center_lat = self.location.get('lat') if self.location else None
        center_lng = self.location.get('lng') if self.location else None
        max_km = self.location.get('distance_km') if self.location else None

        prepared = []
        for listing in listings:
            price = listing.get('price', 0)
            if not price or price <= 0:
                continue
            # GPS radius filter
            if center_lat and center_lng and max_km:
                gps = listing.get('gps', {})
                if isinstance(gps, dict) and gps.get('lat') and gps.get('lng'):
                    dist = haversine_km(center_lat, center_lng, gps['lat'], gps['lng'])
                    if dist > max_km:
                        continue
            address = listing.get('address', '')
            if not address:
                for k, v in listing.items():
                    if k.startswith('address') and isinstance(v, str):
                        address = v
                        break
            if not address:
                address = listing.get('locality', '')
            uri = listing.get('uri', '')
            listing_id = listing.get('id', '')
            link = f"{self.BASE_URL}/nemovitosti-byty-domy/{uri}" if uri else f"{self.BASE_URL}/nemovitosti-byty-domy/{listing_id}"
            prepared.append((listing, address, link))

        with ThreadPoolExecutor(max_workers=10) as pool:
            futures = {pool.submit(self.parse_post, link): (listing, address, link) for listing, address, link in prepared}
            for future in as_completed(futures):
                listing, address, link = futures[future]
                try:
                    self._build_property(listing, address, link, future.result())
                except Exception as e:
                    print(f"Error parsing bezrealitky listing: {repr(e)}")

    def _build_property(self, listing, address, link, detail_result):
        price = listing.get('price', 0)

        if self.property_type == 'flat':
            surface = listing.get('surface', 0)
            disposition = listing.get('disposition', '')
            rooms = DISPOSITION_MAP.get(disposition, disposition)
            room_coeff = self._calc_room_coeff(rooms)
            meters = int(surface) if surface else 0
            price_per_meter = price / meters if meters > 0 else 999999
            floor, penb, state = detail_result
            prop = Flat(
                price=price, title=address, link=link, rooms=rooms,
                size=room_coeff, meters=meters, price_per_meter=price_per_meter,
                floor=floor, penb=penb, state=state
            )

        elif self.property_type == 'house':
            surface = listing.get('surface', 0)
            living_area = int(surface) if surface else 0
            surface_land = listing.get('surfaceLand', 0)
            lot_size = int(surface_land) if surface_land else 0
            price_per_meter = price / living_area if living_area > 0 else 999999
            building_type_raw, penb, state = detail_result
            building_type = listing.get('buildingType', building_type_raw)
            house_type = BUILDING_TYPE_MAP.get(building_type, str(building_type))
            prop = HouseProperty(
                price=price, title=address, link=link,
                living_area=living_area, lot_size=lot_size, house_type=house_type,
                price_per_meter=price_per_meter, penb=penb, state=state
            )

        elif self.property_type == 'lot':
            surface_land = listing.get('surfaceLand', 0) or listing.get('surface', 0)
            lot_size = int(surface_land) if surface_land else 0
            price_per_meter = price / lot_size if lot_size > 0 else 999999
            water, gas, electricity, sewer = detail_result
            prop = LotProperty(
                price=price, title=address, link=link,
                lot_size=lot_size, price_per_meter=price_per_meter,
                water=water, gas=gas, electricity=electricity, sewer=sewer
            )

        self.flats.append(prop.get_cmp_dict())

    def parse_post(self, link):
        """Fetch detail page and extract fields based on property_type."""
        if self.property_type == 'house':
            return self._parse_post_house(link)
        elif self.property_type == 'lot':
            return self._parse_post_lot(link)
        else:
            return self._parse_post_flat(link)

    def _parse_post_flat(self, link):
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
            advert = page_props.get('origAdvert', {})

            if advert:
                etage = advert.get('etage') or advert.get('floor')
                if etage is not None:
                    try:
                        floor = int(etage)
                    except (ValueError, TypeError):
                        floor = 1000
                penb_val = advert.get('penb', '')
                if penb_val:
                    penb = str(penb_val).split('-')[0].strip()
                condition = advert.get('condition', '')
                if condition:
                    state = CONDITION_MAP.get(condition, condition)

        except Exception as e:
            print(f"Error fetching bezrealitky detail {link}: {repr(e)}")

        return floor, penb, state

    def _parse_post_house(self, link):
        building_type = "N/A"
        penb = "N/A"
        state = "N/A"

        try:
            response = requests.get(link, headers=HEADERS, verify=False, timeout=30)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')
            script = soup.find('script', id='__NEXT_DATA__')
            if not script:
                return building_type, penb, state

            data = json.loads(script.string)
            page_props = data.get('props', {}).get('pageProps', {})
            advert = page_props.get('origAdvert', {})

            if advert:
                bt = advert.get('buildingType', '')
                if bt:
                    building_type = bt
                penb_val = advert.get('penb', '')
                if penb_val:
                    penb = str(penb_val).split('-')[0].strip()
                condition = advert.get('condition', '')
                if condition:
                    state = CONDITION_MAP.get(condition, condition)

        except Exception as e:
            print(f"Error fetching bezrealitky detail {link}: {repr(e)}")

        return building_type, penb, state

    def _parse_post_lot(self, link):
        water = "N/A"
        gas = "N/A"
        electricity = "N/A"
        sewer = "N/A"

        try:
            response = requests.get(link, headers=HEADERS, verify=False, timeout=30)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')
            script = soup.find('script', id='__NEXT_DATA__')
            if not script:
                return water, gas, electricity, sewer

            data = json.loads(script.string)
            page_props = data.get('props', {}).get('pageProps', {})
            advert = page_props.get('origAdvert', {})

            if advert:
                if advert.get('water'):
                    water = 'Ano'
                if advert.get('gas'):
                    gas = 'Ano'
                if advert.get('electricity'):
                    electricity = 'Ano'
                if advert.get('sewage') or advert.get('sewer'):
                    sewer = 'Ano'

        except Exception as e:
            print(f"Error fetching bezrealitky detail {link}: {repr(e)}")

        return water, gas, electricity, sewer

    @staticmethod
    def _calc_room_coeff(rooms):
        try:
            parts = rooms.split('+')
            base = int(parts[0])
            addon = 0.0 if 'kk' in parts[1].lower() else 0.5
            return base + addon
        except (IndexError, ValueError):
            return 0.0
