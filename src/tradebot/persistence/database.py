"""Database engine and session setup."""
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session

class Base(DeclarativeBase):
    pass

def create_db_engine(url: str = "sqlite:///tradebot.db"):
    return create_engine(url, echo=False)

def create_session(engine) -> Session:
    return Session(engine)
