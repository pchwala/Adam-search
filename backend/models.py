from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, BigInteger
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base


class Adam(Base):
    __tablename__ = 'Adam'
    
    id = Column(BigInteger, primary_key=True, index=True)
    created_at = Column(DateTime, default=func.now())
    realizowane = Column(String, nullable=True)
    oczekuje = Column(String, nullable=True)
    combined = Column(String, nullable=True)
    nie_dodane = Column(String, nullable=True)
    wykonane = Column(String, nullable=True)
