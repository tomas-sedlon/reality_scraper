class Flat:
    price = ""
    title = ""
    link = ""
    size = ""
    meters = 0
    price_per_meter = 0
    floor = "N/A"
    penb = "N/A"
    state = "neutral"

    def __init__(self,price,title,link, size, meters, price_per_meter,floor,penb,state):
        self.price = price
        self.title = title
        self.link = link
        self.size = size
        self.meters = meters
        self.price_per_meter = price_per_meter
        self.floor = floor
        self.penb = penb
        self.state = state

    def get_cmp_dict(self):
        cmp_dict = {
            "title" : self.title,
            "price" : self.price,
            "size" : self.size,
            "meters" : self.meters,
            "price_per_meter" : self.price_per_meter,
            "floor" : self.floor,
            "penb" : self.penb,
            "state" : self.state,
            "link": self.link

        }
        return cmp_dict
