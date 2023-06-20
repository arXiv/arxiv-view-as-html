from arxiv_auth.legacy.models import db
from sqlalchemy import (
    Column,
    Integer,
    String,
)

class DBLaTeXMLSubmissions(db.Model):
    __bind_key__ = 'latexml'
    __tablename__ = 'arXiv_latexml_sub'

    submission_id = Column(Integer, primary_key=True)
    # conversion_status codes: 
    #   - 0 = in progress
    #   - 1 = success
    #   - 2 = failure
    conversion_status = Column(Integer, nullable=False)
    latexml_version = Column(String(40), nullable=False)
    tex_checksum = Column(String)
    conversion_start_time = Column(Integer)
    conversion_end_time = Column(Integer)
