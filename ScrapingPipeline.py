from scrapers.bezRealitky import Scraper as bezrealitky
from scrapers.realityIdnes import Scraper as realityIdnes
from scrapers.sreality import Scraper as sReality
import pandas as pd
import sqlalchemy as db
from sqlalchemy.orm import sessionmaker
from database.mysql_flat import Flat
import os


class ScrapingPipeline:
    def __init__(self, client_config):
        self.cfg = client_config
        self.all_flats = []
        self.scrapers = [bezrealitky(self.cfg), sReality(self.cfg), realityIdnes(self.cfg)]
        self.res_file = self.cfg['res_file']
        self.db_name = self.cfg['db_name']

        # Use SQLite - db file stored next to the script
        db_dir = os.path.dirname(os.path.abspath(__file__))
        db_path = os.path.join(db_dir, f"{self.db_name}.db")
        self.engine = db.create_engine(f'sqlite:///{db_path}', echo=False)

        self.connection = self.engine.connect()
        Session = sessionmaker(bind=self.engine)
        self.session = Session()
        self.metadata = db.MetaData()
        # Create the flats table if it doesn't exist
        Flat.__table__.create(bind=self.engine, checkfirst=True)
        self.flats_table = db.Table('flats', self.metadata, autoload_with=self.engine)

    def check_existing(self, flat):
        for ex_flat in self.all_flats:
            if flat['price_per_meter'] == ex_flat['price_per_meter']:
                return True
        return False

    def start_scraping_workflow(self):
        for scraper in self.scrapers:
            try:
                flats = scraper.start_workflow()
                for flat in flats:
                    if not self.check_existing(flat):
                        self.all_flats.append(flat)
                print(f"  {scraper.__class__.__module__}: found {len(flats)} flats")
            except Exception as e:
                print(f"  Error in scraper {scraper.__class__.__module__}: {repr(e)}")

    def get_current_results(self):
        if not self.all_flats:
            columns = Flat.__table__.columns.keys()
            return pd.DataFrame(columns=columns)
        data = pd.DataFrame(self.all_flats)
        data['price_per_meter'] = data['price_per_meter'].apply(lambda x: round(x, 1))
        sorted_data = data.sort_values(by=['price_per_meter'])
        filtered_data = sorted_data[pd.to_numeric(sorted_data['floor'], errors='coerce').notnull()]
        return filtered_data

    def show_results(self, sorted_data: pd.DataFrame):
        pd.set_option('display.max_columns', 500)
        pd.set_option('display.max_rows', 500)
        pd.set_option('display.width', 2000)
        pd.set_option('display.expand_frame_repr', False)
        pd.set_option('max_colwidth', 800)
        print(f"\n\n Found new flats that were not found before:\n")
        print(sorted_data)

    def save_to_csv(self, sorted_data: pd.DataFrame, path: str):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        sorted_data.to_csv(path)

    def get_old_data(self):
        try:
            str_sql = db.text("SELECT * FROM flats")
            result_proxy = self.connection.execute(str_sql)
            result_set = result_proxy.fetchall()
            if result_set:
                df = pd.DataFrame(result_set, columns=result_proxy.keys())
            else:
                columns = Flat.__table__.columns.keys()
                df = pd.DataFrame(columns=columns)
        except Exception as e:
            print(f"Cannot acquire old data from db: {repr(e)}\n Assuming no old data.")
            columns = Flat.__table__.columns.keys()
            df = pd.DataFrame(columns=columns)
        return df

    def get_only_new_data(self, current_data: pd.DataFrame, old_data: pd.DataFrame):
        if current_data.empty:
            return current_data
        if old_data.empty:
            return current_data
        common = current_data.merge(old_data, on=['link'])
        only_new_data = current_data[(~current_data.link.isin(common.link))]
        return only_new_data

    def truncate_flats(self):
        self.session.query(Flat).delete()
        self.session.commit()

    def insert_flats(self, data: pd.DataFrame):
        if not data.empty:
            data.to_sql(con=self.engine, name='flats', if_exists='append', index=False)
