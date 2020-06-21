from scrapers.bezRealitky import Scraper as bezrealitky
from scrapers.realityIdnes import Scraper as realityIdnes
from scrapers.centrumReality import Scraper as centrumReality
from scrapers.sreality import Scraper as sReality
import pandas as pd
import os
import yaml
import sqlalchemy as db
from sqlalchemy.orm import sessionmaker


class MasterScraper:
    def __init__(self):
        self.all_flats = []

        self.scrapers = [bezrealitky(),realityIdnes(),centrumReality(),sReality()]
        cfg = yaml.safe_load(open(os.path.join(os.path.dirname(__file__),'config.yml')))
        self.res_file = cfg['res_file']
        # Define the MySQL engine using MySQL Connector/Python
        # change the user and pass if you ever want to use this as anything more than a home fun project
        self.engine = db.create_engine(
            f'mysql+mysqlconnector://root:root@localhost:3306/reality',
            echo=True
        )
        self.connection = self.engine.connect()
        self.metadata = db.MetaData()
        self.flats_table = db.Table('flats', self.metadata, autoload=True, autoload_with=engine)
        # create a configured "Session" class
        Session = sessionmaker(bind=self.engine)
        # create a Session
        self.session = Session()



    def check_existing(self, flat):
        for ex_flat in self.all_flats:
            if flat['price_per_meter'] == ex_flat['price_per_meter']:
                return True

        return False

    def start_scraping_workflow(self):

        for scraper in self.scrapers:
            flats = scraper.start_workflow()

            for flat in flats:
                if not self.check_existing(flat):
                    self.all_flats.append(flat)

    def get_current_results(self):
        data = pd.DataFrame(self.all_flats)
        # round price_per_meter to 1 decimal place
        data['price_per_meter'] = data['price_per_meter'].apply(lambda x: round(x, 1))
        sorted_data = data.sort_values(by=['price_per_meter'])
        return sorted_data

    def show_results(self, sorted_data: pd.DataFrame):

        pd.set_option('display.max_columns', 500)
        pd.set_option('display.max_rows', 500)
        pd.set_option('display.width', 2000)
        pd.set_option('display.expand_frame_repr', False)
        pd.set_option('max_colwidth', 800)
        sorted.style.set_properties(**{'text-align': 'left'}).set_table_styles(
            [dict(selector='th', props=[('text-align', 'left')])])
        pd.option_context('display.colheader_justify', 'right')
        print(sorted)

    def save_to_csv(self, sorted_data: pd.DataFrame, path: str):
        sorted_data.to_csv(path)

    def get_old_data(self):
        # Equivalent to 'SELECT *'
        query = db.select([self.flats_table])
        ResultProxy = self.connection.execute(query)
        ResultSet = ResultProxy.fetchall()
        # convert to pandas df
        df = pd.DataFrame(ResultSet)
        df.columns = ResultSet[0].keys()
        print(df.to_string())
        # retrun resulting dataframe
        return df

    # get current data that are not in old data
    def get_only_new_data(self, current_data: pd.DataFrame, old_data: pd.DataFrame):
        common = current_data.merge(old_data, on=['title', 'price_per_meter'])
        only_new_data = current_data[(~current_data.title.isin(common.title)) & (~current_data.price_per_meter.isin(common.price_per_meter))]
        return only_new_data

    def truncate_flats(self):



if __name__ == "__main__":
    # scrape the sites
    scraper = MasterScraper()
    scraper.start_scraping_workflow()
    # get current data from scrapers
    current_data = scraper.get_current_results()
    # get previous data from db table
    old_data = scraper.get_old_data()
    # get only new flats that were not in our db table
    only_new_flats = scraper.get_only_new_data(current_data, old_data)
    # truncate our table and insert only_new_flats



    scraper.show_results(current_data)
scraper.save_to_csv(current_data, scraper.res_file)
