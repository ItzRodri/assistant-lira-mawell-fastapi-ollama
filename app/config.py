import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv

load_dotenv()

# Use SQLite as default database (works great for this use case)
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./mawell_assistant.db")

# Ensure we're using SQLite (convert any postgres URLs to sqlite if needed)
if not DATABASE_URL.startswith("sqlite"):
    print("⚠️  Converting to SQLite database for better Railway compatibility")
    DATABASE_URL = "sqlite:///./mawell_assistant.db"

# SQLite configuration optimized for production
engine = create_engine(
    DATABASE_URL, 
    connect_args={
        "check_same_thread": False,
        "timeout": 20
    },
    pool_pre_ping=True,
    echo=False  # Set to True for debugging
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()
