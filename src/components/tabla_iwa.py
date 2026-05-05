"""
Tabla del Balance Hídrico IWA — estilo WinUI claro.
Columnas: Vol. Total | nivel1 | nivel2 | nivel3_cra | nivel0
Los rowspan se calculan a partir de los datos reales.
"""
import pandas as pd
from dash import html


# ── Paleta WinUI claro ────────────────────────────────────────────────────────

# Encabezado total
_VOL_HDR_BG   = "#0078D4"   # Azul WinUI — fondo cabecera Vol. Total
_VOL_HDR_TXT  = "#FFFFFF"   # Texto blanco

# Agua Facturada → familia azul-verdosa (ingreso positivo)
_AF_N1_BG    = "#F0F9F0"    # nivel1 — muy claro verde
_AF_N1_TXT   = "#1A1D1E"
_AF_N2_BG    = "#D1FAD1"    # nivel2 — claro verde
_AF_N2_TXT   = "#1A1D1E"
_AF_N3_BG    = "#A8E6A8"    # nivel3 — verde medio
_AF_N3_TXT   = "#1A1D1E"
_AF_N0_BG    = "#107C10"    # nivel0 resumen — Verde WinUI
_AF_N0_TXT   = "#FFFFFF"

# Agua No Facturada → familia naranja-cálida (pérdida)
_ANF_N1_BG   = "#FFF8F5"    # nivel1 — muy claro naranja
_ANF_N1_TXT  = "#1A1D1E"
_ANF_N2_BG   = "#FFE4D0"    # nivel2 — claro naranja
_ANF_N2_TXT  = "#1A1D1E"
_ANF_N3_BG   = "#FFCBA4"    # nivel3 — naranja medio
_ANF_N3_TXT  = "#1A1D1E"
_ANF_N0_BG   = "#D83B01"    # nivel0 resumen — Naranja WinUI
_ANF_N0_TXT  = "#FFFFFF"


# ── Helpers ──────────────────────────────────────────────────────────────────

def _fmt(v: float) -> str:
    if v >= 1_000_000:
        return f"{v / 1_000_000:,.2f} M m³"
    if v >= 1_000:
        return f"{v / 1_000:,.1f} k m³"
    return f"{v:,.0f} m³"


def _td(titulo: str, valor: str, bg: str, text_color: str = "#1A1D1E",
        rowspan: int = None, colspan: int = None) -> html.Td:
    """Celda con etiqueta superior pequeña y valor destacado — estilo WinUI claro."""
    props: dict = {
        "style": {
            "backgroundColor": bg,
            "color": text_color,
            "border": "1px solid #E8EDF2",
            "padding": "6px 8px",
            "textAlign": "center",
            "verticalAlign": "middle",
            "lineHeight": "1.4",
        }
    }
    if rowspan and rowspan > 1:
        props["rowSpan"] = rowspan
    if colspan and colspan > 1:
        props["colSpan"] = colspan

    return html.Td(
        [
            html.Div(titulo, style={
                "fontWeight": "600",
                "fontSize": "10px",
                "textTransform": "uppercase",
                "letterSpacing": "0.4px",
                "marginBottom": "3px",
                "opacity": "0.75",
            }),
            html.Div(valor, style={
                "fontWeight": "700",
                "fontSize": "12px",
            }),
        ],
        **props,
    )


# ── Paleta por nivel0 ─────────────────────────────────────────────────────────

def _palette(nivel0: str) -> dict:
    """Devuelve tuplas (bg, text_color) para cada columna según el nivel0."""
    if "NO" in str(nivel0).upper():
        return {
            "n0": (_ANF_N0_BG,  _ANF_N0_TXT),
            "n1": (_ANF_N1_BG,  _ANF_N1_TXT),
            "n2": (_ANF_N2_BG,  _ANF_N2_TXT),
            "n3": (_ANF_N3_BG,  _ANF_N3_TXT),
        }
    return {
        "n0": (_AF_N0_BG,  _AF_N0_TXT),
        "n1": (_AF_N1_BG,  _AF_N1_TXT),
        "n2": (_AF_N2_BG,  _AF_N2_TXT),
        "n3": (_AF_N3_BG,  _AF_N3_TXT),
    }


# ── Generador del componente ──────────────────────────────────────────────────

def generar_tabla_iwa(df: pd.DataFrame) -> html.Div:
    """
    Tabla IWA dinámica con 5 columnas:
      Col 1 — Volumen Total (rowspan = total de filas)
      Col 2 — nivel1       (rowspan por grupo nivel0+nivel1)
      Col 3 — nivel2       (rowspan por grupo nivel0+nivel1+nivel2)
      Col 4 — nivel3_cra   (una fila por valor)
      Col 5 — nivel0       (rowspan por grupo nivel0)
    """
    if df is None or df.empty:
        return html.Div(
            "Sin datos",
            style={"color": "#5E5E5E", "textAlign": "center", "padding": "20px",
                   "fontSize": "13px"},
        )

    cols_req = {"nivel0", "nivel1", "nivel2", "nivel3_cra", "volumen"}
    if not cols_req.issubset(df.columns):
        return html.Div("Columnas insuficientes",
                        style={"color": "#C50F1F", "fontSize": "13px"})

    mask = (
        df["nivel0"].notna() & (df["nivel0"] != "M") &
        df["nivel1"].notna() & (df["nivel1"] != "M") &
        df["nivel2"].notna() & (df["nivel2"] != "M") &
        df["nivel3_cra"].notna() & (df["nivel3_cra"] != "M")
    )
    df_v = df[mask].copy()

    if df_v.empty:
        return html.Div(
            "Sin datos",
            style={"color": "#5E5E5E", "textAlign": "center", "padding": "20px",
                   "fontSize": "13px"},
        )

    group_cols = ["nivel0", "nivel1", "nivel2", "nivel3_cra"]
    df_agg = (
        df_v.groupby(group_cols, as_index=False)["volumen"]
        .sum()
    )

    # Ordenar: AGUA FACTURADA primero, luego NO FACTURADA
    df_agg["_ord"] = df_agg["nivel0"].apply(
        lambda x: 0 if "NO" not in str(x).upper() else 1
    )
    df_agg = (
        df_agg.sort_values(["_ord", "nivel1", "nivel2", "nivel3_cra"])
        .drop("_ord", axis=1)
        .reset_index(drop=True)
    )

    vol_total  = df_agg["volumen"].sum()
    total_rows = len(df_agg)

    # Precomputar rowspans y volúmenes
    # nivel1 se agrupa SIN nivel0 para que valores compartidos (ej. CONSUMO AUTORIZADO)
    # aparezcan como una sola celda fusionada que suma ambos grupos.
    n0_rows = df_agg.groupby("nivel0").size().to_dict()
    n1_rows = df_agg.groupby("nivel1").size().to_dict()
    n2_rows = df_agg.groupby(["nivel0", "nivel1", "nivel2"]).size().to_dict()

    n0_vols = df_agg.groupby("nivel0")["volumen"].sum().to_dict()
    n1_vols = df_agg.groupby("nivel1")["volumen"].sum().to_dict()
    n2_vols = df_agg.groupby(["nivel0", "nivel1", "nivel2"])["volumen"].sum().to_dict()

    # nivel1 que aparecen en más de un nivel0 → estilo "compartido"
    n1_n0_count = df_agg.groupby("nivel1")["nivel0"].nunique().to_dict()

    seen_n0: set = set()
    seen_n1: set = set()
    seen_n2: set = set()
    first_row  = True
    html_rows  = []

    for _, row in df_agg.iterrows():
        n0  = row["nivel0"]
        n1  = row["nivel1"]
        n2  = row["nivel2"]
        n3  = row["nivel3_cra"]
        vol = row["volumen"]
        pal = _palette(n0)

        cells = []

        # Col 1: Volumen Total (solo primera fila)
        if first_row:
            cells.append(_td(
                "Volumen de Entrada al Sistema",
                _fmt(vol_total),
                _VOL_HDR_BG,
                _VOL_HDR_TXT,
                rowspan=total_rows,
            ))
            first_row = False

        # Col 2: nivel1 — clave independiente de nivel0 para fusionar valores compartidos
        k1 = n1
        if k1 not in seen_n1:
            seen_n1.add(k1)
            if n1_n0_count.get(n1, 1) > 1:
                # Celda compartida entre grupos: estilo neutro azul
                bg, tc = "#EFF6FF", "#0063B1"
            else:
                bg, tc = pal["n1"]
            cells.append(_td(str(n1), _fmt(n1_vols[n1]), bg, tc, rowspan=n1_rows[n1]))

        # Col 3: nivel2
        k2 = (n0, n1, n2)
        if k2 not in seen_n2:
            seen_n2.add(k2)
            bg, tc = pal["n2"]
            cells.append(_td(str(n2), _fmt(n2_vols[k2]), bg, tc, rowspan=n2_rows[k2]))

        # Col 4: nivel3_cra (siempre una fila)
        bg, tc = pal["n3"]
        cells.append(_td(str(n3), _fmt(vol), bg, tc))

        # Col 5: nivel0 (solo primera fila del grupo)
        if n0 not in seen_n0:
            seen_n0.add(n0)
            bg, tc = pal["n0"]
            cells.append(_td(str(n0), _fmt(n0_vols[n0]), bg, tc, rowspan=n0_rows[n0]))

        html_rows.append(html.Tr(cells))

    tabla = html.Table(
        html.Tbody(html_rows),
        style={
            "width": "100%",
            "borderCollapse": "collapse",
            "tableLayout": "fixed",
            "fontSize": "11px",
            "fontFamily": "'Segoe UI', 'Inter', system-ui, sans-serif",
        },
    )

    return html.Div(tabla, style={"overflowX": "auto", "width": "100%"})
