from models.FiltrosTablero import FiltroTablero
from repositorios.obtener_datos import obtener_datos
from components.header import crear_encabezado
from components.mapa import generar_mapa_leaflet
from components.sankey import generar_sankey

import dash_mantine_components as dmc
from dash import Dash, html, Input, Output, dcc, ctx
import dash
import json

app = Dash()

filtro = FiltroTablero()

df, gdf = obtener_datos(filtro)

filtro.mes = max(mes for mes in df['mescalculo'].unique() if mes != 'M')

def calcular_indicadores(df_datos):
    # 1. Sumar volumen donde nivel0 == 'AGUA NO FACTURADA'
    volumen_anf = df_datos[df_datos['nivel0'] == 'AGUA NO FACTURADA']['volumen'].sum() if 'volumen' in df_datos.columns and 'nivel0' in df_datos.columns else 0
    
    # Volumen Facturado
    volumen_facturado = df_datos[df_datos['nivel0'] == 'AGUA FACTURADA']['volumen'].sum() if 'volumen' in df_datos.columns and 'nivel0' in df_datos.columns else 0
    
    # 2. Sumar la cantidad de suscriptores
    if 'suscriptores' in df_datos.columns and 'sector_hidraulico' in df_datos.columns:
        #df_unicos = df_datos.drop_duplicates(subset=['sector_hidraulico'])
        total_suscriptores = df_datos['suscriptores'].sum()
    else:
        total_suscriptores = df_datos['suscriptores'].sum() if 'suscriptores' in df_datos.columns else 0

    # 3. Calcular IPUF
    if total_suscriptores > 0:
        ipuf = volumen_anf / total_suscriptores
    else:
        ipuf = 0
        
    # Calcular Porcentaje de Pérdidas
    volumen_total = volumen_anf + volumen_facturado
    if volumen_total > 0:
        porcentaje_perdidas = (volumen_anf / volumen_total) * 100
    else:
        porcentaje_perdidas = 0

    # 4. Determinar rango
    if ipuf < 4:
        rango_ipuf = 'IPUF BAJO'
    elif 4 <= ipuf <= 6:
        rango_ipuf = 'IPUF MEDIO'
    else:
        rango_ipuf = 'IPUF ALTO'

    return {
        "volumen_anf": volumen_anf,
        "volumen_facturado": volumen_facturado,
        "total_suscriptores": total_suscriptores,
        "ipuf": ipuf,
        "rango_ipuf": rango_ipuf,
        "porcentaje_perdidas": porcentaje_perdidas
    }


app.layout = dmc.MantineProvider(
dmc.AppShell(
    header={"height": 80},  # Esto le dice al AppShell que reserve 80px de altura para el header
    padding=0, # Eliminamos el padding global del AppShell
    children=[
        dcc.Store(id="store-filtros"),
        html.Div(
            id="contenedor-encabezado",
            children=crear_encabezado(filtro_actual=filtro, df=df)
        ),
        dmc.AppShellMain(
            children=[
                dmc.Container([
                    # Fila 1: Indicadores
                    html.Div(id="contenedor-indicadores", style={"marginTop": "10px", "marginBottom": "10px"}),
                    
                    # Fila 2: Contenido principal dividido en 4 columnas
                    dmc.Grid([
                        # Columna vacía 1 (ocupa 3 de 12 espacios = 1/4)
                        dmc.GridCol([
                            html.Div("Espacio para futuros componentes", style={"height": "50vh", "backgroundColor": "#f8f9fa", "borderRadius": "8px", "display": "flex", "alignItems": "center", "justifyContent": "center", "color": "#adb5bd", "margin": "2px"})
                        ], span=3, p=0),
                        
                        # Columna vacía 2 (ocupa 3 de 12 espacios = 1/4)
                        dmc.GridCol([
                            html.Div("Espacio para futuros componentes", style={"height": "50vh", "backgroundColor": "#f8f9fa", "borderRadius": "8px", "display": "flex", "alignItems": "center", "justifyContent": "center", "color": "#adb5bd", "margin": "2px"})
                        ], span=3, p=0),
                        
                        # Columna vacía 3 (ocupa 3 de 12 espacios = 1/4)
                        dmc.GridCol([
                            html.Div("Espacio para futuros componentes", style={"height": "50vh", "backgroundColor": "#f8f9fa", "borderRadius": "8px", "display": "flex", "alignItems": "center", "justifyContent": "center", "color": "#adb5bd", "margin": "2px"})
                        ], span=3, p=0),
                        
                        # Columna 4: El Mapa (ocupa 3 de 12 espacios = 1/4)
                        dmc.GridCol([
                            html.Div(
                                id="contenedor-mapa",
                                children=generar_mapa_leaflet(gdf),
                                style={"width": "100%", "height": "50vh", "padding": "2px"}
                            )
                        ], span=3, p=0)
                    ], gutter=0),
                    
                    # Fila 3: Gráfico Sankey
                    dmc.Grid([
                        dmc.GridCol([
                            dmc.Paper(
                                children=[
                                    html.Div(id="contenedor-sankey", children=generar_sankey(df))
                                ],
                                withBorder=True, shadow="sm", p="md", radius="md"
                            )
                        ], span=12, p="xs")
                    ], style={"marginTop": "20px", "marginBottom": "40px"})
                    
                ], fluid=True, px=0) 
            ]
        )
    ]
)
)


@app.callback(
    Output("tooltip-mapa", "children"),
    [Input("capa-sectores-leaflet", "hoverData")],
    prevent_initial_call=True
)
def mostrar_tooltip(hoverData):
    if hoverData:
        nombre = hoverData.get('properties', {}).get('name', 'Sector desconocido')
        return f"Sector: {nombre}"
    return dash.no_update

@app.callback(
    Output("store-filtros", "data"),
    Output("contenedor-encabezado", "children"),
    Output("mapa-principal", "viewport"), 
    Output("capa-sectores-leaflet", "data"), 
    Output("contenedor-indicadores", "children"),
    Output("contenedor-sankey", "children"),
    [
        Input("filtro-mes", "value"),
        Input("filtro-aps", "value"),
        Input("filtro-zona", "value"),
        Input("filtro-sector", "value"),
        Input("btn-limpiar-filtros", "n_clicks"),
        Input("capa-sectores-leaflet", "clickData")
    ],
    prevent_initial_call=False
)
def actualizar_tablero(mes, aps, zona, sector, n_clicks, click_feature):
    def normalizar_lista(valor):
        if not valor: return None
        return valor if isinstance(valor, list) else [valor]

    trigger = ctx.triggered_id
    
    if trigger == "btn-limpiar-filtros":
        nuevo_filtro = FiltroTablero(
            mes=normalizar_lista(max(m for m in df['mescalculo'].unique() if m != 'M')),
            aps=None,
            zona=None,
            sector=None
        )
    else:
        if trigger == "capa-sectores-leaflet" and click_feature:
            sector_seleccionado = click_feature.get('properties', {}).get('name')
            if sector_seleccionado:
                sector = str(sector_seleccionado)
        
        nuevo_filtro = FiltroTablero(
            mes=normalizar_lista(mes) if mes else normalizar_lista(max(m for m in df['mescalculo'].unique() if m != 'M')),
            aps=normalizar_lista(aps),
            zona=normalizar_lista(zona),
            sector=normalizar_lista(sector)
        )

        if (trigger == "filtro-sector" or trigger == "capa-sectores-leaflet") and sector:
            df_sector = df[df['sector_hidraulico'].astype(str) == str(sector)]
            if not df_sector.empty:
                zona_del_sector = df_sector['zona'].iloc[0]
                aps_del_sector = df_sector['aps'].iloc[0]
                if zona_del_sector and zona_del_sector != 'M':
                    nuevo_filtro.zona = normalizar_lista(zona_del_sector)
                if aps_del_sector and aps_del_sector != 'M':
                    nuevo_filtro.aps = normalizar_lista(aps_del_sector)
        elif trigger == "filtro-zona" and zona:
            if sector: 
                df_validacion = df[(df['zona'] == zona) & (df['sector_hidraulico'].astype(str) == str(sector))]
                if df_validacion.empty:
                    nuevo_filtro.sector = None 
            
            if aps:
                df_validacion_aps = df[(df['zona'] == zona) & (df['aps'] == aps)]
                if df_validacion_aps.empty:
                    nuevo_filtro.aps = None

        elif trigger == "filtro-aps" and aps:
             if zona: 
                df_validacion_zona = df[(df['aps'] == aps) & (df['zona'] == zona)]
                if df_validacion_zona.empty:
                    nuevo_filtro.zona = None
                    nuevo_filtro.sector = None
             if sector:
                df_validacion_sec = df[(df['aps'] == aps) & (df['sector_hidraulico'].astype(str) == str(sector))]
                if df_validacion_sec.empty:
                    nuevo_filtro.sector = None
                
    pnuevo_encabezado_visual = crear_encabezado(filtro_actual=nuevo_filtro, df=df)
    datos_para_store = f"Filtros actuales instanciados: {nuevo_filtro}"
    
    # 1. Filtrar los datos
    df_filtrado = df.copy()
    if nuevo_filtro.mes:
        meses = nuevo_filtro.mes if isinstance(nuevo_filtro.mes, list) else [nuevo_filtro.mes]
        df_filtrado = df_filtrado[df_filtrado['mescalculo'].isin(meses)]
    if nuevo_filtro.aps:
        aps_list = nuevo_filtro.aps if isinstance(nuevo_filtro.aps, list) else [nuevo_filtro.aps]
        df_filtrado = df_filtrado[df_filtrado['aps'].isin(aps_list)]
    if nuevo_filtro.zona:
        zonas = nuevo_filtro.zona if isinstance(nuevo_filtro.zona, list) else [nuevo_filtro.zona]
        df_filtrado = df_filtrado[df_filtrado['zona'].isin(zonas)]
    if nuevo_filtro.sector:
        sectores = nuevo_filtro.sector if isinstance(nuevo_filtro.sector, list) else [nuevo_filtro.sector]
        sectores_str = [str(s) for s in sectores]
        df_filtrado = df_filtrado[df_filtrado['sector_hidraulico'].astype(str).isin(sectores_str)]

    # 2. Calcular los indicadores con los datos filtrados
    indicadores = calcular_indicadores(df_filtrado)
    
    # Creamos un componente visual para mostrar los indicadores (facturado y no facturado)
    tarjetas_indicadores = dmc.Group([
        dmc.Paper(
            children=[
                dmc.Text("IPUF", c="dimmed", size="xs"),
                dmc.Text(f"{indicadores['ipuf']:,.2f}", fw=700, size="xl")
            ],
            withBorder=True, shadow="sm", p="md", radius="md", style={"flex": 1, "textAlign": "center", "margin": "0 5px"}
        ),
        dmc.Paper(
            children=[
                dmc.Text("% Pérdidas", c="dimmed", size="xs"),
                dmc.Text(f"{indicadores['porcentaje_perdidas']:,.2f}%", fw=700, size="xl", c="red" if indicadores['porcentaje_perdidas'] > 30 else "yellow" if indicadores['porcentaje_perdidas'] > 15 else "green")
            ],
            withBorder=True, shadow="sm", p="md", radius="md", style={"flex": 1, "textAlign": "center", "margin": "0 5px"}
        ),
        dmc.Paper(
            children=[
                dmc.Text("Volumen Facturado (m3)", c="dimmed", size="xs"),
                dmc.Text(f"{indicadores['volumen_facturado']:,.2f}", fw=700, size="xl")
            ],
            withBorder=True, shadow="sm", p="md", radius="md", style={"flex": 1, "textAlign": "center", "margin": "0 5px"}
        ),
        dmc.Paper(
            children=[
                dmc.Text("Volumen No Facturado (m3)", c="dimmed", size="xs"),
                dmc.Text(f"{indicadores['volumen_anf']:,.2f}", fw=700, size="xl")
            ],
            withBorder=True, shadow="sm", p="md", radius="md", style={"flex": 1, "textAlign": "center", "margin": "0 5px"}
        )
    ], grow=True)

    # 3. Filtrar gdf para el mapa
    sectores_filtrados = [str(s) for s in df_filtrado['sector_hidraulico'].unique() if s != 'M']
    
    # Asignar color al mapa calculando el IPUF por cada sector individual
    mapa_colores = {
        'IPUF BAJO': '#22c55e',  # Verde
        'IPUF MEDIO': '#eab308',  # Amarillo
        'IPUF ALTO': '#ef4444'  # Rojo
    }
    
    if not df_filtrado.empty and 'sector_hidraulico' in df_filtrado.columns and not gdf.empty:
        # Hacemos una copia solo de los sectores que están en la lista
        gdf_filtrado = gdf[gdf['name'].astype(str).isin(sectores_filtrados)].copy()
        
        if not gdf_filtrado.empty:
            rangos_por_sector = {}
            for sector_id in sectores_filtrados:
                df_sec = df_filtrado[df_filtrado['sector_hidraulico'].astype(str) == sector_id]
                ind_sec = calcular_indicadores(df_sec)
                rangos_por_sector[sector_id] = ind_sec['rango_ipuf']
                
            gdf_filtrado['categoria_perdidas'] = gdf_filtrado['name'].astype(str).map(rangos_por_sector)
            gdf_filtrado['color_hex'] = gdf_filtrado['categoria_perdidas'].map(mapa_colores)
            gdf_filtrado['color_hex'] = gdf_filtrado['color_hex'].fillna('#9ca3af')
            
            minx, miny, maxx, maxy = gdf_filtrado.total_bounds
            if minx == maxx and miny == maxy:
                limites_mapa = [[float(miny) - 0.01, float(minx) - 0.01], [float(maxy) + 0.01, float(maxx) + 0.01]]
            else:
                limites_mapa = [[float(miny), float(minx)], [float(maxy), float(maxx)]]
                
            nuevo_viewport = dict(bounds=limites_mapa, transition="flyTo", options={"padding": [20, 20]})
            datos_geojson = json.loads(gdf_filtrado.to_json())
        else:
            datos_geojson = json.loads(gdf.iloc[0:0].to_json())
            nuevo_viewport = dash.no_update
    else:
        # Si df_filtrado está vacío, mandamos un geojson vacío
        datos_geojson = json.loads(gdf.iloc[0:0].to_json()) if not gdf.empty else {"type": "FeatureCollection", "features": []}
        nuevo_viewport = dash.no_update 
        
    # 4. Generar el Sankey con los datos filtrados
    sankey_chart = generar_sankey(df_filtrado)
    
    return datos_para_store, pnuevo_encabezado_visual, nuevo_viewport, datos_geojson, tarjetas_indicadores, sankey_chart




if __name__ == '__main__':
    filtro = FiltroTablero()
    obtener_datos(filtro)
    app.run(debug=True)
