import os
from sqlalchemy import create_engine
from sqlalchemy.engine import URL
from dotenv import load_dotenv

def init_db():
    try:
        load_dotenv()
        
        # Construimos la URL usando los componentes individuales
        connection_url = URL.create(
            drivername="postgresql+psycopg2",
            username=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),  # SQLAlchemy escapará el @@ automáticamente
            host=os.getenv("DB_HOST"),
            port=int(os.getenv("DB_PORT")),
            database=os.getenv("DB_NAME")
        )
        
        engine = create_engine(connection_url)
        return engine
    except Exception as e:
        print(f"Error conectando a la base de datos: {e}")
        return None