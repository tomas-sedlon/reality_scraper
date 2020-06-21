import requests
from bs4 import BeautifulSoup
import yaml
import os




class Scraper:
    def __init__(self, cfg):
        baseUrl = cfg['bydlisnami_url']
        self.flats = []
        self.urls = [baseUrl + "=&yt0="]
        for i in range(1,39):
            url = baseUrl + "&p=" + str(i) + "&yt0="
            self.urls.append(url)

    def start_workflow(self):
        self.parse_pages(self.urls)
        return self.flats

    def parse_pages(self,urls):
        for url in urls:
            print(url)
            response = requests.get(url,verify=False)
            soup = BeautifulSoup(response.content,'html.parser',fromEncoding='utf-8')



            mydivs = soup.findAll("div", {"class": "listview-item"})


            self.parse_posts(mydivs)



    def parse_posts(self,posts):

        for div in posts:

            location = div.find('h3').find('a').text
            price = div.find("span",class_="price").text.replace("Kč","").strip()
            price = price.encode("ascii", errors="ignore").decode()
            try:
                price = int(price)
            except ValueError as e:
                continue
            suburb = ""
            try:
                location_splitted = location.split(",")
                size = int(location_splitted[-1].replace("m2","").strip())
                rooms = location_splitted[0].replace("Prodej bytu","").strip()
                room_base_coeff = int(rooms.split('+')[0])
                room_addons_coeff = 0.0 if "kk" in rooms else 0.5
                room_coeff = room_base_coeff + room_addons_coeff
                price_per_meter = price / size

                desc = div.find('p',class_="hidden-sm").text.strip()
            except ValueError as e:
                continue

            if "panel" in desc or "ateliér" in desc:
                print("panel")
                continue

            print(location,suburb,size,rooms,room_coeff,price,price_per_meter,desc)

            continue
            heading = div.find("p", class_='product__note').text.strip()
            meters = heading.replace("Prodej bytu","").replace("m²","")

            size = meters.split(',')[1].strip()
            size = int(size)
            price = div.find("strong",class_="product__value").text.strip().replace("Kč","").replace(".","").strip()
            price = int(price)

            price_per_meter = price / size

            price_per_room = price / room_coeff
            if price_per_room > 2500000.0:
                continue
            if price_per_meter > 95000.0:
                continue
            print(location,suburb,price,room_coeff,rooms,size,price_per_meter, price_per_room)
