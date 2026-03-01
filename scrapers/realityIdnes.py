import requests
from bs4 import BeautifulSoup
from model.flat import Flat
import re
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'cs,en;q=0.9',
}


class Scraper:
    def __init__(self, cfg):
        self.flats = []
        baseUrl = cfg['realityIdnes_url']
        self.urls = [baseUrl]
        for i in range(1, 39):
            sep = '&' if '?' in baseUrl else '?'
            self.urls.append(f"{baseUrl}{sep}page={i}")

    def start_workflow(self):
        self.parse_pages(self.urls)
        return self.flats

    def parse_pages(self, urls):
        consecutive_errors = 0
        for i, url in enumerate(urls):
            try:
                print(f"INFO -- realityIdnes: parsing page {i + 1}")
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
        for post in posts:
            try:
                # Price
                price_el = post.find("p", class_="c-products__price")
                if not price_el:
                    continue
                price_text = price_el.get_text(strip=True)
                # Remove currency, spaces, non-breaking spaces, zero-width chars
                price_clean = re.sub(r'[^\d]', '', price_text.replace("Cenanavyžádání", "999999999"))
                if not price_clean:
                    continue
                price = int(price_clean)

                # Location
                location_el = post.find("p", class_="c-products__info")
                location = location_el.text.strip() if location_el else "N/A"

                # Title: "prodej bytu 1+kk 42 m²"
                title_el = post.find("h2", class_="c-products__title")
                if not title_el:
                    continue
                title = title_el.get_text(strip=True)

                # Parse meters from title
                m_match = re.search(r'(\d+)\s*m[²2]', title)
                size = int(m_match.group(1)) if m_match else 1

                # Parse rooms from title
                r_match = re.search(r'(\d\+(?:kk|\d))', title, re.IGNORECASE)
                rooms = r_match.group(1) if r_match else "0+0"

                try:
                    room_base_coeff = int(rooms.split('+')[0])
                except (ValueError, IndexError):
                    room_base_coeff = 0
                room_addons_coeff = 0.0 if "kk" in rooms else 0.5
                room_coeff = room_base_coeff + room_addons_coeff
                price_per_meter = price / size if size > 0 else 999999

                # Link - may be full URL or relative
                link_el = post.find("a", class_="c-products__link")
                if not link_el:
                    continue
                link = link_el['href']
                if not link.startswith('http'):
                    link = "https://reality.idnes.cz" + link
                link = link.split('?')[0]

                floor, penb, state = self.parse_post(link)

                flat = Flat(
                    title=location,
                    rooms=rooms,
                    size=room_coeff,
                    price=price,
                    price_per_meter=price_per_meter,
                    meters=size,
                    link=link,
                    floor=floor,
                    penb=penb,
                    state=state
                )
                self.flats.append(flat.get_cmp_dict())
            except Exception as e:
                print(f"Error parsing realityIdnes post: {repr(e)}")

    def parse_post(self, link):
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
