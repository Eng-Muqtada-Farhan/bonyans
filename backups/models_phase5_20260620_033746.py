from sqlalchemy import Column, Integer, Float, Text
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class Company(Base):
    __tablename__ = "companies"

    id         = Column(Integer, primary_key=True, autoincrement=True)
    name       = Column(Text)
    city       = Column(Text)
    phone      = Column(Text)
    spec       = Column(Text)
    desc       = Column(Text)
    email      = Column(Text)
    website    = Column(Text)
    map_link   = Column(Text)
    rating     = Column(Float, default=5.0)
    verified   = Column(Integer, default=0)
    status     = Column(Text, default="pending")
    created_at = Column(Text)
