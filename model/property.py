class HouseProperty:
    price = ""
    title = ""
    link = ""
    living_area = 0
    lot_size = 0
    house_type = "N/A"
    price_per_meter = 0
    penb = "N/A"
    state = "N/A"

    def __init__(self, price, title, link, living_area, lot_size, house_type, price_per_meter, penb, state):
        if price_per_meter > 999999:
            price_per_meter = 999999

        self.price = price
        self.title = title
        self.link = link
        self.living_area = living_area
        self.lot_size = lot_size
        self.house_type = house_type
        self.price_per_meter = price_per_meter
        self.penb = penb
        self.state = state

    def get_cmp_dict(self):
        return {
            "title": self.title,
            "price": self.price,
            "living_area": self.living_area,
            "lot_size": self.lot_size,
            "house_type": self.house_type,
            "price_per_meter": self.price_per_meter,
            "penb": self.penb,
            "state": self.state,
            "link": self.link
        }


class LotProperty:
    price = ""
    title = ""
    link = ""
    lot_size = 0
    price_per_meter = 0
    water = "N/A"
    gas = "N/A"
    electricity = "N/A"
    sewer = "N/A"

    def __init__(self, price, title, link, lot_size, price_per_meter, water, gas, electricity, sewer):
        if price_per_meter > 999999:
            price_per_meter = 999999

        self.price = price
        self.title = title
        self.link = link
        self.lot_size = lot_size
        self.price_per_meter = price_per_meter
        self.water = water
        self.gas = gas
        self.electricity = electricity
        self.sewer = sewer

    def get_cmp_dict(self):
        return {
            "title": self.title,
            "price": self.price,
            "lot_size": self.lot_size,
            "price_per_meter": self.price_per_meter,
            "water": self.water,
            "gas": self.gas,
            "electricity": self.electricity,
            "sewer": self.sewer,
            "link": self.link
        }
