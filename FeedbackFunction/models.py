import os

from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

base = declarative_base()

class DBFeedback (base):
    __tablename__ = 'feedback'

    id = Column(String, primary_key=True)
    canonical_url = Column(String)
    conversion_url = Column(String)
    report_time = Column(Integer)
    browser_info = Column(String)
    location_low = Column(String)
    location_high = Column(String)
    description = Column(String)


engine = create_engine(os.environ['LATEXML_DB_URI'])
session = sessionmaker(bind=engine)
base.metadata.create_all(engine)

def add_feedback (id: str, canonical_url: str, conversion_url: str,
                  report_time: str, browser_info: str, location_low: str,
                  location_high: str, description: str):
    s = session()
    s.add(DBFeedback(
        id=id,
        canonical_url=canonical_url,
        conversion_url=conversion_url,
        report_time=report_time,
        browser_info=browser_info,
        location_low=location_low,
        location_high=location_high,
        description=description
    ))
    s.commit()
