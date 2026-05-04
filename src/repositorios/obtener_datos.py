import os
from pathlib import Path
from typing import Any, Iterator

from pandas import DataFrame

from src.infraestructure.database import init_db
from src.models.FiltrosTablero import FiltroTablero

import pandas as pd
import geopandas as gpd
from dotenv import load_dotenv


def obtener_datos(filtro: FiltroTablero) -> tuple[DataFrame | Iterator[DataFrame], Any] | tuple[None, None]:
    engine = init_db()
    load_dotenv()
    BASE_DIR = Path(__file__).resolve().parent
    geojson_sectores_path = os.getenv("SECTORES_GEOJSON")
    ruta_geojson = (BASE_DIR / geojson_sectores_path).resolve()
    print(f"Ruta dinámica generada: {ruta_geojson}")
    if engine:
        df = pd.read_sql_table('balance_tablero', engine)
        gdf = gpd.read_file(r'C:\dev\TableroBalance\src\assets\Sectores.geojson')
        gdf = gdf[['name', 'geometry']]
        return df, gdf
    else:
        print("No se pudo establecer conexión con el motor de base de datos.")
        return None, None


