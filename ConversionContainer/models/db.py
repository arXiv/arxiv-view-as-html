"""ORM models for latexml table"""

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Column, Enum, \
    ForeignKey, Integer, SmallInteger, \
    String, Text, DateTime
from sqlalchemy.orm import relationship

db: SQLAlchemy = SQLAlchemy()

class DBLaTeXML(db.Model):
    """ LaTeXML metadata table """

    __tablename__ = 'arXiv_latexml'

    document_id = Column(Integer, primary_key=True)
    document_version = Column(Integer, primary_key=True)
    # conversion_status codes: 
    #   - 0 = in progress
    #   - 1 = success
    #   - 2 = failure
    conversion_status = Column(Integer, nullable=False)
    latexml_version = Column(String(40), nullable=False)
    tex_checksum = Column(String)
    conversion_start_time = Column(DateTime)
    conversion_end_time = Column(DateTime)
