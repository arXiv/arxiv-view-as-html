"""Helpers and Flask application integration."""
from contextlib import contextmanager

from typing import Generator, Callable
from datetime import datetime
from pytz import timezone, UTC
import logging
import time
from functools import wraps

from flask import Flask
from sqlalchemy import text
from sqlalchemy.orm.session import Session

from .db import db
from ..exceptions import DBConnectionError

logger = logging.getLogger(__name__)

def now() -> int:
    """Get the current epoch/unix time."""
    return epoch(datetime.now(tz=UTC))


def epoch(t: datetime) -> int:
    """Convert a :class:`.datetime` to UNIX time."""
    delta = t - datetime.fromtimestamp(0, tz=UTC)
    return int(round((delta).total_seconds()))


def from_epoch(t: int) -> datetime:
    """Get a :class:`datetime` from an UNIX timestamp."""
    return datetime.fromtimestamp(t, tz=UTC)


@contextmanager
def transaction() -> Generator[Session, None, None]:
    """Context manager for database transaction."""
    try:
        yield db.session
        # The caller may have explicitly committed already, in order to
        # implement exception handling logic. We only want to commit here if
        # there is anything remaining that is not flushed.
        if db.session.new or db.session.dirty or db.session.deleted:
            db.session.commit()
    except Exception as e:
        logger.warn(f'Commit failed, rolling back', exc_info=1)
        db.session.rollback()
        raise DBConnectionError from e


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


def database_retry (retries: int):

    def decorator (func: Callable) -> Callable:

        @wraps(func)
        def wrapped (*args, **kwargs):
            for i in range(retries):
                try:
                    return func(*args, **kwargs)
                except DBConnectionError:
                    time.sleep(3)
            raise DBConnectionError
        
        return wrapped
    
    return decorator
