import os

import sqlalchemy
from sqlalchemy import create_engine
from dotenv import load_dotenv

def init_db() -> sqlalchemy.engine.base.Engine | None:
    try:
        load_dotenv()
        database_url = os.getenv("DATABASE_URL")
        engine = create_engine(database_url)
        return engine
    except Exception as e:
        print(e)
        return None