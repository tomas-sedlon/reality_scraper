import requests
from bs4 import BeautifulSoup
from model.flat import Flat
import yaml
import os

class Scraper:
    def __init__(self, cfg):
        self.flats = []
        baseUrl = cfg['bezrealitky_url']
        #baseUrl = "https://www.bezrealitky.cz/vypis/nabidka-prodej/byt/praha/2-1,3-kk,3-1,4-kk,4-1?priceTo=6%20000%20000&ownership%5B0%5D=osobni&construction%5B0%5D=cihla&surfaceFrom=50&_token=uOlMs5mRlC581leMdI66w1fRQs6Q_qOSPe2YbqBuiK8"
        self.urls = [baseUrl,baseUrl+"&page=2",baseUrl+"&page=3"]



    def start_workflow(self):
        self.parse_pages(self.urls)
        return self.flats

    def parse_pages(self,urls):
        for url in urls:
            #try:
                response = requests.get(url,verify=False)
                soup = BeautifulSoup(response.content,'html.parser')

                mydivs = soup.findAll("div", {"class": "product__body"})
                self.parse_posts(mydivs)
            #except Exception as e:
                #print(f"Error while loadinf {url}: {repr(e)}")

    def parse_posts(self,posts):

        for div in posts:
            #print(div)
            location = div.find('strong').text
            suburb = location.split('-')[1]
            heading = div.find("p", class_='product__note').text.strip()
            meters = heading.replace("Prodej bytu","").replace("m²","")
            rooms = meters.split(',')[0].strip()
            size = meters.split(',')[1].strip()
            size = int(size)
            price = div.find("strong",class_="product__value").text.strip().replace("Kč","").replace(".","").strip()
            price = int(price)

            price_per_meter = price / size
            room_base_coeff = int(rooms.split('+')[0])
            room_addons_coeff =0.0 if "kk" in rooms else 0.5
            room_coeff = room_base_coeff + room_addons_coeff
            price_per_room = price / room_coeff

            if price_per_meter > 100000.0:
                continue

            if price > 5500000:
                continue

            link = div.find("a",class_="product__link")['href']
            link = "https://bezrealitky.cz" + link

            floor,penb,state = self.parse_post(link)

            if floor < 2:
                continue

            if state == "bad":
                continue

            flat = Flat(
                price=price,
                title=location,
                link=link,
                size=room_coeff,
                meters=size,
                price_per_meter=price_per_meter,
                floor=floor,
                penb=penb,
                state=state
            )
            self.flats.append(flat.get_cmp_dict())
            #print(location,suburb,price,room_coeff,rooms,size,price_per_meter, price_per_room)
            #print(div)

    def parse_post(self,link):
        floor = None
        state = "neutral"
        penb = None

        response = requests.get(link, verify=False)
        soup = BeautifulSoup(response.content, 'html.parser')

        div = soup.find("div", {"class": "b-desc"})

        #print(div)
        desc = div.find("p",class_="b-desc__info").text.strip()

        if "určen k rekonstrukci" in desc:
            state = "bad"
        rows = div.find_all("tr")

        for row in rows:
            content = row.text.strip()
            #print(content)

            if "PENB" in content:
                penb = content.replace("PENB:","").replace("\n","").strip()
            if "Podlaží:" in content:
                floor = content.replace("Podlaží:","").replace("\n","").strip()
        #print(desc)

        #print(floor,penb)
        try:
            floor = int(floor)
        except TypeError as e:
            floor = 1000
        return floor,penb,state
