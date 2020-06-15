import requests
from bs4 import BeautifulSoup
from model.flat import Flat
from traceback import print_exc

class Scraper:
    def __init__(self):
        self.flats = []

        baseUrl = "https://realitymix.cz/vypis-nabidek/?form%5Badresa_kraj_id%5D[]=19&form%5Bcena_mena%5D=&form%5Bcena_normalizovana__from%5D=&form%5Bcena_normalizovana__to%5D=6000000&form%5Bdispozice%5D[]=10&form%5Bdispozice%5D[]=11&form%5Bdispozice%5D[]=4&form%5Bdispozice%5D[]=5&form%5Bdruh_objektu%5D[]=2&form%5Bexclusive%5D=&form%5Bfk_rk%5D=&form%5Binzerat_typ%5D=1&form%5Bnemovitost_typ%5D=4&form%5Bplocha__from%5D=50&form%5Bplocha__to%5D=&form%5Bpodlazi_cislo__from%5D=1&form%5Bpodlazi_cislo__to%5D=&form%5Bprojekt_id%5D=&form%5Bsearch_in_city%5D=&form%5Bsearch_in_text%5D=&form%5Bstari_inzeratu%5D=&form%5Bstav_objektu%5D=&form%5Btop_nabidky%5D=&form%5Bvlastnictvi%5D[]=1"
        self.urls = [baseUrl]
        for i in range(1, 3):
            additionalUrl = baseUrl + "&stranka=" + str(i)
            self.urls.append(additionalUrl)

    def start_workflow(self):
        self.parse_pages(self.urls)
        return self.flats

    def parse_pages(self,urls):
        for url in urls:
            #print(url)
            response = requests.get(url,verify=False)
            soup = BeautifulSoup(response.content,'html.parser',fromEncoding='utf-8')

            all_posts = soup.find("ul", {"class": "advert-list-items__items"})
            posts = all_posts.find_all("li")

            #print(mydivs)
            self.parse_posts(posts)

    def parse_post(self,link):

        state = 'N/A'
        penb = 'N/A'
        floor = 1000

        # parsing here
        response = requests.get(link, verify=False)
        soup = BeautifulSoup(response.content, 'html.parser', fromEncoding='utf-8')

        detail_info = soup.find("div",class_="detail-information")
        desc = soup.find("div", class_="advert-description__text-inner-inner").text.strip()




        info_items = detail_info.find_all("li",class_="detail-information__data-item")

        for item in info_items:
            text= item.text

            #print(text)

            if "Číslo podlaží v domě" in text:
                replaced = text.replace("Číslo podlaží v domě:","").strip()
                floor = int(replaced)

            if "Energetická náročnost budovy" in text:
                replaced = text.replace("Energetická náročnost budovy:", "").strip()
                if replaced == 'N/A':
                    penb = replaced
                else:
                    penb = replaced.split('-')[0].strip()
            if "Stav objektu" in text:
                replaced = text.replace("Stav objektu:", "").strip()
                state = replaced

        if "přízem" in desc:
            floor = 0

        return floor,penb, state

    def parse_posts(self,posts):
        for post in posts:

            try:
                heading = post.find("h2").text.strip()
                heading = heading.replace("Prodej bytu,","").replace(" ","")
                rooms = heading.split(',')[0]
                room_base_coeff = int(rooms.split('+')[0])
                room_addons_coeff = 0.0 if "kk" in rooms else 0.5
                room_coeff = room_base_coeff + room_addons_coeff
                meters = heading.split(',')[1]
                meters = int(meters.replace("m²","").strip())
                price = post.find("span",class_="advert-list-items__content-price-price").text.strip()
                price = price.replace("Kč","")
                price = price.encode("ascii", errors="ignore").decode()
                price = int(price.replace(" ","").strip())
            
                price_per_meter = price / meters
                location = post.find("p",class_="advert-list-items__content-address").text.strip()
                floor = "N/A"
                penb = "N/A"
                state = "N/A"
                link = post.find("a",class_="form-price")["href"]

                #print(room_coeff,meters,location,price, link)
                floor, penb, state = self.parse_post(link)

                if floor < 2:
                    continue

                flat = Flat(
                    price=price,
                    title=location,
                    link=link,
                    size=room_coeff,
                    meters=meters,
                    price_per_meter=price_per_meter,
                    floor=floor,
                    penb=penb,
                    state=state
                )
                self.flats.append(flat.get_cmp_dict())
            except AttributeError as ae:
                pass # this is an advert
            except Exception as e:
                print("Exception occurred in post ------------------------------------------------------------------")
                print(e.__class__.__name__,e)
                if "Cena" in str(e):
                    pass
                elif "Rezerv" in str(e):
                    pass
                else:
                    print(post)




if __name__ == "__main__":
    scraper = Scraper()
    scraper.start_workflow()

    for flat in scraper.flats:
        print(flat)
