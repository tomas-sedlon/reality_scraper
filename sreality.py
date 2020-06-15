import requests
from bs4 import BeautifulSoup
from traceback import print_exc

from model.flat import Flat
class Scraper:
    def __init__(self):
        self.flats = []

        baseUrl = "https://www.sreality.cz/hledani/prodej/byty/praha?velikost=2%2B1,3%2Bkk,3%2B1,4%2Bkk&stavba=cihlova&vlastnictvi=osobni&stav=velmi-dobry-stav,dobry-stav,novostavby,po-rekonstrukci&plocha-od=50&plocha-do=10000000000&cena-od=0&cena-do=6000000"

        self.urls = [baseUrl+"&bez-aukce=1"]
        for i in range(1, 3):
            additionalUrl = baseUrl + "&strana=" + str(i) + "&bez-aukce=1"
            self.urls.append(additionalUrl)

    def start_workflow(self):
        self.parse_pages(self.urls)
        return self.flats

    def parse_pages(self, urls):
        # srealitky posts are rendered during runtime with JS, so we need to use selenium with JS support
        from selenium import webdriver

        self.driver = webdriver.PhantomJS("C:\\dev\\phantomjs-2.1.1-windows\\phantomjs-2.1.1-windows\\bin\\phantomjs.exe")

        #soupFromJokesCC = BeautifulSoup(driver.page_source)  # page_source fetches page after rendering is complete
        #driver.save_screenshot('screen.png')  # save a screenshot to disk

        #driver.quit()
        for url in urls:
            print("INFO -- parsing page")
            self.driver.get(url)
            #response = requests.get(url, verify=False)
            soup = BeautifulSoup(self.driver.page_source)



            posts = soup.find_all("div",class_="info")

            #print(posts)
            self.parse_posts(posts)
        self.driver.quit()

    def parse_posts(self,posts):
        for post in posts:

            location = post.find("span",class_="locality").text.strip()
            price = post.find("span", class_="norm-price").text.strip()
            heading = post.find("span",class_="name").text.strip()
            heading = heading.replace("Prodej bytu ","")
            heading = heading.encode("ascii", errors="ignore").decode()
            rooms = heading.split(' ')[0]
            room_base_coeff = int(rooms.split('+')[0])
            room_addons_coeff = 0.0 if "kk" in rooms else 0.5
            room_coeff = room_base_coeff + room_addons_coeff




            link = post.find("a",class_="title")['href']
            link = "https://sreality.cz" + link
            if price == "Info o ceně u RK":
                continue
            price = price.replace("Kč","")
            price = price.encode("ascii", errors="ignore").decode()
            price = int(price.replace(" ",""))

            try:
                meters = heading.replace('m', '').strip()
                meters = meters[-2:]
                meters = int(meters)
                price_per_meter = price / meters
                #print(location, price, room_coeff, meters, price_per_meter, link)

                floor, penb, state = self.parse_post(link)
                if floor == "1":
                    continue

                if price > 5500000:
                    continue
                flat = Flat(title=location,
                            size=room_coeff,
                            price=price,
                            price_per_meter=price_per_meter,
                            meters=meters,
                            link=link,
                            floor=floor,
                            penb=penb,
                            state=state
                            )
                self.flats.append(flat.get_cmp_dict())
            except IndexError as ie:
                print('error',heading)
                #print(heading,ie)
            except ValueError as ve:
                print('error',heading)
                #print(heading,ve)
            #print(post)

    def parse_post(self,link):
        floor = 1000
        penb = "N/A"
        state = "N/A"

        try:

            self.driver.get(link)
            soup = BeautifulSoup(self.driver.page_source)

            params = soup.find("div",class_="params")
            labels = params.find_all("li",class_="param")

            for param in labels:

                label = param.find("label",class_="param-label").text.strip()
                if "Energetická náročnost budovy" in label:
                    value = param.find("span").text.strip()
                    value = value.replace("Třída ",'')

                    penb = value.split('-').strip()
                if "Stav objektu" in label:
                    value = param.find("span").text.strip()
                    state = value
                if "Podlaží" in label:
                    value = param.find("span").text.strip()
                    floor = value.split('.')[0]
        except Exception as e:
            print(e.__class__.__name__,e)
            print_exc()
            print(link)
            print("------------------------")


        return floor, penb, state





if __name__ == "__main__":
    scraper = Scraper()
    scraper.start_workflow()

    for flat in scraper.flats:
        print(flat)

