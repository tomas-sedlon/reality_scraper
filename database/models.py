from sqlalchemy.orm import declarative_base
from sqlalchemy import Column, Integer, VARCHAR, DECIMAL

HouseModel = declarative_base(name='HouseModel')
LotModel = declarative_base(name='LotModel')


class HouseRecord(HouseModel):
    __tablename__ = 'houses'

    title = Column(VARCHAR(300))
    price = Column(Integer)
    living_area = Column(Integer)
    lot_size = Column(Integer)
    house_type = Column(VARCHAR(50))
    price_per_meter = Column(DECIMAL(7, 1))
    penb = Column(VARCHAR(50))
    state = Column(VARCHAR(50))
    link = Column(VARCHAR(300), primary_key=True)


class LotRecord(LotModel):
    __tablename__ = 'lots'

    title = Column(VARCHAR(300))
    price = Column(Integer)
    lot_size = Column(Integer)
    price_per_meter = Column(DECIMAL(7, 1))
    water = Column(VARCHAR(50))
    gas = Column(VARCHAR(50))
    electricity = Column(VARCHAR(50))
    sewer = Column(VARCHAR(50))
    link = Column(VARCHAR(300), primary_key=True)
