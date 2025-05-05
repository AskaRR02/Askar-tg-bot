from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Float
from sqlalchemy.sql import func

from database import Base


class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True)
    username = Column(String, nullable=True)
    registered_at = Column(DateTime, default=func.now())


class Session(Base):
    __tablename__ = "sessions"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    current_question = Column(Integer, default=0)
    current_theme = Column(String, nullable=True)
    score = Column(Integer, default=0)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


class TestResult(Base):
    __tablename__ = "test_results"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    theme = Column(String)
    score = Column(Float)
    date = Column(DateTime, default=func.now())


class PhishingLog(Base):
    __tablename__ = "phishing_logs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    clicked = Column(Boolean, default=False)
    date = Column(DateTime, default=func.now()) 