import requests
from bs4 import BeautifulSoup
from model.flat import Flat
import re
import yaml
import pandas as pd
import os
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class Scraper:
    def __init__(self, cfg):
        self.flats = []
        baseUrl = cfg['realityIdnes_url']

        self.urls = [baseUrl]
        for i in range(1,39):
            additionalUrl = baseUrl+ "&page="+str(i)
            self.urls.append(additionalUrl)

    def start_workflow(self):

        self.parse_pages(self.urls)
        return self.flats



    def parse_pages(self,urls):
        for url in urls:
            response = requests.get(url,verify=False)
            soup = BeautifulSoup(response.content,'html.parser',fromEncoding='utf-8')

            posts = soup.findAll("div", {"class": "c-list-products__inner"})
            self.parse_posts(posts)

    def parse_posts(self,posts):
        for post in posts:

            price = post.find("p",class_="c-list-products__price").text.strip().replace("Kč","").replace(" ","").replace("Cenanavyžádání","999999999")
            price = int(price)
            location = post.find("p",class_="c-list-products__info").text.strip()
            title = post.find("h2", class_="c-list-products__title").text.strip().replace("\n","").replace("prodejbytu","")
            try:
                size = int(title.replace("m²","").strip().split(" ")[1])
            except Exception as e:
                print(f"Cannot parse title {title}, error: {repr(e)}")
                size = 1
            rooms = title.split(',')[0]
            try:
                room_base_coeff = int(rooms.split('+')[0])
            except Exception as e:
                room_base_coeff = 0.0
                print(f"Cannot parse post {post}, error: {repr(e)}")
            room_addons_coeff = 0.0 if "kk" in rooms else 0.5
            room_coeff = room_base_coeff + room_addons_coeff
            price_per_meter = price / size


            link = post.find("a",class_="c-list-products__link")['href']
            link = "https://reality.idnes.cz" + link

            link = link.split('?')[0]

            floor,penb,state = self.parse_post(link)

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


        return floor,penb,state
