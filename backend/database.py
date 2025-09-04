from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
import os
from dotenv import load_dotenv

# Load URL_DATABASE from environment
URL_DATABASE = os.getenv("URL_DATABASE")
if not URL_DATABASE:
    load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '.env'))
    URL_DATABASE = os.getenv("URL_DATABASE")
    if not URL_DATABASE:
        raise ValueError("URL_DATABASE not set in environment or .env file")

engine = create_engine(URL_DATABASE)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()