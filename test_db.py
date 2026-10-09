#####  THIS FILE IS FOR CHECKING CONNECTION WITH NEON POSTGRES DATABASE
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL is missing from .env")

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
)

try:
    with engine.connect() as connection:
        result = connection.execute(
            text("SELECT version(), current_database(), current_user")
        )
        version, database, user = result.fetchone()

        print("Neon PostgreSQL connection successful!")
        print(f"Database: {database}")
        print(f"User: {user}")
        print(f"PostgreSQL version: {version}")

except Exception as e:
    print(f"Database connection failed: {e}")

finally:
    engine.dispose()
