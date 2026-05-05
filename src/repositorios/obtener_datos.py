import os
from pathlib import Path
from typing import Any

from pandas import DataFrame
from src.infraestructure.database import init_db
from src.models.FiltrosTablero import FiltroTablero

import pandas as pd
import geopandas as gpd
from dotenv import load_dotenv

load_dotenv()

_BASE_DIR = Path(__file__).resolve().parent


def obtener_datos(filtro: FiltroTablero) -> tuple[DataFrame, Any] | tuple[None, None]:
    """
    Carga el DataFrame de balance y el GeoDataFrame de sectores.
    La ruta del GeoJSON se resuelve desde la variable de entorno SECTORES_GEOJSON
    relativa a este archivo, con fallback a la ruta de assets del proyecto.
    """
    engine = init_db()
    if engine is None:
        return None, None

    df = pd.read_sql_table("balance_tablero", engine)

    geojson_env = os.getenv("SECTORES_GEOJSON")
    if geojson_env:
        ruta_geojson = (_BASE_DIR / geojson_env).resolve()
    else:
        # Fallback: assets junto al paquete src
        ruta_geojson = (_BASE_DIR.parent / "assets" / "Sectores.geojson").resolve()

    gdf = gpd.read_file(ruta_geojson)[["name", "geometry"]]
    return df, gdf