from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from config.environment import DATABASE_URL

# Connect FastAPI with SQLAlchemy
engine = create_engine(
    DATABASE_URL#type:ignore
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine,pool_pre_ping=True)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()