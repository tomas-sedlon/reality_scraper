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
# create a configured "Session" class
Session = sessionmaker(bind=engine)
# create a Session
session = Session()
print('\n\n\n aaaa')
#flats_table = db.Table('flats', metadata, autoload=True, autoload_with=engine)
#Flat.__table__.create(engine)
#if engine.dialect.has_table(engine, 'flats'):
#    session.query(Flat).delete()
#    session.commit()

metadata = db.MetaData()
metadata.bind = engine
metadata.create_all(engine, tables=[Flat.__table__])
flats_table = db.Table('flats', metadata)



print("tables in metadata")
for t in metadata.sorted_tables:
    print(t.name)
print('\n\n\n made metadata')



# Print the column names
print(flats_table.columns.keys())
# Print full table metadata
print(repr(metadata.tables['flats']))
print('\n\n\n shown flats')


# insert
#session.add(Flat(title='test', price_per_meter=3.6))
#session.commit()
#print('\n\n\n inserted flats')



# Equivalent to 'SELECT *'
#query = db.select([flats_table])
#query = flats_table.select()
str_sql = db.text("SELECT * FROM reality.flats")

ResultProxy = connection.execute(str_sql)
ResultSet = ResultProxy.fetchall()

print('\n\n\n selected flats')


# convert to pandas df
df = pd.DataFrame(ResultSet)
#df.columns = ResultSet[0].keys()
print(df.to_string())

# truncate
#session.query(Flat).delete()
#session.commit()

print('\n\n\n truncated flats')

# insert the whole dataframe
df.to_sql(con=engine, name='flats', if_exists='append', index=False)
#connection.bulk_insert('flats', (df.to_records(index=False).tolist()))
session.commit()
session.close()




# convert to pandas df
df = pd.DataFrame(ResultSet)
#df.columns = ResultSet[0].keys()
print(df.to_string())


