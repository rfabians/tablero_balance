"""
Tabla del Balance Hídrico IWA — estilo WinUI claro con visualización de porcentajes.
Columnas: Vol. Total | nivel1 | nivel2 | nivel3_cra | nivel0
Los rowspan se calculan a partir de los datos reales.
"""
import pandas as pd
from dash import html


# ── Paleta de Colores (Estilo WinUI Claro) ────────────────────────────────────

# Volumen de Entrada al Sistema (Total)
COLOR_VOLUMEN_TOTAL_BG = "#0078D4"    # Azul WinUI
COLOR_VOLUMEN_TOTAL_TEXT = "#FFFFFF"

# Celda Compartida/Neutra (para nivel1 que pertenece a múltiples nivel0)
COLOR_COMPARTIDO_BG = "#EFF6FF"       # Azul muy claro
COLOR_COMPARTIDO_TEXT = "#0063B1"     # Azul medio

# Agua Facturada (Ingreso Positivo - Familia de verdes)
PALETA_AGUA_FACTURADA = {
    "n0": {"bg": "#107C10", "text": "#FFFFFF"},  # Verde WinUI oscuro
    "n1": {"bg": "#F0F9F0", "text": "#1A1D1E"},  # Verde muy claro
    "n2": {"bg": "#D1FAD1", "text": "#1A1D1E"},  # Verde claro
    "n3": {"bg": "#A8E6A8", "text": "#1A1D1E"},  # Verde medio
}

# Agua No Facturada (Pérdida - Familia de naranjas/cálidos)
PALETA_AGUA_NO_FACTURADA = {
    "n0": {"bg": "#D83B01", "text": "#FFFFFF"},  # Naranja WinUI oscuro
    "n1": {"bg": "#FFF8F5", "text": "#1A1D1E"},  # Naranja muy claro
    "n2": {"bg": "#FFE4D0", "text": "#1A1D1E"},  # Naranja claro
    "n3": {"bg": "#FFCBA4", "text": "#1A1D1E"},  # Naranja medio
}


# ── Helpers de Formato y Estructura ──────────────────────────────────────────

def formatear_volumen_iwa(volumen: float) -> str:
    """Formatea un valor de volumen a millones de metros cúbicos (M m³)."""
    return f"{volumen / 1_000_000:,.3f} M m³"


def obtener_paleta_por_categoria(nivel0: str) -> dict:
    """Retorna la paleta de colores según si la categoría es Agua Facturada o No Facturada."""
    if "NO" in str(nivel0).upper():
        return PALETA_AGUA_NO_FACTURADA
    return PALETA_AGUA_FACTURADA


def crear_celda_iwa(
    titulo: str,
    valor: str,
    bg_color: str,
    text_color: str = "#1A1D1E",
    rowspan: int = None,
    colspan: int = None,
    porcentaje: float = None
) -> html.Td:
    """
    Crea una celda de tabla (html.Td) con estilo WinUI claro.
    
    Cada celda actúa como una tarjeta pequeña con:
      - Título/Categoría en texto pequeño y mayúsculas.
      - Valor numérico destacado en negrita.
      - Porcentaje opcional (con respecto al volumen total) debajo del valor.
    """
    estilos = {
        "backgroundColor": bg_color,
        "color": text_color,
        "border": "1px solid #E8EDF2",
        "padding": "8px 10px",
        "textAlign": "center",
        "verticalAlign": "middle",
        "lineHeight": "1.4",
    }
    
    props = {"style": estilos}
    if rowspan and rowspan > 1:
        props["rowSpan"] = rowspan
    if colspan and colspan > 1:
        props["colSpan"] = colspan

    contenido_tarjeta = [
        # Categoría
        html.Div(titulo, style={
            "fontWeight": "600",
            "fontSize": "10px",
            "textTransform": "uppercase",
            "letterSpacing": "0.4px",
            "marginBottom": "3px",
            "opacity": "0.75",
        }),
        # Valor del Volumen
        html.Div(valor, style={
            "fontWeight": "700",
            "fontSize": "12px",
        }),
    ]

    # Porcentaje de volumen con respecto al total
    if porcentaje is not None:
        contenido_tarjeta.append(
            html.Div(f"{porcentaje:.1f}%", style={
                "fontSize": "10px",
                "fontWeight": "600",
                "marginTop": "4px",
                "opacity": "0.85",
            })
        )

    return html.Td(contenido_tarjeta, **props)


# ── Componente Principal ──────────────────────────────────────────────────────

def generar_tabla_iwa(df: pd.DataFrame) -> html.Div:
    """
    Genera la tabla dinámica de balance hídrico IWA utilizando un diseño de 5 columnas:
      Col 1: Volumen de Entrada al Sistema (Total global)
      Col 2: Categorías Nivel 1 (ej. Consumo Autorizado, Pérdidas de Agua)
      Col 3: Categorías Nivel 2 (ej. Consumo Autorizado Facturado, Pérdidas Reales)
      Col 4: Categorías Nivel 3 / Detalle CRA (ej. Consumo Facturado Medido)
      Col 5: Categorías Nivel 0 / Resumen (Agua Facturada, Agua No Facturada)
      
    Agrupa celdas verticalmente usando rowspan según la estructura y relaciones reales de los datos.
    Debajo de cada valor numérico se incluye el porcentaje correspondiente con respecto al volumen total.
    """
    # 1. Validación de entrada
    if df is None or df.empty:
        return html.Div(
            "Sin datos disponibles",
            style={
                "color": "#5E5E5E",
                "textAlign": "center",
                "padding": "20px",
                "fontSize": "13px"
            },
        )

    columnas_requeridas = {"nivel0", "nivel1", "nivel2", "nivel3_cra", "volumen"}
    if not columnas_requeridas.issubset(df.columns):
        return html.Div(
            "Error: Columnas del DataFrame insuficientes para generar la Tabla IWA",
            style={"color": "#C50F1F", "fontSize": "13px"}
        )

    # 2. Filtrado de registros válidos y eliminación de agregados (etiquetados con "M")
    mascara_validos = (
        df["nivel0"].notna() & (df["nivel0"] != "M") &
        df["nivel1"].notna() & (df["nivel1"] != "M") &
        df["nivel2"].notna() & (df["nivel2"] != "M") &
        df["nivel3_cra"].notna() & (df["nivel3_cra"] != "M")
    )
    df_filtrado = df[mascara_validos].copy()

    if df_filtrado.empty:
        return html.Div(
            "Sin datos para mostrar tras filtrar valores nulos/agregados",
            style={
                "color": "#5E5E5E",
                "textAlign": "center",
                "padding": "20px",
                "fontSize": "13px"
            },
        )

    # 3. Agrupación y ordenamiento de los datos
    columnas_agrupamiento = ["nivel0", "nivel1", "nivel2", "nivel3_cra"]
    df_agrupado = (
        df_filtrado.groupby(columnas_agrupamiento, as_index=False)["volumen"]
        .sum()
    )

    # Definir criterio de ordenación para colocar AGUA FACTURADA primero y AGUA NO FACTURADA después
    df_agrupado["_criterio_orden"] = df_agrupado["nivel0"].apply(
        lambda cat: 0 if "NO" not in str(cat).upper() else 1
    )
    df_agrupado = (
        df_agrupado.sort_values(["_criterio_orden", "nivel1", "nivel2", "nivel3_cra"])
        .drop("_criterio_orden", axis=1)
        .reset_index(drop=True)
    )

    # Calcular volumen total y número total de filas resultantes
    volumen_total = df_agrupado["volumen"].sum()
    total_filas = len(df_agrupado)

    # Evitar división por cero en el cálculo de porcentajes
    volumen_referencia = volumen_total if volumen_total > 0 else 1.0

    # 4. Precomputar rowspans (cantidad de filas a agrupar) y volúmenes acumulados
    filas_por_nivel0 = df_agrupado.groupby("nivel0").size().to_dict()
    filas_por_nivel1 = df_agrupado.groupby("nivel1").size().to_dict()
    filas_por_grupo_nivel2 = df_agrupado.groupby(["nivel0", "nivel1", "nivel2"]).size().to_dict()

    volumen_por_nivel0 = df_agrupado.groupby("nivel0")["volumen"].sum().to_dict()
    volumen_por_nivel1 = df_agrupado.groupby("nivel1")["volumen"].sum().to_dict()
    volumen_por_grupo_nivel2 = df_agrupado.groupby(["nivel0", "nivel1", "nivel2"])["volumen"].sum().to_dict()

    # Identificar si un mismo nivel1 se comparte en varios nivel0 (ej. Consumo Autorizado)
    conteo_nivel0_por_nivel1 = df_agrupado.groupby("nivel1")["nivel0"].nunique().to_dict()

    # 5. Construir dinámicamente las filas de la tabla
    nivel0_procesados = set()
    nivel1_procesados = set()
    grupo_nivel2_procesados = set()
    es_primera_fila = True
    filas_tabla = []

    for _, fila in df_agrupado.iterrows():
        nivel0_val = fila["nivel0"]
        nivel1_val = fila["nivel1"]
        nivel2_val = fila["nivel2"]
        nivel3_val = fila["nivel3_cra"]
        volumen_val = fila["volumen"]
        
        paleta = obtener_paleta_por_categoria(nivel0_val)
        celdas = []

        # Columna 1: Volumen Total (se incluye solo en la primera fila de la tabla con rowspan total)
        if es_primera_fila:
            celdas.append(crear_celda_iwa(
                titulo="Volumen de Entrada al Sistema",
                valor=formatear_volumen_iwa(volumen_total),
                bg_color=COLOR_VOLUMEN_TOTAL_BG,
                text_color=COLOR_VOLUMEN_TOTAL_TEXT,
                rowspan=total_filas,
                porcentaje=100.0 if volumen_total > 0 else 0.0
            ))
            es_primera_fila = False

        # Columna 2: Nivel 1 (se agrupa con rowspan)
        if nivel1_val not in nivel1_procesados:
            nivel1_procesados.add(nivel1_val)
            vol_n1 = volumen_por_nivel1[nivel1_val]
            pct_n1 = (vol_n1 / volumen_referencia) * 100
            
            # Si el nivel1 está compartido entre nivel0 (ej: CONSUMO AUTORIZADO), usamos un color neutro
            if conteo_nivel0_por_nivel1.get(nivel1_val, 1) > 1:
                bg, tc = COLOR_COMPARTIDO_BG, COLOR_COMPARTIDO_TEXT
            else:
                bg, tc = paleta["n1"]["bg"], paleta["n1"]["text"]
                
            celdas.append(crear_celda_iwa(
                titulo=str(nivel1_val),
                valor=formatear_volumen_iwa(vol_n1),
                bg_color=bg,
                text_color=tc,
                rowspan=filas_por_nivel1[nivel1_val],
                porcentaje=pct_n1
            ))

        # Columna 3: Nivel 2 (se agrupa con rowspan según la tupla de nivel0, nivel1 y nivel2)
        clave_n2 = (nivel0_val, nivel1_val, nivel2_val)
        if clave_n2 not in grupo_nivel2_procesados:
            grupo_nivel2_procesados.add(clave_n2)
            vol_n2 = volumen_por_grupo_nivel2[clave_n2]
            pct_n2 = (vol_n2 / volumen_referencia) * 100
            
            celdas.append(crear_celda_iwa(
                titulo=str(nivel2_val),
                valor=formatear_volumen_iwa(vol_n2),
                bg_color=paleta["n2"]["bg"],
                text_color=paleta["n2"]["text"],
                rowspan=filas_por_grupo_nivel2[clave_n2],
                porcentaje=pct_n2
            ))

        # Columna 4: Nivel 3 / Detalle (siempre se renderiza ya que es el nivel de mayor granularidad)
        pct_n3 = (volumen_val / volumen_referencia) * 100
        celdas.append(crear_celda_iwa(
            titulo=str(nivel3_val),
            valor=formatear_volumen_iwa(volumen_val),
            bg_color=paleta["n3"]["bg"],
            text_color=paleta["n3"]["text"],
            porcentaje=pct_n3
        ))

        # Columna 5: Nivel 0 / Resumen (se incluye solo en la primera fila de cada grupo nivel0 con rowspan)
        if nivel0_val not in nivel0_procesados:
            nivel0_procesados.add(nivel0_val)
            vol_n0 = volumen_por_nivel0[nivel0_val]
            pct_n0 = (vol_n0 / volumen_referencia) * 100
            
            celdas.append(crear_celda_iwa(
                titulo=str(nivel0_val),
                valor=formatear_volumen_iwa(vol_n0),
                bg_color=paleta["n0"]["bg"],
                text_color=paleta["n0"]["text"],
                rowspan=filas_por_nivel0[nivel0_val],
                porcentaje=pct_n0
            ))

        filas_tabla.append(html.Tr(celdas))

    # 6. Renderizar tabla con estructura de diseño WinUI responsiva
    tabla = html.Table(
        html.Tbody(filas_tabla, style={"height": "100%"}), # <-- Asegura el cuerpo de la tabla
        style={
            "width": "100%",
            "height": "100%",        # <-- CAMBIO: Fuerza a la tabla a usar el alto del Paper
            "borderCollapse": "collapse",
            "tableLayout": "fixed",
            "fontSize": "11px",
            "fontFamily": "'Segoe UI', 'Inter', system-ui, sans-serif",
        },
    )

    return html.Div(
        tabla, 
        style={
            "overflowX": "auto", 
            "width": "100%", 
            "height": "calc(100% - 30px)"  # <-- CAMBIO: Ocupa el alto restante restando el título
        }
    )
