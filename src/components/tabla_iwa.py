"""
Tabla del Balance Hídrico IWA — generada dinámicamente desde el DataFrame.
Columnas: Vol. Total | nivel1 | nivel2 | nivel3_cra | nivel0
Los rowspan se calculan a partir de los datos reales.
"""
import pandas as pd
from dash import html


# ── Paleta de colores ────────────────────────────────────────────────────────
_AZUL_1  = "#dbeafe"   # Volumen Total
_AZUL_2  = "#bfdbfe"   # nivel1 / nivel2 de Agua Facturada
_AZUL_3  = "#93c5fd"   # nivel2 de Agua Facturada (más oscuro)
_AZUL_4  = "#60a5fa"   # nivel3_cra de Agua Facturada
_AZUL_N0 = "#3b82f6"   # Agua Facturada (nivel0)
_VIO_1   = "#ede9fe"   # nivel1 de Agua No Facturada
_VIO_2   = "#ddd6fe"   # nivel2 de Agua No Facturada
_VIO_3   = "#c4b5fd"   # nivel3_cra de Agua No Facturada
_VIO_N0  = "#a78bfa"   # Agua No Facturada (nivel0)
_C_OSC   = "#1e1b4b"   # texto oscuro


# ── Helpers ──────────────────────────────────────────────────────────────────

def _fmt(v: float) -> str:
    if v >= 1_000_000:
        return f"{v / 1_000_000:,.2f} M m³"
    if v >= 1_000:
        return f"{v / 1_000:,.1f} k m³"
    return f"{v:,.0f} m³"


def _td(titulo: str, valor: str, bg: str,
        rowspan: int = None, colspan: int = None) -> html.Td:
    """Celda con etiqueta superior pequeña y valor destacado."""
    props: dict = {
        "style": {
            "backgroundColor": bg,
            "color": _C_OSC,
            "border": "2px solid #f8fafc",
            "padding": "5px 7px",
            "textAlign": "center",
            "verticalAlign": "middle",
            "lineHeight": "1.35",
        }
    }
    if rowspan and rowspan > 1:
        props["rowSpan"] = rowspan
    if colspan and colspan > 1:
        props["colSpan"] = colspan

    return html.Td(
        [
            html.Div(titulo, style={
                "fontWeight": "700", "fontSize": "9px",
                "textTransform": "uppercase", "letterSpacing": "0.3px",
                "marginBottom": "3px",
            }),
            html.Div(valor, style={"fontWeight": "800", "fontSize": "11px"}),
        ],
        **props,
    )


# ── Paleta por nivel0 ─────────────────────────────────────────────────────────

def _palette(nivel0: str) -> dict:
    """Devuelve los colores para cada columna según el nivel0 del grupo."""
    if "NO" in str(nivel0).upper():
        return {"n0": _VIO_N0, "n1": _VIO_1, "n2": _VIO_2, "n3": _VIO_3}
    return {"n0": _AZUL_N0, "n1": _AZUL_2, "n2": _AZUL_3, "n3": _AZUL_4}


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
            style={"color": "#adb5bd", "textAlign": "center", "padding": "20px"},
        )

    # ── Filtrar filas con niveles válidos ─────────────────────────────────────
    cols_req = {"nivel0", "nivel1", "nivel2", "nivel3_cra", "volumen"}
    if not cols_req.issubset(df.columns):
        return html.Div("Columnas insuficientes", style={"color": "#e03131"})

    mask = (
        df["nivel0"].notna() & (df["nivel0"] != "M") &
        df["nivel1"].notna() & (df["nivel1"] != "M") &
        df["nivel2"].notna() & (df["nivel2"] != "M") &
        df["nivel3_cra"].notna() & (df["nivel3_cra"] != "M")
    )
    df_v = df[mask].copy()

    if df_v.empty:
        return html.Div("Sin datos", style={"color": "#adb5bd", "textAlign": "center", "padding": "20px"})

    # ── Agregar por los 4 niveles ─────────────────────────────────────────────
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

    # ── Precomputar rowspans y volúmenes por grupo ────────────────────────────
    n0_rows = df_agg.groupby("nivel0").size().to_dict()
    n1_rows = df_agg.groupby(["nivel0", "nivel1"]).size().to_dict()
    n2_rows = df_agg.groupby(["nivel0", "nivel1", "nivel2"]).size().to_dict()

    n0_vols = df_agg.groupby("nivel0")["volumen"].sum().to_dict()
    n1_vols = df_agg.groupby(["nivel0", "nivel1"])["volumen"].sum().to_dict()
    n2_vols = df_agg.groupby(["nivel0", "nivel1", "nivel2"])["volumen"].sum().to_dict()

    # ── Construir filas ───────────────────────────────────────────────────────
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
            cells.append(_td("Volumen de Entrada\nal Sistema",
                              _fmt(vol_total), _AZUL_1, rowspan=total_rows))
            first_row = False

        # Col 2: nivel1
        k1 = (n0, n1)
        if k1 not in seen_n1:
            seen_n1.add(k1)
            cells.append(_td(str(n1), _fmt(n1_vols[k1]), pal["n1"],
                              rowspan=n1_rows[k1]))

        # Col 3: nivel2
        k2 = (n0, n1, n2)
        if k2 not in seen_n2:
            seen_n2.add(k2)
            cells.append(_td(str(n2), _fmt(n2_vols[k2]), pal["n2"],
                              rowspan=n2_rows[k2]))

        # Col 4: nivel3_cra (siempre una fila)
        cells.append(_td(str(n3), _fmt(vol), pal["n3"]))

        # Col 5: nivel0 (solo primera fila del grupo)
        if n0 not in seen_n0:
            seen_n0.add(n0)
            cells.append(_td(str(n0), _fmt(n0_vols[n0]), pal["n0"],
                              rowspan=n0_rows[n0]))

        html_rows.append(html.Tr(cells))

    tabla = html.Table(
        html.Tbody(html_rows),
        style={
            "width": "100%",
            "borderCollapse": "collapse",
            "tableLayout": "fixed",
            "fontSize": "10px",
        },
    )

    return html.Div(tabla, style={"overflowX": "auto", "width": "100%"})