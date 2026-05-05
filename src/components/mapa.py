import dash_leaflet as dl
import json
from dash_extensions.javascript import assign

estilo_poligonos = assign("""function(feature, context){
    return {
        fillColor: feature.properties.color_hex,
        color: "#FFFFFF",
        weight: 1.5,
        fillOpacity: 0.72
    };
}""")


def generar_mapa_leaflet(gdf):
    """
    Recibe un GeoDataFrame, asigna colores categóricos y retorna un mapa de Leaflet centrado.
    Estilo WinUI claro — tiles claros con sectores coloreados en verde/naranja/rojo.
    """
    mapa_colores = {
        'IPUF BAJO':  '#107C10',  # Verde WinUI
        'IPUF MEDIO': '#FF8C00',  # Naranja WinUI
        'IPUF ALTO':  '#C50F1F',  # Rojo WinUI
    }

    tile_url = "https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png"
    tile_attr = (
        '&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a> '
        '&copy; <a href="https://carto.com/attributions">CARTO</a>'
    )

    map_style = {
        'height': '100%', 'width': '100%',
        'borderRadius': '10px', 'zIndex': 0,
        'margin': 0, 'padding': 0,
    }

    if gdf is None or gdf.empty:
        return dl.Map(
            [dl.TileLayer(url=tile_url, attribution=tile_attr)],
            id="mapa-principal",
            center=[4.6097, -74.0817],
            zoom=12,
            style=map_style,
        )

    if 'categoria_perdidas' in gdf.columns:
        gdf['color_hex'] = gdf['categoria_perdidas'].map(mapa_colores)
    else:
        gdf['color_hex'] = None

    gdf['color_hex'] = gdf['color_hex'].fillna('#9CA3AF')

    minx, miny, maxx, maxy = gdf.total_bounds

    if minx == maxx and miny == maxy:
        limites_mapa = [
            [float(miny) - 0.01, float(minx) - 0.01],
            [float(maxy) + 0.01, float(maxx) + 0.01],
        ]
    else:
        limites_mapa = [
            [float(miny), float(minx)],
            [float(maxy), float(maxx)],
        ]

    datos_geojson = json.loads(gdf.to_json())

    return dl.Map(
        [
            dl.TileLayer(url=tile_url, attribution=tile_attr),
            dl.GeoJSON(
                data=datos_geojson,
                options=dict(style=estilo_poligonos),
                hoverStyle=dict(weight=3, color='#0078D4', dashArray=''),
                id="capa-sectores-leaflet",
                children=[dl.Tooltip(id="tooltip-mapa")],
            ),
        ],
        id="mapa-principal",
        center=[4.6097, -74.0817],
        zoom=12,
        bounds=limites_mapa,
        boundsOptions={"padding": [20, 20]},
        style=map_style,
    )
