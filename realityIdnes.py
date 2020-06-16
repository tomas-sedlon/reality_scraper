import requests
from bs4 import BeautifulSoup
from model.flat import Flat
import re
import yaml
import pandas as pd

class Scraper:
    def __init__(self):
        self.flats = []
        cfg = yaml.safe_load(open('config.yml'))
        baseUrl = cfg['realityIdnes_url']

        #baseUrl = "https://reality.idnes.cz/s/prodej/byty/cena-do-6000000/praha/?s-qc%5BsubtypeFlat%5D%5B0%5D=21&s-qc%5BsubtypeFlat%5D%5B1%5D=3k&s-qc%5BsubtypeFlat%5D%5B2%5D=31&s-qc%5BsubtypeFlat%5D%5B3%5D=4k&s-qc%5BusableAreaMin%5D=50&s-qc%5Bownership%5D%5B0%5D=personal&s-qc%5Bcondition%5D%5B0%5D=new&s-qc%5Bcondition%5D%5B1%5D=good-condition&s-qc%5Bcondition%5D%5B2%5D=maintained&s-qc%5Bcondition%5D%5B3%5D=after-reconstruction&s-qc%5Bmaterial%5D%5B0%5D=brick"

        #baseUrl = "https://reality.idnes.cz/s/prodej/byty/cena-do-6000000/praha/?s-qc%5BsubtypeFlat%5D%5B0%5D=21&s-qc%5BsubtypeFlat%5D%5B1%5D=3k&s-qc%5BsubtypeFlat%5D%5B2%5D=31&s-qc%5BsubtypeFlat%5D%5B3%5D=4k&s-qc%5BsubtypeFlat%5D%5B4%5D=41&s-qc%5BusableAreaMin%5D=50&s-qc%5Bownership%5D%5B0%5D=personal&s-qc%5Bmaterial%5D%5B0%5D=brick"
        self.urls = [baseUrl]
        for i in range(1,6):
            additionalUrl = baseUrl+ "&page="+str(i)
            self.urls.append(additionalUrl)

    def start_workflow(self):

        self.parse_pages(self.urls)
        return self.flats



    def parse_pages(self,urls):
        for url in urls:
            #print(url)
            response = requests.get(url,verify=False)
            soup = BeautifulSoup(response.content,'html.parser',fromEncoding='utf-8')

            posts = soup.findAll("div", {"class": "c-list-products__inner"})
            #print(mydivs)
            self.parse_posts(posts)

    def parse_posts(self,posts):
        for post in posts:
            #print(post)
            price = post.find("p",class_="c-list-products__price").text.strip().replace("Kč","").replace(" ","")
            price = int(price)
            location = post.find("p",class_="c-list-products__info").text.strip()
            title = post.find("h2", class_="c-list-products__title").text.strip().replace("\n","").replace("prodejbytu","")
            size = int(title.split(',')[1].replace("m²","").strip())
            rooms = title.split(',')[0]
            room_base_coeff = int(rooms.split('+')[0])
            room_addons_coeff = 0.0 if "kk" in rooms else 0.5
            room_coeff = room_base_coeff + room_addons_coeff

            price_per_meter = price / size


            #print(price,location,title,size,price_per_meter)
            link = ""
            if room_coeff > 3.5:
                continue
            if size < 55:
                continue
            link = post.find("a",class_="c-list-products__link")['href']
            link = "https://reality.idnes.cz" + link

            link = link.split('?')[0]

            floor,penb,state = self.parse_post(link)

            if floor < 2:
                continue

            flat = Flat(title=location,
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

    def parse_post(self,link):
        floor = 1000
        penb = None
        state = "neutral"

        response = requests.get(link, verify=False)
        soup = BeautifulSoup(response.content, 'html.parser')

        div = soup.find("div", {"class": "row-main"})
        dt= div.find_all("dt")
        dd = div.find_all("dd")
        desc = div.find("div",class_="b-desc")
        desc_text = desc.find("p").text.strip()
        floor_regex = r"((?: )[1-9](?:\.))"

        for dt,dd in zip(dt,dd):
            if "Podlaží" == dt.text.strip():
                floor = dd.text.strip()
                if "přízemí" in floor:
                    floor = 0
                else:
                    floor = floor.split(".")[0]
                    floor = int(floor)
            if "PENB" == dt.text.strip():
                penb = dd.text.strip().split(' ')[0] if len(dd.text.strip()) >1 else dd.text.strip()

            if "Stav bytu" == dt.text.strip():
                state = dd.text.strip()

        if floor == 1000:
            pass
            #floor = re.findall(desc_text,floor_regex)
            #print(link)


            #print(dt,dd)
        #print(floor,penb)

        return floor,penb,state

if __name__ == "__main__":
    scraper = Scraper()
    scraper.start_workflow()

    for flat in scraper.flats:
        print(flat)