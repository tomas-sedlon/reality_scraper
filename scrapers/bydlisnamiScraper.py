import requests
from bs4 import BeautifulSoup
import yaml
import os




class Scraper:
    def __init__(self, cfg):
        baseUrl = cfg['bydlisnami_url']
        #baseUrl = "https://www.bydlisnami.cz/nemovitosti?Ads%5Badvert_function%5D=1&Ads%5Badvert_type%5D=1&Ads%5BfromPrice%5D=0&Ads%5BtoPrice%5D=6+000+000&Ads%5Badvert_subtype%5D%5B%5D=5&Ads%5Badvert_subtype%5D%5B%5D=6&Ads%5Badvert_subtype%5D%5B%5D=7&Ads%5Badvert_subtype%5D%5B%5D=8&Ads%5Badvert_subtype%5D%5B%5D=9&Ads%5Bownership%5D%5B%5D=1&Ads%5BfromEstateArea%5D=&Ads%5BtoEstateArea%5D=&Ads%5BfromUsableArea%5D=&Ads%5BtoUsableArea%5D=&Ads%5Bloc_region_id%5D=1&Ads%5Bloc_city_id%5D=&Ads%5Bq%5D=&Ads_sort=top_date.desc&mobile_advert_type=1&mobile_loc_region=1"
        #baseUrl = "https://www.bezrealitky.cz/vypis/nabidka-prodej/byt/praha/2-1,3-kk,3-1,4-kk,4-1?priceTo=6%20000%20000&ownership%5B0%5D=osobni&construction%5B0%5D=cihla&surfaceFrom=50&_token=uOlMs5mRlC581leMdI66w1fRQs6Q_qOSPe2YbqBuiK8"
        urls = [baseUrl + "=&yt0="]
        for i in range(1,39):
            url = baseUrl + "&p=" + str(i) + "&yt0="
            urls.append(url)



        self.parse_pages(urls)

    def parse_pages(self,urls):
        for url in urls:
            print(url)
            response = requests.get(url,verify=False)
            soup = BeautifulSoup(response.content,'html.parser',fromEncoding='utf-8')



            mydivs = soup.findAll("div", {"class": "listview-item"})


            self.parse_posts(mydivs)



    def parse_posts(self,posts):

        for div in posts:

            #print(div)
            location = div.find('h3').find('a').text
            price = div.find("span",class_="price").text.replace("Kč","").strip()
            #price2 = price.replace("\\xa0790","")
            price = price.encode("ascii", errors="ignore").decode()
            try:
                price = int(price)
            except ValueError as e:
                continue
            #print(div)
            suburb = ""
            #suburb = location.split('-')[1].split(',')[0].strip()
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
