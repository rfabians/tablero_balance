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
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap" rel="stylesheet">
    <style>
      * { box-sizing: border-box; }
      body {
        margin: 0;
        font-family: 'Segoe UI Variable', 'Segoe UI', 'Inter', system-ui, -apple-system, sans-serif;
        background-color: #F3F6FA;
        color: #1A1D1E;
      }
      ::-webkit-scrollbar { width: 6px; height: 6px; }
      ::-webkit-scrollbar-track { background: #F0F2F5; border-radius: 10px; }
      ::-webkit-scrollbar-thumb { background: #C8D3DD; border-radius: 10px; }
      ::-webkit-scrollbar-thumb:hover { background: #0078D4; transition: background 0.2s; }
      .mantine-Paper-root { transition: box-shadow 0.15s ease; }
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
_ACCENTS = {
    "blue":   {"color": "#0078D4", "bg_tint": "#EFF6FF", "border": "#C7E0F4", "icon_bg": "#0078D4"},
    "green":  {"color": "#107C10", "bg_tint": "#F0FDF4", "border": "#BBF7D0", "icon_bg": "#107C10"},
    "orange": {"color": "#D83B01", "bg_tint": "#FFF7ED", "border": "#FED7AA", "icon_bg": "#D83B01"},
    "red":    {"color": "#C50F1F", "bg_tint": "#FEF2F2", "border": "#FCA5A5", "icon_bg": "#C50F1F"},
}


def _color_perdidas(pct: float) -> str:
    if pct > 30: return "red"
    if pct > 15: return "orange"
    return "green"


def tarjetas_kpi(indicadores: dict) -> dmc.SimpleGrid:
    """Genera las 4 tarjetas KPI estilo WinUI claro."""

    def tarjeta(titulo, valor, acento="blue"):
        a = _ACCENTS[acento]
        return html.Div([
            # Barra izquierda de color
            html.Div(style={
                "width": "4px",
                "background": a["color"],
                "position": "absolute", "top": 0, "left": 0, "bottom": 0,
                "borderRadius": "10px 0 0 10px",
            }),
            html.Div([
                # Etiqueta
                html.Div(titulo, style={
                    "fontSize": "11px", "fontWeight": "600",
                    "color": "#5E5E5E",
                    "textTransform": "uppercase", "letterSpacing": "0.7px",
                    "marginBottom": "6px",
                }),
                # Valor grande
                html.Div(valor, style={
                    "fontSize": "28px", "fontWeight": "700",
                    "color": a["color"],
                    "lineHeight": "1.1",
                }),
            ], style={"paddingLeft": "4px"}),
        ], style={
            "background": "#FFFFFF",
            "border": f"1px solid {a['border']}",
            "borderRadius": "10px",
            "padding": "16px 18px 16px 20px",
            "position": "relative",
            "overflow": "hidden",
            "textAlign": "left",
            "boxShadow": "0 1px 3px rgba(0,0,0,0.06), 0 4px 12px rgba(0,0,0,0.04)",
        })

    pct = indicadores["porcentaje_perdidas"]
    return dmc.SimpleGrid(
        cols={"base": 2, "sm": 4},
        spacing="sm",
        children=[
            tarjeta("IPUF",                   f"{indicadores['ipuf']:,.2f}",                    "blue"),
            tarjeta("% Pérdidas",             f"{pct:,.1f}%",                                  _color_perdidas(pct)),
            tarjeta("Vol. Facturado (m³)",    fmt_volumen(indicadores["volumen_facturado"]),    "green"),
            tarjeta("Vol. No Facturado (m³)", fmt_volumen(indicadores["volumen_anf"]),          "orange"),
        ],
    )


# ---------------------------------------------------------------------------
# Componente: panel de leyenda IPUF (estático)
# ---------------------------------------------------------------------------
def panel_leyenda() -> html.Div:
    def item_leyenda(color, texto, texto_color="#3A3A3A"):
        return html.Div([
            html.Div(style={
                "width": 10, "height": 10, "borderRadius": "3px",
                "backgroundColor": color, "flexShrink": 0,
                "display": "inline-block", "marginRight": "6px",
                "verticalAlign": "middle",
            }),
            html.Span(texto, style={
                "fontSize": "12px", "color": texto_color,
                "fontWeight": "500", "verticalAlign": "middle",
            }),
        ], style={"display": "inline-flex", "alignItems": "center"})

    return html.Div([
        html.Div("Clasificación IPUF", style={
            "fontSize": "11px", "fontWeight": "700", "color": "#0078D4",
            "textTransform": "uppercase", "letterSpacing": "0.6px",
            "marginBottom": "10px",
        }),
        html.Div([
            item_leyenda("#107C10", "IPUF Bajo (< 4)"),
            item_leyenda("#FF8C00", "IPUF Medio (4–6)"),
            item_leyenda("#C50F1F", "IPUF Alto (> 6)"),
        ], style={"display": "flex", "flexWrap": "wrap", "gap": "12px", "alignItems": "center"}),
    ])


# ---------------------------------------------------------------------------
# Layout
# ---------------------------------------------------------------------------
app.layout = dmc.MantineProvider(
    forceColorScheme="light",
    theme={
        "primaryColor": "blue",
        "fontFamily": "'Segoe UI Variable', 'Segoe UI', 'Inter', system-ui, sans-serif",
    },
    children=[dmc.AppShell(
        header={"height": 68},
        padding=0,
        style={"background": "#F3F6FA"},
        children=[
            dcc.Store(id="store-filtros"),
            html.Div(
                id="contenedor-encabezado",
                children=crear_encabezado(filtro_actual=filtro_inicial, df=df),
            ),
            dmc.AppShellMain(
                style={"background": "#F3F6FA"},
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
                                color="#0078D4",
                                children=html.Div(
                                    id="contenedor-indicadores",
                                    style={"marginBottom": "12px"},
                                ),
                            ),

                            # ── Fila 2: Mapa (40%) + Panel derecho (60%) ──
                            dmc.Grid(
                                gutter="sm",
                                children=[
                                    # Mapa
                                    dmc.GridCol(
                                        html.Div([
                                            html.Div(id="contenedor-mapa",
                                                     children=generar_mapa_leaflet(gdf),
                                                     style={
                                                         "width": "100%", "height": "55vh",
                                                         "overflow": "hidden",
                                                         "position": "relative", "zIndex": 0,
                                                     }),
                                        ], style={
                                            "background": "#FFFFFF",
                                            "border": "1px solid #E1E5EA",
                                            "borderRadius": "10px",
                                            "overflow": "hidden",
                                            "boxShadow": "0 1px 3px rgba(0,0,0,0.06)",
                                        }),
                                        span={"base": 12, "sm": 4},
                                    ),
                                    # Panel derecho: leyenda + tabla IWA
                                    dmc.GridCol(
                                        dmc.Paper(
                                            [
                                                panel_leyenda(),
                                                dmc.Divider(my="sm",
                                                            style={"borderColor": "#E1E5EA"}),
                                                html.Div("Balance Hídrico IWA", style={
                                                    "fontSize": "12px", "fontWeight": "700",
                                                    "color": "#0078D4",
                                                    "textTransform": "uppercase",
                                                    "letterSpacing": "0.6px",
                                                    "marginBottom": "10px",
                                                }),
                                                html.Div(
                                                    id="contenedor-tabla-iwa",
                                                    children=generar_tabla_iwa(df),
                                                ),
                                            ],
                                            withBorder=True, shadow="xs",
                                            p="sm", radius="md",
                                            style={
                                                "height": "55vh", "overflow": "auto",
                                                "borderColor": "#E1E5EA",
                                                "background": "#FFFFFF",
                                            },
                                        ),
                                        span={"base": 12, "sm": 8},
                                    ),
                                ],
                            ),

                            # ── Fila 3: Sankey ────────────────────────────
                            dmc.Paper(
                                [
                                    html.Div("Diagrama de Flujo — Balance Hídrico", style={
                                        "fontSize": "12px", "fontWeight": "700",
                                        "color": "#0078D4",
                                        "textTransform": "uppercase",
                                        "letterSpacing": "0.6px",
                                        "marginBottom": "8px",
                                    }),
                                    dcc.Loading(
                                        id="loading-sankey",
                                        type="dot",
                                        color="#0078D4",
                                        children=html.Div(id="contenedor-sankey",
                                                          children=generar_sankey(df)),
                                    ),
                                ],
                                withBorder=True, shadow="xs",
                                p="md", radius="md",
                                mt="sm", mb="xl",
                                style={
                                    "borderColor": "#E1E5EA",
                                    "background": "#FFFFFF",
                                },
                            ),
                        ],
                    )
                ]
            ),
        ],
    )]
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
    MAPA_COLORES = {"IPUF BAJO": "#107C10", "IPUF MEDIO": "#FF8C00", "IPUF ALTO": "#C50F1F"}
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