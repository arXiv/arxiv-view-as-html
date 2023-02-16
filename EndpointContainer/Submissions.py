from typing import Optional, List

from sqlalchemy.dialects.mysql import BIGINT, CHAR, DECIMAL, INTEGER, MEDIUMINT, MEDIUMTEXT, SMALLINT, TINYINT, VARCHAR
from sqlalchemy import BINARY, CHAR, Column, Date, DateTime, Enum, ForeignKey, ForeignKeyConstraint, Index, String, TIMESTAMP, Table, Text, text
from sqlalchemy.orm import relationship

from arxiv_auth.legacy.models import db


class Submissions(db.Model):
    __tablename__ = 'arXiv_submissions'

    submission_id = Column(INTEGER(11), primary_key=True)
    document_id = Column(ForeignKey('arXiv_documents.document_id', ondelete='CASCADE', onupdate='CASCADE'), index=True)
    doc_paper_id = Column(VARCHAR(20), index=True)
    sword_id = Column(ForeignKey('arXiv_tracking.sword_id'), index=True)
    userinfo = Column(TINYINT(4), server_default=text("'0'"))
    is_author = Column(TINYINT(1), nullable=False, server_default=text("'0'"))
    agree_policy = Column(TINYINT(1), server_default=text("'0'"))
    viewed = Column(TINYINT(1), server_default=text("'0'"))
    stage = Column(INTEGER(11), server_default=text("'0'"))
    submitter_id = Column(ForeignKey('tapir_users.user_id', ondelete='CASCADE', onupdate='CASCADE'), index=True)
    submitter_name = Column(String(64))
    submitter_email = Column(String(64))
    created = Column(DateTime)
    updated = Column(DateTime)
    status = Column(INTEGER(11), nullable=False, index=True, server_default=text("'0'"))
    sticky_status = Column(INTEGER(11))
    must_process = Column(TINYINT(1), server_default=text("'1'"))
    submit_time = Column(DateTime)
    release_time = Column(DateTime)
    source_size = Column(INTEGER(11), server_default=text("'0'"))
    source_format = Column(VARCHAR(12))
    source_flags = Column(VARCHAR(12))
    has_pilot_data = Column(TINYINT(1))
    is_withdrawn = Column(TINYINT(1), nullable=False, server_default=text("'0'"))
    title = Column(Text)
    authors = Column(Text)
    comments = Column(Text)
    proxy = Column(VARCHAR(255))
    report_num = Column(Text)
    msc_class = Column(String(255))
    acm_class = Column(String(255))
    journal_ref = Column(Text)
    doi = Column(String(255))
    abstract = Column(Text)
    license = Column(ForeignKey('arXiv_licenses.name', onupdate='CASCADE'), index=True)
    version = Column(INTEGER(4), nullable=False, server_default=text("'1'"))
    type = Column(CHAR(8), index=True)
    is_ok = Column(TINYINT(1), index=True)
    admin_ok = Column(TINYINT(1))
    allow_tex_produced = Column(TINYINT(1), server_default=text("'0'"))
    is_oversize = Column(TINYINT(1), server_default=text("'0'"))
    remote_addr = Column(VARCHAR(16), nullable=False, server_default=text("''"))
    remote_host = Column(VARCHAR(255), nullable=False, server_default=text("''"))
    package = Column(VARCHAR(255), nullable=False, server_default=text("''"))
    rt_ticket_id = Column(INTEGER(8), index=True)
    auto_hold = Column(TINYINT(1), server_default=text("'0'"))
    is_locked = Column(INTEGER(1), nullable=False, index=True, server_default=text("'0'"))

    document = relationship('Documents')
    arXiv_licenses = relationship('Licenses')
    submitter = relationship('TapirUsers')
    sword = relationship('Tracking')
    submission_category = relationship('SubmissionCategory', viewonly=True)
    abs_classifier_data = relationship('SubmissionAbsClassifierData', viewonly=True)
    proposals = relationship('SubmissionCategoryProposal', viewonly=True)
    hold_reasons = relationship('SubmissionHoldReason', viewonly=True)
    flags = relationship('SubmissionFlag', viewonly=True)
    admin_log = relationship('AdminLog',
                             primaryjoin='AdminLog.submission_id == Submissions.submission_id',
                             foreign_keys='AdminLog.submission_id',
                             collection_class=list)

    @property
    def primary_classification(self) -> Optional[str]:
        """Get the primary classification for this submission."""
        categories = [
            db_cat for db_cat in self.submission_category if db_cat.is_primary == 1
        ]
        try:
            cat = categories[0].category
        except Exception:
            return None
        return cat

    @property
    def secondary_categories(self) -> List[str]:
        """Category names from this submission's secondary classifications.
        Returns published and unpublished secondaries."""
        return [c.category for c in self.submission_category
                if c.is_primary == 0]

    @property
    def categories(self) -> List[str]:
        """All the categories"""
        return [cr.category for cr in self.submission_category]

    @property
    def new_crosses(self) -> List[str]:
        """For type 'new' these will be redundant with secondary_categories"""
        return [c.category for c in self.submission_category
                if c.is_primary == 0 and c.is_published != 1]

    @property
    def hold_reason(self) -> Optional['SubmissionHoldReason']:
        if self.hold_reasons:
            return self.hold_reasons[0]
        else:
            return None

    @property
    def fudged_categories(self) -> str:

        # This is a close port of the legacy code
        # Needs to be same as arXiv::Schema::ResultSet::DocCategory.string
        primary_str = self.primary_classification if self.primary_classification else '-'
        secondary_list = list(set([cat for cat in self.secondary_categories]))
        cats_to_add = [CATEGORY_ALIASES_INV[cat] for cat in secondary_list
                       if cat in CATEGORY_ALIASES_INV]
        fudged = [primary_str] + sorted(secondary_list + cats_to_add)
        return ' '.join(fudged)
