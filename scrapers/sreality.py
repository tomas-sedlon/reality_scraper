import requests
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from model.flat import Flat
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class Scraper:
    API_BASE = "https://www.sreality.cz/api/cs/v2/estates"

    def __init__(self, cfg):
        self.flats = []
        self.sreality_url = cfg.get('sreality_url', '')
        self.pages = cfg.get('sreality_pages', 3)

    def _build_api_params(self):
        """Build API query params from the config URL."""
        params = {
            'category_main_cb': 1,   # apartments
            'category_type_cb': 1,   # sale
            'locality_region_id': 10,  # Prague
            'per_page': 60,
            'bez-aukce': 1,
        }
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
        for page in range(1, self.pages + 1):
            params['page'] = page
            try:
                print(f"INFO -- sreality: parsing page {page}")
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
        # Filter valid estates and prepare for parallel detail fetching
        valid = []
        for estate in estates:
            name = estate.get('name', '')
            list_price = estate.get('price', 0)
            if list_price <= 0 or list_price >= 999999999:
                continue
            valid.append(estate)

        # Fetch all details in parallel
        with ThreadPoolExecutor(max_workers=10) as pool:
            futures = {pool.submit(self.parse_post, e.get('hash_id', '')): e for e in valid}
            for future in as_completed(futures):
                estate = futures[future]
                try:
                    name = estate.get('name', '')
                    list_price = estate.get('price', 0)
                    locality = estate.get('locality', '')
                    hash_id = estate.get('hash_id', '')
                    rooms = self._parse_rooms(name)
                    room_coeff = self._calc_room_coeff(rooms)

                    floor, penb, state, seo_locality, detail_price, detail_meters = future.result()

                    price = detail_price if detail_price > 0 else list_price
                    meters = detail_meters if detail_meters > 0 else self._parse_meters(name)
                    price_per_meter = price / meters if meters > 0 else 999999

                    link = f"https://www.sreality.cz/detail/prodej/byt/{rooms.replace('+', '%2B')}/{seo_locality}/{hash_id}"

                    flat = Flat(
                        price=price,
                        title=locality,
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
                    print(f"Error parsing sreality estate: {repr(e)}")

    def parse_post(self, hash_id):
        """Fetch detail for a single estate via API."""
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

            # Get SEO locality for building the browser URL
            seo = data.get('seo', {})
            seo_locality = seo.get('locality', '')

            # Get accurate price from detail
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

                # Get accurate usable area from detail
                if 'Užitná plocha' in item_name:
                    try:
                        detail_meters = int(float(str(value).strip()))
                    except (ValueError, TypeError):
                        pass

        except Exception as e:
            print(f"Error fetching sreality detail {hash_id}: {repr(e)}")

        return floor, penb, state, seo_locality, detail_price, detail_meters

    @staticmethod
    def _parse_meters(name):
        m = re.search(r'(\d+)\s*m[²2]', name)
        return int(m.group(1)) if m else 0

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
