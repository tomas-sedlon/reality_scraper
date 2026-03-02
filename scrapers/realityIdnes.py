import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from bs4 import BeautifulSoup
from model.flat import Flat
from model.property import HouseProperty, LotProperty
from scrapers.geo import haversine_km, geocode_cached
import re
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'cs,en;q=0.9',
}


class Scraper:
    def __init__(self, cfg, property_type='flat'):
        self.flats = []
        self.property_type = property_type
        self.location = cfg.get('location', {})
        baseUrl = cfg.get('realityIdnes_url', '')
        if not baseUrl:
            self.urls = []
            return
        self.urls = [baseUrl]
        for i in range(1, 39):
            sep = '&' if '?' in baseUrl else '?'
            self.urls.append(f"{baseUrl}{sep}page={i}")

    def start_workflow(self):
        if not self.urls:
            print(f"INFO -- realityIdnes ({self.property_type}): no URL configured, skipping")
            return self.flats
        self.parse_pages(self.urls)
        return self.flats

    def parse_pages(self, urls):
        type_label = self.property_type
        consecutive_errors = 0
        for i, url in enumerate(urls):
            try:
                print(f"INFO -- realityIdnes ({type_label}): parsing page {i + 1}")
                response = requests.get(url, headers=HEADERS, verify=False, timeout=30)
                response.raise_for_status()
                soup = BeautifulSoup(response.content, 'html.parser')

                posts = soup.findAll("div", {"class": "c-products__inner"})
                if not posts:
                    print(f"  No listings found on page {i + 1}, stopping.")
                    break
                consecutive_errors = 0
                self.parse_posts(posts)
            except Exception as e:
                consecutive_errors += 1
                print(f"Error fetching realityIdnes page {i + 1}: {repr(e)}")
                if consecutive_errors >= 2:
                    print(f"  Multiple consecutive errors, stopping pagination.")
                    break

    def parse_posts(self, posts):
        prepared = []
        for post in posts:
            try:
                price_el = post.find("p", class_="c-products__price")
                if not price_el:
                    continue
                price_text = price_el.get_text(strip=True)
                price_clean = re.sub(r'[^\d]', '', price_text.replace("Cenanavyžádání", "999999999"))
                if not price_clean:
                    continue
                price = int(price_clean)

                location_el = post.find("p", class_="c-products__info")
                location = location_el.text.strip() if location_el else "N/A"

                title_el = post.find("h2", class_="c-products__title")
                if not title_el:
                    continue
                title = title_el.get_text(strip=True)

                link_el = post.find("a", class_="c-products__link")
                if not link_el:
                    continue
                link = link_el['href']
                if not link.startswith('http'):
                    link = "https://reality.idnes.cz" + link
                link = link.split('?')[0]

                prepared.append((price, location, title, link))
            except Exception as e:
                print(f"Error parsing realityIdnes post: {repr(e)}")

        # GPS radius filter via geocoding of location strings
        center_lat = self.location.get('lat') if self.location else None
        center_lng = self.location.get('lng') if self.location else None
        max_km = self.location.get('distance_km') if self.location else None

        if center_lat and center_lng and max_km:
            # Geocode unique location strings
            unique_locations = set(loc for _, loc, _, _ in prepared)
            geo_lookup = {}
            for loc in unique_locations:
                geo_lookup[loc] = geocode_cached(loc)

            before_count = len(prepared)
            filtered = []
            for price, location, title, link in prepared:
                coords = geo_lookup.get(location)
                if coords:
                    dist = haversine_km(center_lat, center_lng, coords[0], coords[1])
                    if dist <= max_km:
                        filtered.append((price, location, title, link))
                # If geocoding failed, skip the listing (conservative filter)
            prepared = filtered
            print(f"  realityIdnes ({self.property_type}): GPS filter {before_count} → {len(prepared)} listings")

        with ThreadPoolExecutor(max_workers=10) as pool:
            futures = {pool.submit(self.parse_post, link): (price, location, title, link)
                       for price, location, title, link in prepared}
            for future in as_completed(futures):
                price, location, title, link = futures[future]
                try:
                    self._build_property(price, location, title, link, future.result())
                except Exception as e:
                    print(f"Error parsing realityIdnes post: {repr(e)}")

    def _build_property(self, price, location, title, link, detail_result):
        if self.property_type == 'flat':
            m_match = re.search(r'(\d[\d\s\xa0]*)\s*m[²2]', title)
            size = int(m_match.group(1).replace('\xa0', '').replace(' ', '')) if m_match else 1
            r_match = re.search(r'(\d\+(?:kk|\d))', title, re.IGNORECASE)
            rooms = r_match.group(1) if r_match else "0+0"
            try:
                room_base_coeff = int(rooms.split('+')[0])
            except (ValueError, IndexError):
                room_base_coeff = 0
            room_addons_coeff = 0.0 if "kk" in rooms else 0.5
            room_coeff = room_base_coeff + room_addons_coeff
            price_per_meter = price / size if size > 0 else 999999

            floor, penb, state = detail_result
            prop = Flat(
                title=location, rooms=rooms, size=room_coeff, price=price,
                price_per_meter=price_per_meter, meters=size, link=link,
                floor=floor, penb=penb, state=state
            )

        elif self.property_type == 'house':
            living_area, lot_size, house_type, penb, state = detail_result
            # Fallback: parse living area from title ("domu 102 m²")
            if living_area == 0:
                m = re.search(r'(\d[\d\s\xa0]*)\s*m[²2]', title)
                if m:
                    living_area = int(m.group(1).replace('\xa0', '').replace(' ', ''))
            # Fallback: parse lot size from title ("pozemkem 904 m²")
            if lot_size == 0:
                m = re.search(r'pozemk\w*\s+(\d[\d\s]*)\s*m[²2]', title)
                if m:
                    lot_size = int(m.group(1).replace('\xa0', '').replace(' ', ''))
            price_per_meter = price / living_area if living_area > 0 else 999999
            prop = HouseProperty(
                price=price, title=location, link=link,
                living_area=living_area, lot_size=lot_size, house_type=house_type,
                price_per_meter=price_per_meter, penb=penb, state=state
            )

        elif self.property_type == 'lot':
            lot_size, water, gas, electricity, sewer = detail_result
            # Fallback: parse lot size from title ("pozemku 762 m²")
            if lot_size == 0:
                m = re.search(r'(\d[\d\s]*)\s*m[²2]', title)
                if m:
                    lot_size = int(m.group(1).replace('\xa0', '').replace(' ', ''))
            price_per_meter = price / lot_size if lot_size > 0 else 999999
            prop = LotProperty(
                price=price, title=location, link=link,
                lot_size=lot_size, price_per_meter=price_per_meter,
                water=water, gas=gas, electricity=electricity, sewer=sewer
            )

        self.flats.append(prop.get_cmp_dict())

    def parse_post(self, link):
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
            soup = BeautifulSoup(response.content, 'html.parser')

            dts = soup.find_all("dt")
            dds = soup.find_all("dd")

            for dt_el, dd_el in zip(dts, dds):
                label = dt_el.text.strip()
                value = dd_el.text.strip()

                if "Podlaží" == label:
                    if "přízemí" in value.lower():
                        floor = 0
                    else:
                        floor_match = re.match(r'(\d+)', value)
                        if floor_match:
                            floor = int(floor_match.group(1))

                if "PENB" == label:
                    penb = value.split(' ')[0] if value else "N/A"

                if "Stav bytu" == label:
                    state = value

        except Exception as e:
            print(f"Error fetching realityIdnes detail {link}: {repr(e)}")

        return floor, penb, state

    def _parse_post_house(self, link):
        living_area = 0
        lot_size = 0
        house_type = "N/A"
        penb = "N/A"
        state = "N/A"

        try:
            response = requests.get(link, headers=HEADERS, verify=False, timeout=30)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')

            dts = soup.find_all("dt")
            dds = soup.find_all("dd")

            for dt_el, dd_el in zip(dts, dds):
                label = dt_el.text.strip()
                value = dd_el.text.strip()

                if "Užitná plocha" == label:
                    m = re.search(r'(\d[\d\s\xa0]*)', value)
                    if m:
                        living_area = int(m.group(1).replace('\xa0', '').replace(' ', ''))

                if "Plocha pozemku" == label:
                    m = re.search(r'(\d[\d\s\xa0]*)', value)
                    if m:
                        lot_size = int(m.group(1).replace('\xa0', '').replace(' ', ''))

                if label in ("Typ domu", "Poloha domu"):
                    house_type = value

                if "PENB" == label:
                    penb = value.split(' ')[0] if value else "N/A"

                if label in ("Stav objektu", "Stav domu", "Stav budovy"):
                    state = value

        except Exception as e:
            print(f"Error fetching realityIdnes detail {link}: {repr(e)}")

        return living_area, lot_size, house_type, penb, state

    def _parse_post_lot(self, link):
        lot_size = 0
        water = "N/A"
        gas = "N/A"
        electricity = "N/A"
        sewer = "N/A"

        try:
            response = requests.get(link, headers=HEADERS, verify=False, timeout=30)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')

            dts = soup.find_all("dt")
            dds = soup.find_all("dd")

            for dt_el, dd_el in zip(dts, dds):
                label = dt_el.text.strip()
                value = dd_el.text.strip()

                if "Plocha pozemku" == label or "Plocha" == label:
                    m = re.search(r'(\d[\d\s\xa0]*)', value)
                    if m:
                        lot_size = int(m.group(1).replace('\xa0', '').replace(' ', ''))

                if "Vodovod" == label:
                    water = value if value else "N/A"

                if "Plyn" == label:
                    gas = value if value else "N/A"

                if "Elektřina" == label:
                    electricity = value if value else "N/A"

                if "Kanalizace" == label:
                    sewer = value if value else "N/A"

        except Exception as e:
            print(f"Error fetching realityIdnes detail {link}: {repr(e)}")

        return lot_size, water, gas, electricity, sewer
