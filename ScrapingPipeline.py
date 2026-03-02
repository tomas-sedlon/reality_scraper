from scrapers.bezRealitky import Scraper as bezrealitky
from scrapers.realityIdnes import Scraper as realityIdnes
from scrapers.sreality import Scraper as sReality
from concurrent.futures import ThreadPoolExecutor, as_completed
import pandas as pd
import sqlalchemy as db
from sqlalchemy.orm import sessionmaker
from database.mysql_flat import Flat
from database.models import HouseRecord, LotRecord
import os

# Map property_type key (from config) to internal type string used by scrapers
TYPE_KEY_MAP = {
    'flats': 'flat',
    'houses': 'house',
    'lots': 'lot',
}

# Map property type to DB model class
DB_MODEL_MAP = {
    'flat': Flat,
    'house': HouseRecord,
    'lot': LotRecord,
}

# Map property type to table name
TABLE_NAME_MAP = {
    'flat': 'flats',
    'house': 'houses',
    'lot': 'lots',
}


class ScrapingPipeline:
    def __init__(self, client_config):
        self.cfg = client_config
        self.property_types = client_config.get('property_types', ['flats'])
        self.res_file = self.cfg['res_file']
        self.db_name = self.cfg['db_name']

        # Per-type results storage
        self.all_data = {}  # { 'flat': [...], 'house': [...], ... }

        # Use SQLite - db file stored next to the script
        db_dir = os.path.dirname(os.path.abspath(__file__))
        db_path = os.path.join(db_dir, f"{self.db_name}.db")
        self.engine = db.create_engine(f'sqlite:///{db_path}', echo=False)

        self.connection = self.engine.connect()
        Session = sessionmaker(bind=self.engine)
        self.session = Session()
        self.metadata = db.MetaData()

        # Create tables for each property type
        for pt_key in self.property_types:
            pt = TYPE_KEY_MAP.get(pt_key, pt_key)
            model = DB_MODEL_MAP.get(pt)
            if model:
                model.__table__.create(bind=self.engine, checkfirst=True)

    def _get_type_config(self, property_type_key):
        """Merge top-level config with type-specific sub-dict for backward compat."""
        type_cfg = dict(self.cfg)
        sub = self.cfg.get(property_type_key, {})
        if sub:
            type_cfg.update(sub)
        # Pass location through if present
        if 'location' in self.cfg:
            type_cfg['location'] = self.cfg['location']
        return type_cfg

    def _create_scrapers(self, property_type_key):
        """Instantiate scrapers with correct property_type and type-specific config."""
        pt = TYPE_KEY_MAP.get(property_type_key, property_type_key)
        cfg = self._get_type_config(property_type_key)
        return [
            bezrealitky(cfg, property_type=pt),
            sReality(cfg, property_type=pt),
            realityIdnes(cfg, property_type=pt),
        ]

    def check_existing(self, items, new_item):
        for ex in items:
            if new_item['price_per_meter'] == ex['price_per_meter']:
                return True
        return False

    def start_scraping_workflow(self):
        for pt_key in self.property_types:
            pt = TYPE_KEY_MAP.get(pt_key, pt_key)
            items = []
            scrapers = self._create_scrapers(pt_key)

            with ThreadPoolExecutor(max_workers=3) as pool:
                futures = {pool.submit(scraper.start_workflow): scraper for scraper in scrapers}
                for future in as_completed(futures):
                    scraper = futures[future]
                    try:
                        results = future.result()
                        for item in results:
                            if not self.check_existing(items, item):
                                items.append(item)
                        print(f"  {scraper.__class__.__module__} ({pt}): found {len(results)} items")
                    except Exception as e:
                        print(f"  Error in scraper {scraper.__class__.__module__} ({pt}): {repr(e)}")

            self.all_data[pt] = items

    def get_current_results(self, property_type='flat'):
        items = self.all_data.get(property_type, [])
        table_name = TABLE_NAME_MAP.get(property_type, 'flats')
        model = DB_MODEL_MAP.get(property_type, Flat)

        if not items:
            columns = model.__table__.columns.keys()
            return pd.DataFrame(columns=columns)

        data = pd.DataFrame(items)
        data['price_per_meter'] = data['price_per_meter'].apply(lambda x: round(x, 1))
        sorted_data = data.sort_values(by=['price_per_meter'])

        # Only filter by floor for flats
        if property_type == 'flat' and 'floor' in sorted_data.columns:
            sorted_data = sorted_data[pd.to_numeric(sorted_data['floor'], errors='coerce').notnull()]

        return sorted_data

    def show_results(self, sorted_data: pd.DataFrame, label=''):
        pd.set_option('display.max_columns', 500)
        pd.set_option('display.max_rows', 500)
        pd.set_option('display.width', 2000)
        pd.set_option('display.expand_frame_repr', False)
        pd.set_option('max_colwidth', 800)
        prefix = f" ({label})" if label else ""
        print(f"\n\n Found new items{prefix} that were not found before:\n")
        print(sorted_data)

    def save_to_csv(self, sorted_data: pd.DataFrame, path: str):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        sorted_data.to_csv(path)

    def get_old_data(self, property_type='flat'):
        table_name = TABLE_NAME_MAP.get(property_type, 'flats')
        model = DB_MODEL_MAP.get(property_type, Flat)
        try:
            str_sql = db.text(f"SELECT * FROM {table_name}")
            result_proxy = self.connection.execute(str_sql)
            result_set = result_proxy.fetchall()
            if result_set:
                df = pd.DataFrame(result_set, columns=result_proxy.keys())
            else:
                columns = model.__table__.columns.keys()
                df = pd.DataFrame(columns=columns)
        except Exception as e:
            print(f"Cannot acquire old data from db ({table_name}): {repr(e)}\n Assuming no old data.")
            columns = model.__table__.columns.keys()
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

    def truncate_table(self, property_type='flat'):
        model = DB_MODEL_MAP.get(property_type, Flat)
        self.session.query(model).delete()
        self.session.commit()

    def insert_data(self, data: pd.DataFrame, property_type='flat'):
        if not data.empty:
            table_name = TABLE_NAME_MAP.get(property_type, 'flats')
            data.to_sql(con=self.engine, name=table_name, if_exists='append', index=False)

    # Backward-compatible aliases
    def insert_flats(self, data: pd.DataFrame):
        self.insert_data(data, 'flat')

    def truncate_flats(self):
        self.truncate_table('flat')
