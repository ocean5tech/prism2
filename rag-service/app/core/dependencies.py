from functools import lru_cache
from sqlalchemy.orm import Session
from .database import SessionLocal
from .config import Settings


@lru_cache()
def get_settings():
    return Settings()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()