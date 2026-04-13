import requests
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from model.flat import Flat
from model.property import HouseProperty, LotProperty
from scrapers.geo import haversine_km
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# sreality category_main_cb values
CATEGORY_MAP = {
    'flat': 1,
    'house': 2,
    'lot': 3,
}

# URL path segment per type
URL_TYPE_MAP = {
    'flat': 'byt',
    'house': 'dum',
    'lot': 'pozemek',
}

# category_sub_cb → URL slug for houses
HOUSE_SUB_SLUGS = {
    33: 'cinzovni-dum',
    35: 'zemedelska-usedlost',
    37: 'rodinny',
    39: 'vila',
    43: 'chalupa',
    44: 'na-klic',
    47: 'pamatka-jine',
}

# category_sub_cb → URL slug for lots
LOT_SUB_SLUGS = {
    18: 'komercni',
    19: 'pole',
    20: 'lesy',
    21: 'louky',
    22: 'bydleni',
    23: 'zahrady',
    24: 'ostatni',
    25: 'sady-vinice',
    46: 'rybniky',
}


class Scraper:
    API_BASE = "https://www.sreality.cz/api/cs/v2/estates"

    def __init__(self, cfg, property_type='flat'):
        self.flats = []
        self.property_type = property_type
        self.sreality_url = cfg.get('sreality_url', '')
        self.pages = cfg.get('sreality_pages', 3)
        self.location = cfg.get('location', {})

    def _build_api_params(self):
        """Build API query params from the config URL."""
        params = {
            'category_main_cb': CATEGORY_MAP.get(self.property_type, 1),
            'category_type_cb': 1,   # sale
            'per_page': 60,
            'bez-aukce': 1,
        }

        # Use district_id from location config, otherwise fall back to URL-based region
        if self.location and self.location.get('sreality_district_id'):
            params['locality_district_id'] = self.location['sreality_district_id']
        elif not self.sreality_url:
            params['locality_region_id'] = 10  # Prague default

        url = self.sreality_url
        price_from = ''
        price_to = ''
        if 'cena-od=' in url:
            m = re.search(r'cena-od=(\d+)', url)
            if m:
                price_from = m.group(1)
        if 'cena-do=' in url:
            m = re.search(r'cena-do=(\d+)', url)
            if m:
                price_to = m.group(1)
        if price_from or price_to:
            params['czk_price_summary_order2'] = f"{price_from}|{price_to}"
        if 'plocha-od=' in url:
            m = re.search(r'plocha-od=(\d+)', url)
            if m:
                params['usable_area'] = f"{m.group(1)}|10000000"
        if 'patro-od=' in url:
            m = re.search(r'patro-od=(\d+)', url)
            if m:
                params['floor_number'] = f"{m.group(1)}|"
        if 'stavba=cihlova' in url:
            params['building_type_search'] = 1
        ownership = []
        if 'osobni' in url:
            ownership.append('1')
        if 'druzstevni' in url:
            ownership.append('4')
        if ownership:
            params['ownership'] = '|'.join(ownership)
        return params

    def start_workflow(self):
        self.parse_pages()
        return self.flats

    def parse_pages(self):
        params = self._build_api_params()
        type_label = self.property_type
        for page in range(1, self.pages + 1):
            params['page'] = page
            try:
                print(f"INFO -- sreality ({type_label}): parsing page {page}")
                response = requests.get(self.API_BASE, params=params, verify=False, timeout=30)
                response.raise_for_status()
                data = response.json()
                estates = data.get('_embedded', {}).get('estates', [])
                if not estates:
                    break
                self.parse_posts(estates)
            except Exception as e:
                print(f"Error fetching sreality page {page}: {repr(e)}")

    def parse_posts(self, estates):
        center_lat = self.location.get('lat') if self.location else None
        center_lng = self.location.get('lng') if self.location else None
        max_km = self.location.get('distance_km') if self.location else None

        valid = []
        for estate in estates:
            list_price = estate.get('price', 0)
            if list_price <= 0 or list_price >= 999999999:
                continue
            # GPS radius filter: skip listings outside the configured distance
            if center_lat and center_lng and max_km:
                gps = estate.get('gps', {})
                if gps:
                    dist = haversine_km(center_lat, center_lng, gps['lat'], gps['lon'])
                    if dist > max_km:
                        continue
            valid.append(estate)

        with ThreadPoolExecutor(max_workers=10) as pool:
            futures = {pool.submit(self.parse_post, e.get('hash_id', '')): e for e in valid}
            for future in as_completed(futures):
                estate = futures[future]
                try:
                    self._build_property(estate, future.result())
                except Exception as e:
                    print(f"Error parsing sreality estate: {repr(e)}")

    def _build_link(self, url_type, sub_slug, seo_locality, hash_id):
        return f"https://www.sreality.cz/detail/prodej/{url_type}/{sub_slug}/{seo_locality}/{hash_id}"

    def _build_property(self, estate, detail_result):
        name = estate.get('name', '')
        list_price = estate.get('price', 0)
        locality = estate.get('locality', '')
        hash_id = estate.get('hash_id', '')

        url_type = URL_TYPE_MAP.get(self.property_type, 'byt')

        # seo_locality is needed for a valid link; skip if detail fetch failed
        seo_idx = {'flat': 3, 'house': 5, 'lot': 5}.get(self.property_type, 3)
        if not detail_result[seo_idx]:
            return

        if self.property_type == 'flat':
            floor, penb, state, seo_locality, detail_price, detail_meters = detail_result
            rooms = self._parse_rooms(name)
            room_coeff = self._calc_room_coeff(rooms)
            price = detail_price if detail_price > 0 else list_price
            meters = detail_meters if detail_meters > 0 else self._parse_meters(name)
            price_per_meter = price / meters if meters > 0 else 999999
            link = self._build_link(url_type, rooms.replace('+', '%2B'), seo_locality, hash_id)
            prop = Flat(
                price=price, title=locality, link=link, rooms=rooms,
                size=room_coeff, meters=meters, price_per_meter=price_per_meter,
                floor=floor, penb=penb, state=state
            )

        elif self.property_type == 'house':
            living_area, lot_size, house_type, penb, state, seo_locality, detail_price, sub_slug = detail_result
            price = detail_price if detail_price > 0 else list_price
            # Fallback: parse living area from name ("Prodej rodinného domu 127 m²")
            if living_area == 0:
                living_area = self._parse_meters(name)
            # Fallback: parse lot size from name ("pozemek 593 m²")
            if lot_size == 0:
                lot_size = self._parse_lot_from_name(name)
            price_per_meter = price / living_area if living_area > 0 else 999999
            link = self._build_link(url_type, sub_slug, seo_locality, hash_id)
            prop = HouseProperty(
                price=price, title=locality, link=link,
                living_area=living_area, lot_size=lot_size, house_type=house_type,
                price_per_meter=price_per_meter, penb=penb, state=state
            )

        elif self.property_type == 'lot':
            lot_size, water, gas, electricity, sewer, seo_locality, detail_price, sub_slug = detail_result
            price = detail_price if detail_price > 0 else list_price
            # Fallback: parse lot size from name
            if lot_size == 0:
                lot_size = self._parse_meters(name)
            price_per_meter = price / lot_size if lot_size > 0 else 999999
            link = self._build_link(url_type, sub_slug, seo_locality, hash_id)
            prop = LotProperty(
                price=price, title=locality, link=link,
                lot_size=lot_size, price_per_meter=price_per_meter,
                water=water, gas=gas, electricity=electricity, sewer=sewer
            )

        self.flats.append(prop.get_cmp_dict())

    def parse_post(self, hash_id):
        """Fetch detail for a single estate via API."""
        if self.property_type == 'house':
            return self._parse_post_house(hash_id)
        elif self.property_type == 'lot':
            return self._parse_post_lot(hash_id)
        else:
            return self._parse_post_flat(hash_id)

    def _parse_post_flat(self, hash_id):
        floor = 1000
        penb = "N/A"
        state = "N/A"
        seo_locality = ""
        detail_price = 0
        detail_meters = 0

        try:
            url = f"{self.API_BASE}/{hash_id}"
            response = requests.get(url, verify=False, timeout=30)
            response.raise_for_status()
            data = response.json()

            seo = data.get('seo', {})
            seo_locality = seo.get('locality', '')

            price_czk = data.get('price_czk', {})
            if isinstance(price_czk, dict):
                detail_price = price_czk.get('value_raw', 0)

            for item in data.get('items', []):
                item_name = item.get('name', '')
                value = item.get('value', '')
                if isinstance(value, list) and value:
                    value = value[0].get('value', '') if isinstance(value[0], dict) else str(value[0])

                if 'Podlaží' in item_name:
                    floor_str = str(value).split('.')[0].strip()
                    try:
                        floor = int(floor_str)
                    except (ValueError, TypeError):
                        floor = 1000

                if 'Energetická náročnost budovy' in item_name:
                    penb_val = str(value).replace('Třída ', '').strip()
                    penb = penb_val.split('-')[0].strip() if penb_val else "N/A"

                if 'Stav objektu' in item_name:
                    state = str(value).strip() if value else "N/A"

                if 'Užitná ploch' in item_name:
                    try:
                        detail_meters = int(float(str(value).strip()))
                    except (ValueError, TypeError):
                        pass

        except Exception as e:
            print(f"Error fetching sreality detail {hash_id}: {repr(e)}")

        return floor, penb, state, seo_locality, detail_price, detail_meters

    def _parse_post_house(self, hash_id):
        living_area = 0
        lot_size = 0
        house_type = "N/A"
        penb = "N/A"
        state = "N/A"
        seo_locality = ""
        detail_price = 0
        sub_slug = "rodinny"

        try:
            url = f"{self.API_BASE}/{hash_id}"
            response = requests.get(url, verify=False, timeout=30)
            response.raise_for_status()
            data = response.json()

            seo = data.get('seo', {})
            seo_locality = seo.get('locality', '')
            sub_cb = seo.get('category_sub_cb')
            if sub_cb:
                sub_slug = HOUSE_SUB_SLUGS.get(sub_cb, 'rodinny')

            price_czk = data.get('price_czk', {})
            if isinstance(price_czk, dict):
                detail_price = price_czk.get('value_raw', 0)

            for item in data.get('items', []):
                item_name = item.get('name', '')
                value = item.get('value', '')
                if isinstance(value, list) and value:
                    value = value[0].get('value', '') if isinstance(value[0], dict) else str(value[0])

                # API returns "Užitná ploch" (without trailing 'a')
                if 'Užitná ploch' in item_name:
                    try:
                        living_area = int(float(str(value).strip()))
                    except (ValueError, TypeError):
                        pass
                if 'Plocha pozemku' in item_name:
                    try:
                        lot_size = int(float(str(value).strip()))
                    except (ValueError, TypeError):
                        pass
                if 'Typ domu' in item_name:
                    house_type = str(value).strip() if value else "N/A"
                if 'Energetická náročnost budovy' in item_name:
                    penb_val = str(value).replace('Třída ', '').strip()
                    penb = penb_val.split('-')[0].strip() if penb_val else "N/A"
                if 'Stav objektu' in item_name:
                    state = str(value).strip() if value else "N/A"

        except Exception as e:
            print(f"Error fetching sreality detail {hash_id}: {repr(e)}")

        return living_area, lot_size, house_type, penb, state, seo_locality, detail_price, sub_slug

    def _parse_post_lot(self, hash_id):
        lot_size = 0
        water = "N/A"
        gas = "N/A"
        electricity = "N/A"
        sewer = "N/A"
        seo_locality = ""
        detail_price = 0
        sub_slug = "bydleni"

        try:
            url = f"{self.API_BASE}/{hash_id}"
            response = requests.get(url, verify=False, timeout=30)
            response.raise_for_status()
            data = response.json()

            seo = data.get('seo', {})
            seo_locality = seo.get('locality', '')
            sub_cb = seo.get('category_sub_cb')
            if sub_cb:
                sub_slug = LOT_SUB_SLUGS.get(sub_cb, 'bydleni')

            price_czk = data.get('price_czk', {})
            if isinstance(price_czk, dict):
                detail_price = price_czk.get('value_raw', 0)

            for item in data.get('items', []):
                item_name = item.get('name', '')
                value = item.get('value', '')
                if isinstance(value, list) and value:
                    value = value[0].get('value', '') if isinstance(value[0], dict) else str(value[0])

                if 'Plocha pozemku' in item_name or item_name == 'Plocha':
                    try:
                        lot_size = int(float(str(value).strip()))
                    except (ValueError, TypeError):
                        pass
                if 'Voda' in item_name or 'Vodovod' in item_name:
                    water = str(value).strip() if value else "N/A"
                if 'Plyn' in item_name:
                    gas = str(value).strip() if value else "N/A"
                if 'Elektřina' in item_name:
                    electricity = str(value).strip() if value else "N/A"
                if 'Kanalizace' in item_name or 'Odpad' in item_name:
                    sewer = str(value).strip() if value else "N/A"

        except Exception as e:
            print(f"Error fetching sreality detail {hash_id}: {repr(e)}")

        return lot_size, water, gas, electricity, sewer, seo_locality, detail_price, sub_slug

    @staticmethod
    def _parse_meters(name):
        """Parse first m² value from name (e.g. '127 m²' from 'Prodej domu 127 m²')."""
        m = re.search(r'(\d+)\s*m[²2]', name)
        return int(m.group(1)) if m else 0

    @staticmethod
    def _parse_lot_from_name(name):
        """Parse lot size from name (e.g. '593' from 'pozemek 593 m²')."""
        m = re.search(r'pozemek\s+(\d[\d\s]*)\s*m[²2]', name)
        if m:
            return int(m.group(1).replace(' ', ''))
        return 0

    @staticmethod
    def _parse_rooms(name):
        m = re.search(r'(\d\+(?:kk|\d))', name, re.IGNORECASE)
        return m.group(1) if m else "0+0"

    @staticmethod
    def _calc_room_coeff(rooms):
        try:
            parts = rooms.split('+')
            base = int(parts[0])
            addon = 0.0 if 'kk' in parts[1].lower() else 0.5
            return base + addon
        except (IndexError, ValueError):
            return 0.0
