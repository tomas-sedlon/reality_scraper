from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, ForeignKey, Integer, VARCHAR, DECIMAL

Model = declarative_base(name='Model')


class Flat(Model):
    __tablename__ = 'flats'

    title = Column(VARCHAR(300), primary_key=True)
    price = Column(Integer)
    size = Column(Integer)
    meters = Column(Integer)
    price_per_meter = Column(DECIMAL(7, 1), primary_key=True)
    floor = Column(Integer)
    penb = Column(VARCHAR(1))
    state = Column(VARCHAR(50))
    link = Column(VARCHAR(300))