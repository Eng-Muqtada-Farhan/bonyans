import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "")


def get_engine():
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL is not set in .env")
    return create_engine(DATABASE_URL, pool_pre_ping=True)


def get_session_factory():
    return sessionmaker(bind=get_engine(), autocommit=False, autoflush=False)


def test_connection() -> bool:
    """التحقق من الاتصال بـ PostgreSQL — لا يُستدعى من main.py."""
    try:
        engine = get_engine()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("PostgreSQL connection: OK")
        return True
    except Exception as e:
        print(f"PostgreSQL connection FAILED: {e}")
        return False


if __name__ == "__main__":
    test_connection()
