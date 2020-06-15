from bezRealitky import Scraper as bezrealitky
from realityIdnes import Scraper as realityIdnes
from centrumReality import Scraper as centrumReality
from sreality import Scraper as sReality
import pandas as pd
class MasterScraper:
    def __init__(self):
        self.all_flats = []

        self.scrapers = [bezrealitky(),realityIdnes(),centrumReality(),sReality()]

    def check_existing(self, flat):
        for ex_flat in self.all_flats:
            if flat['price_per_meter'] == ex_flat['price_per_meter']:
                return True

        return False

    def start_workflow(self):

        for scraper in self.scrapers:
            flats = scraper.start_workflow()

            for flat in flats:
                if not self.check_existing(flat):
                    self.all_flats.append(flat)

    def show_results(self):

        data = pd.DataFrame(self.all_flats)

        sorted = data.sort_values(by=['price_per_meter'])
        pd.set_option('display.max_columns', 500)
        pd.set_option('display.max_rows', 500)
        pd.set_option('display.width', 2000)
        pd.set_option('display.expand_frame_repr', False)
        pd.set_option('max_colwidth', 800)
        sorted.style.set_properties(**{'text-align': 'left'}).set_table_styles(
            [dict(selector='th', props=[('text-align', 'left')])])
        pd.option_context('display.colheader_justify', 'right')
        print(sorted)

if __name__ == "__main__":
    scraper = MasterScraper()
    scraper.start_workflow()
    scraper.show_results()