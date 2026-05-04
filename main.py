from models.FiltrosTablero import FiltroTablero
from repositorios.obtener_datos import obtener_datos
from components.header import crear_encabezado
from components.mapa import generar_mapa_leaflet
from components.sankey import generar_sankey
from components.tabla_iwa import generar_tabla_iwa

import dash_mantine_components as dmc
from dash import Dash, html, Input, Output, dcc, ctx
import dash
import json
import pandas as pd

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
app = Dash(__name__, suppress_callback_exceptions=True)

# Viewport meta para soporte mobile
app.index_string = """<!DOCTYPE html>
<html>
  <head>
    {%metas%}
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0">
    <title>Balance Hídrico</title>
    {%favicon%}
    {%css%}
    <style>
      * { box-sizing: border-box; }
      body { margin: 0; font-family: system-ui, sans-serif; }
    </style>
  </head>
  <body>
    {%app_entry%}
    <footer>
      {%config%}
      {%scripts%}
      {%renderer%}
    </footer>
  </body>
</html>"""

# ---------------------------------------------------------------------------
# Carga inicial de datos
# ---------------------------------------------------------------------------
filtro_inicial = FiltroTablero()
df, gdf = obtener_datos(filtro_inicial)
MES_MAXIMO = max(m for m in df["mescalculo"].unique() if m != "M")

# ---------------------------------------------------------------------------
# Helpers de negocio
# ---------------------------------------------------------------------------
def normalizar_lista(valor):
    """Convierte un valor escalar o None en lista o None."""
    if not valor:
        return None
    return valor if isinstance(valor, list) else [valor]


def fmt_volumen(v: float) -> str:
    """Formatea un volumen en m³ con sufijo M/k para legibilidad."""
    if v >= 1_000_000:
        return f"{v / 1_000_000:,.2f} M"
    if v >= 1_000:
        return f"{v / 1_000:,.1f} k"
    return f"{v:,.1f}"


def calcular_indicadores(df_datos: pd.DataFrame) -> dict:
    """Calcula KPIs globales del DataFrame filtrado."""
    if df_datos.empty:
        return {
            "volumen_anf": 0, "volumen_facturado": 0,
            "total_suscriptores": 0, "ipuf": 0,
            "rango_ipuf": "IPUF BAJO", "porcentaje_perdidas": 0,
        }

    vol = df_datos.groupby("nivel0")["volumen"].sum()
    volumen_anf      = vol.get("AGUA NO FACTURADA", 0)
    volumen_facturado = vol.get("AGUA FACTURADA", 0)
    total_suscriptores = df_datos["suscriptores"].sum() if "suscriptores" in df_datos.columns else 0

    ipuf = volumen_anf / total_suscriptores if total_suscriptores > 0 else 0
    volumen_total = volumen_anf + volumen_facturado
    porcentaje_perdidas = (volumen_anf / volumen_total * 100) if volumen_total > 0 else 0

    if ipuf < 4:
        rango_ipuf = "IPUF BAJO"
    elif ipuf <= 6:
        rango_ipuf = "IPUF MEDIO"
    else:
        rango_ipuf = "IPUF ALTO"

    return {
        "volumen_anf": volumen_anf,
        "volumen_facturado": volumen_facturado,
        "total_suscriptores": total_suscriptores,
        "ipuf": ipuf,
        "rango_ipuf": rango_ipuf,
        "porcentaje_perdidas": porcentaje_perdidas,
    }


def calcular_rangos_por_sector(df_filtrado: pd.DataFrame) -> dict:
    """
    Calcula el rango IPUF para todos los sectores en una sola pasada vectorizada.
    Reemplaza el loop O(N) anterior.
    """
    if df_filtrado.empty:
        return {}

    anf = (
        df_filtrado[df_filtrado["nivel0"] == "AGUA NO FACTURADA"]
        .groupby("sector_hidraulico")["volumen"].sum()
    )
    sus = df_filtrado.groupby("sector_hidraulico")["suscriptores"].sum()
    ipuf_por_sector = (anf / sus).fillna(0)

    def rango(v):
        if v < 4:   return "IPUF BAJO"
        if v <= 6:  return "IPUF MEDIO"
        return "IPUF ALTO"

    return {str(k): rango(v) for k, v in ipuf_por_sector.items()}


def filtrar_df(df_base: pd.DataFrame, filtro: FiltroTablero) -> pd.DataFrame:
    """Aplica los filtros del tablero sobre el DataFrame base."""
    resultado = df_base
    if filtro.mes:
        meses = filtro.mes if isinstance(filtro.mes, list) else [filtro.mes]
        resultado = resultado[resultado["mescalculo"].isin(meses)]
    if filtro.aps:
        aps_l = filtro.aps if isinstance(filtro.aps, list) else [filtro.aps]
        resultado = resultado[resultado["aps"].isin(aps_l)]
    if filtro.zona:
        zonas = filtro.zona if isinstance(filtro.zona, list) else [filtro.zona]
        resultado = resultado[resultado["zona"].isin(zonas)]
    if filtro.sector:
        sectores = [str(s) for s in (filtro.sector if isinstance(filtro.sector, list) else [filtro.sector])]
        resultado = resultado[resultado["sector_hidraulico"].astype(str).isin(sectores)]
    return resultado


# ---------------------------------------------------------------------------
# Componente: tarjetas KPI
# ---------------------------------------------------------------------------
_COLORES_PERDIDAS = {"<15": "green", "15-30": "yellow", ">30": "red"}

def _color_perdidas(pct: float) -> str:
    if pct > 30: return "red"
    if pct > 15: return "yellow"
    return "green"


def tarjetas_kpi(indicadores: dict) -> dmc.SimpleGrid:
    """Genera las 4 tarjetas de KPI con layout responsivo 2→4 columnas."""
    def tarjeta(titulo, valor, color=None):
        return dmc.Paper(
            [
                dmc.Text(titulo, c="dimmed", size="xs", fw=500),
                dmc.Text(valor, fw=700, size="xl", c=color or "dark"),
            ],
            withBorder=True, shadow="xs", p="md", radius="md",
            style={"textAlign": "center"},
        )

    pct = indicadores["porcentaje_perdidas"]
    return dmc.SimpleGrid(
        cols={"base": 2, "sm": 4},
        spacing="sm",
        children=[
            tarjeta("IPUF", f"{indicadores['ipuf']:,.2f}"),
            tarjeta("% Pérdidas", f"{pct:,.1f}%", _color_perdidas(pct)),
            tarjeta("Vol. Facturado (m³)", fmt_volumen(indicadores["volumen_facturado"])),
            tarjeta("Vol. No Facturado (m³)", fmt_volumen(indicadores["volumen_anf"])),
        ],
    )


# ---------------------------------------------------------------------------
# Componente: panel de leyenda IPUF (estático)
# ---------------------------------------------------------------------------
def panel_leyenda() -> html.Div:
    def item_leyenda(color, texto):
        return dmc.Group([
            html.Div(style={
                "width": 12, "height": 12, "borderRadius": 2,
                "backgroundColor": color, "flexShrink": 0,
            }),
            dmc.Text(texto, size="xs"),
        ], gap="xs", align="center")

    return html.Div([
        dmc.Text("Leyenda del mapa", fw=700, size="xs", mb=4),
        dmc.Group([
            item_leyenda("#22c55e", "IPUF Bajo  (< 4)"),
            item_leyenda("#eab308", "IPUF Medio (4–6)"),
            item_leyenda("#ef4444", "IPUF Alto  (> 6)"),
        ], gap="md"),
    ])


# ---------------------------------------------------------------------------
# Layout
# ---------------------------------------------------------------------------
app.layout = dmc.MantineProvider(
    dmc.AppShell(
        header={"height": 80},
        padding=0,
        children=[
            dcc.Store(id="store-filtros"),
            html.Div(
                id="contenedor-encabezado",
                children=crear_encabezado(filtro_actual=filtro_inicial, df=df),
            ),
            dmc.AppShellMain(
                children=[
                    dmc.Container(
                        fluid=True,
                        px="md",
                        py="sm",
                        children=[
                            # ── Fila 1: KPIs ──────────────────────────────
                            dcc.Loading(
                                id="loading-kpi",
                                type="dot",
                                color="#228be6",
                                children=html.Div(
                                    id="contenedor-indicadores",
                                    style={"marginBottom": "12px"},
                                ),
                            ),

                            # ── Fila 2: Mapa (50%) + Panel derecho (50%) ──
                            dmc.Grid(
                                gutter="sm",
                                children=[
                                    # Mapa — la mitad del ancho
                                    dmc.GridCol(
                                        html.Div(
                                            id="contenedor-mapa",
                                            children=generar_mapa_leaflet(gdf),
                                            style={
                                                "width": "100%", "height": "55vh",
                                                "overflow": "hidden",
                                                "position": "relative", "zIndex": 0,
                                            },
                                        ),
                                        span={"base": 12, "sm": 4},
                                    ),
                                    # Panel derecho: leyenda + tabla IWA
                                    dmc.GridCol(
                                        dmc.Paper(
                                            [
                                                panel_leyenda(),
                                                dmc.Divider(my="sm"),
                                                dmc.Text(
                                                    "Balance Hídrico IWA",
                                                    fw=700, size="sm", mb="xs",
                                                ),
                                                html.Div(
                                                    id="contenedor-tabla-iwa",
                                                    children=generar_tabla_iwa(df),
                                                ),
                                            ],
                                            withBorder=True, shadow="xs",
                                            p="sm", radius="md",
                                            style={"heinght": "45vh", "overflow": "auto"},
                                        ),
                                        span={"base": 12, "sm": 8},
                                    ),
                                ],
                            ),

                            # ── Fila 3: Sankey ────────────────────────────
                            dmc.Paper(
                                dcc.Loading(
                                    id="loading-sankey",
                                    type="dot",
                                    color="#228be6",
                                    children=html.Div(id="contenedor-sankey",
                                                      children=generar_sankey(df)),
                                ),
                                withBorder=True, shadow="sm",
                                p="md", radius="md",
                                mt="sm", mb="xl",
                            ),
                        ],
                    )
                ]
            ),
        ],
    )
)


# ---------------------------------------------------------------------------
# Callbacks
# ---------------------------------------------------------------------------
@app.callback(
    Output("tooltip-mapa", "children"),
    Input("capa-sectores-leaflet", "hoverData"),
    prevent_initial_call=True,
)
def mostrar_tooltip(hover_data):
    if hover_data:
        nombre = hover_data.get("properties", {}).get("name", "Sector desconocido")
        return f"Sector: {nombre}"
    return dash.no_update


@app.callback(
    Output("store-filtros", "data"),
    Output("contenedor-encabezado", "children"),
    Output("mapa-principal", "viewport"),
    Output("capa-sectores-leaflet", "data"),
    Output("contenedor-indicadores", "children"),
    Output("contenedor-tabla-iwa", "children"),
    Output("contenedor-sankey", "children"),
    Input("filtro-mes", "value"),
    Input("filtro-aps", "value"),
    Input("filtro-zona", "value"),
    Input("filtro-sector", "value"),
    Input("btn-limpiar-filtros", "n_clicks"),
    Input("capa-sectores-leaflet", "clickData"),
    prevent_initial_call=False,
)
def actualizar_tablero(mes, aps, zona, sector, _n_clicks, click_feature):
    trigger = ctx.triggered_id

    # ── Construir nuevo filtro ────────────────────────────────────────────
    if trigger == "btn-limpiar-filtros":
        nuevo_filtro = FiltroTablero(mes=normalizar_lista(MES_MAXIMO))
    else:
        if trigger == "capa-sectores-leaflet" and click_feature:
            nombre_sector = click_feature.get("properties", {}).get("name")
            if nombre_sector:
                sector = str(nombre_sector)

        nuevo_filtro = FiltroTablero(
            mes=normalizar_lista(mes) if mes else normalizar_lista(MES_MAXIMO),
            aps=normalizar_lista(aps),
            zona=normalizar_lista(zona),
            sector=normalizar_lista(sector),
        )

        # Validaciones cruzadas de filtros
        if trigger in ("filtro-sector", "capa-sectores-leaflet") and sector:
            df_sec = df[df["sector_hidraulico"].astype(str) == str(sector)]
            if not df_sec.empty:
                z = df_sec["zona"].iloc[0]
                a = df_sec["aps"].iloc[0]
                if z and z != "M":
                    nuevo_filtro.zona = normalizar_lista(z)
                if a and a != "M":
                    nuevo_filtro.aps = normalizar_lista(a)

        elif trigger == "filtro-zona" and zona:
            if sector and df[(df["zona"] == zona) & (df["sector_hidraulico"].astype(str) == str(sector))].empty:
                nuevo_filtro.sector = None
            if aps and df[(df["zona"] == zona) & (df["aps"] == aps)].empty:
                nuevo_filtro.aps = None

        elif trigger == "filtro-aps" and aps:
            if zona and df[(df["aps"] == aps) & (df["zona"] == zona)].empty:
                nuevo_filtro.zona = None
                nuevo_filtro.sector = None
            if sector and df[(df["aps"] == aps) & (df["sector_hidraulico"].astype(str) == str(sector))].empty:
                nuevo_filtro.sector = None

    # ── Filtrar datos ────────────────────────────────────────────────────
    df_filtrado = filtrar_df(df, nuevo_filtro)

    # ── KPIs ─────────────────────────────────────────────────────────────
    indicadores = calcular_indicadores(df_filtrado)
    kpis = tarjetas_kpi(indicadores)

    # ── GeoJSON + viewport ───────────────────────────────────────────────
    MAPA_COLORES = {"IPUF BAJO": "#22c55e", "IPUF MEDIO": "#eab308", "IPUF ALTO": "#ef4444"}
    sectores_filtrados = [
        str(s) for s in df_filtrado["sector_hidraulico"].unique() if s != "M"
    ]

    datos_geojson = {"type": "FeatureCollection", "features": []}
    nuevo_viewport = dash.no_update

    if not df_filtrado.empty and not gdf.empty:
        gdf_filtrado = gdf[gdf["name"].astype(str).isin(sectores_filtrados)].copy()

        if not gdf_filtrado.empty:
            # Cálculo vectorizado de IPUF por sector (sin loop)
            rangos = calcular_rangos_por_sector(df_filtrado)
            gdf_filtrado["categoria_perdidas"] = gdf_filtrado["name"].astype(str).map(rangos)
            gdf_filtrado["color_hex"] = (
                gdf_filtrado["categoria_perdidas"].map(MAPA_COLORES).fillna("#9ca3af")
            )

            minx, miny, maxx, maxy = gdf_filtrado.total_bounds
            padding = 0.01 if minx == maxx and miny == maxy else 0
            limites = [
                [float(miny) - padding, float(minx) - padding],
                [float(maxy) + padding, float(maxx) + padding],
            ]
            nuevo_viewport = {"bounds": limites, "transition": "flyTo",
                              "options": {"padding": [20, 20]}}
            datos_geojson = json.loads(gdf_filtrado.to_json())
        else:
            datos_geojson = json.loads(gdf.iloc[0:0].to_json())

    return (
        str(nuevo_filtro),
        crear_encabezado(filtro_actual=nuevo_filtro, df=df),
        nuevo_viewport,
        datos_geojson,
        kpis,
        generar_tabla_iwa(df_filtrado),
        generar_sankey(df_filtrado),
    )


# Expuesto para gunicorn: gunicorn main:server
server = app.server

if __name__ == "__main__":
    app.run(debug=True)