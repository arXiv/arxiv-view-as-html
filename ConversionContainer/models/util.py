"""Helpers and Flask application integration."""

from contextlib import contextmanager

from typing import Generator, List, Any
from datetime import datetime
from pytz import timezone, UTC

from flask import Flask
from sqlalchemy import text
from sqlalchemy.orm.session import Session

from arxiv.base import logging
from arxiv.base.globals import get_application_config

from db import db

EASTERN = timezone('US/Eastern')
logger = logging.getLogger(__name__)
logger.propagate = False

def now() -> int:
    """Get the current epoch/unix time."""
    return epoch(datetime.now(tz=UTC))


def epoch(t: datetime) -> int:
    """Convert a :class:`.datetime` to UNIX time."""
    delta = t - datetime.fromtimestamp(0, tz=EASTERN)
    return int(round((delta).total_seconds()))


def from_epoch(t: int) -> datetime:
    """Get a :class:`datetime` from an UNIX timestamp."""
    return datetime.fromtimestamp(t, tz=EASTERN)


@contextmanager
def transaction() -> Generator:
    """Context manager for database transaction."""
    try:
        yield db.session
        # The caller may have explicitly committed already, in order to
        # implement exception handling logic. We only want to commit here if
        # there is anything remaining that is not flushed.
        if db.session.new or db.session.dirty or db.session.deleted:
            db.session.commit()
    except Exception as e:
        logger.warning('Commit failed, rolling back: %s', str(e))
        db.session.rollback()
        raise


def init_app(app: Flask) -> None:
    """Set configuration defaults and attach session to the application."""
    db.init_app(app)


def current_session() -> Session:
    """Get/create database session for this context."""
    return db.session


def create_all() -> None:
    """Create all tables in the database."""
    db.create_all()

def drop_all() -> None:
    """Drop all tables in the database."""
    db.drop_all()