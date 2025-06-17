from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()

class ResponseHistory(Base):
    __tablename__ = "response_history"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, nullable=False, index=True)
    vacancy_id = Column(String, nullable=False)
    vacancy_title = Column(String, nullable=False)
    cover_letter = Column(Text, nullable=False)
    match_score = Column(Integer, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    sent_at = Column(DateTime, nullable=True)