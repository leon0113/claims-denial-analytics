import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

def get_engine():
    url = os.getenv("DATABASE_URL")

    if not url:
        raise RuntimeError("No database url in env file!")
    return create_engine(url)


if __name__ == "__main__":
    engine = get_engine()

    with engine.connect() as conn:
        v = conn.execute(text("SELECT version()")).scalar()
        print("db connected!")
        print(v)