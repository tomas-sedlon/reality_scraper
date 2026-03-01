from sqlalchemy.orm import declarative_base
from sqlalchemy import Column, Integer, VARCHAR, DECIMAL

Model = declarative_base(name='Model')


class Flat(Model):
    __tablename__ = 'flats'

    title = Column(VARCHAR(300))
    price = Column(Integer)
    rooms = Column(VARCHAR(10))
    size = Column(Integer)
    meters = Column(Integer)
    price_per_meter = Column(DECIMAL(7, 1))
    floor = Column(Integer)
    penb = Column(VARCHAR(50))
    state = Column(VARCHAR(50))
    link = Column(VARCHAR(300), primary_key=True)
