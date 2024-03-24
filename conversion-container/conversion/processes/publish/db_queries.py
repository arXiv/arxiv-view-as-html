from typing import Optional
from datetime import datetime
from contextlib import contextmanager
import logging

from flask import current_app

from sqlalchemy.orm import Session
from sqlalchemy.sql import text, select

from arxiv.db import session, transaction
from arxiv.db.models import DBLaTeXMLDocuments, \
    DBLaTeXMLSubmissions

logger = logging.getLogger()

