from scrapers.bezRealitky import Scraper as bezrealitky
from scrapers.realityIdnes import Scraper as realityIdnes
from scrapers.centrumReality import Scraper as centrumReality
from scrapers.sreality import Scraper as sReality
from scrapers.bydlisnamiScraper import Scraper as bydlisnami
import pandas as pd
import sqlalchemy as db
from sqlalchemy.orm import sessionmaker
from sqlalchemy_utils import database_exists, create_database
from database.mysql_flat import Flat


class ScrapingPipeline:
    def __init__(self, client_config):
        self.cfg = client_config
        self.all_flats = []
        # TODO add bydlisnami(self.cfg)
        self.scrapers = [centrumReality(self.cfg), sReality(self.cfg), realityIdnes(self.cfg), bezrealitky(self.cfg)]
        self.res_file = self.cfg['res_file']
        self.db_name = self.cfg['db_name']
        # Define the MySQL engine using MySQL Connector/Python
        # change the user and pass if you ever want to use this as anything more than a home fun project
        self.engine = db.create_engine(
            f'mysql+mysqlconnector://root:root@localhost:3306/{self.db_name}',
            echo=True
        )
        if not database_exists(self.engine.url):
            create_database(self.engine.url)
        self.connection = self.engine.connect()
        # create a configured "Session" class
        Session = sessionmaker(bind=self.engine)
        # create a Session
        self.session = Session()
        # get metadata
        self.metadata = db.MetaData()
        self.metadata.bind = self.engine
        # create flat table
        self.metadata.create_all(self.engine, tables=[Flat.__table__])
        # get the flat tab;e
        self.flats_table = db.Table('flats', self.metadata)

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
        # filter the 'floor' data to only contain integers
        filtered_data = sorted_data[pd.to_numeric(sorted_data['floor'], errors='coerce').notnull()]
        return filtered_data

    def show_results(self, sorted_data: pd.DataFrame):

        pd.set_option('display.max_columns', 500)
        pd.set_option('display.max_rows', 500)
        pd.set_option('display.width', 2000)
        pd.set_option('display.expand_frame_repr', False)
        pd.set_option('max_colwidth', 800)
        sorted_data.style.set_properties(**{'text-align': 'left'}).set_table_styles(
            [dict(selector='th', props=[('text-align', 'left')])])
        pd.option_context('display.colheader_justify', 'right')
        print(f"\n\n\n\n Found new flats that were not found before:\n")
        print(sorted_data)

    def save_to_csv(self, sorted_data: pd.DataFrame, path: str):
        sorted_data.to_csv(path)

    def get_old_data(self):
        # Equivalent to 'SELECT *'
        try:
            str_sql = db.text(f"SELECT * FROM {self.db_name}.flats")
            result_proxy = self.connection.execute(str_sql)
            result_set = result_proxy.fetchall()
            # convert to pandas df
            df = pd.DataFrame(result_set)
            df.columns = result_set[0].keys()
        except Exception as e:
            print(f"Cannot acquire old data from db because of error: \n {repr(e)} "
                  f"\n Assuming no old data are present in db")
            columns = Flat.__table__.columns.keys()
            df = pd.DataFrame(columns=columns)

        # return resulting dataframe
        return df

    # get current data that are not in old data
    def get_only_new_data(self, current_data: pd.DataFrame, old_data: pd.DataFrame):
        common = current_data.merge(old_data, on=['link'])
        only_new_data = current_data[(~current_data.link.isin(common.link))]
        return only_new_data

    def truncate_flats(self):
        self.session.query(Flat).delete()
        self.session.commit()

    def insert_flats(self, data: pd.DataFrame):
        data.to_sql(con=self.engine, name='flats', if_exists='append', index=False)
