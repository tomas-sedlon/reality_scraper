import sqlalchemy as db
import pandas as pd
from sqlalchemy.orm import sessionmaker

from database.mysql_flat import Flat, Model

# Define the MySQL engine using MySQL Connector/Python
engine = db.create_engine(
    'mysql+mysqlconnector://root:root@localhost:3306/reality',
    echo=True
)

connection = engine.connect()
metadata = db.MetaData()
flats_table = db.Table('flats', metadata, autoload=True, autoload_with=engine)
# create a configured "Session" class
Session = sessionmaker(bind=engine)
# create a Session
session = Session()

# Print the column names
print(flats_table.columns.keys())
# Print full table metadata
print(repr(metadata.tables['flats']))

# Equivalent to 'SELECT *'
query = db.select([flats_table])
ResultProxy = connection.execute(query)
ResultSet = ResultProxy.fetchall()

# truncate
session.query(Flat).delete()

# insert
session.add(Flat(title='test', price_per_meter=3.6))
session.commit()

session.close()

# convert to pandas df
df = pd.DataFrame(ResultSet)
df.columns = ResultSet[0].keys()
print(df.to_string())


