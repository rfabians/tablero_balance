import dash_leaflet as dl
import json
from dash_extensions.javascript import assign

estilo_poligonos = assign("""function(feature, context){
    return {
        fillColor: feature.properties.color_hex, 
        color: "white",       // Borde del polígono
        weight: 1.5,          // Grosor del borde
        fillOpacity: 0.6      // Transparencia (0 a 1)
    };
}""")


def generar_mapa_leaflet(gdf):
    """
    Recibe un GeoDataFrame, asigna colores categóricos y retorna un mapa de Leaflet centrado.
    """
    mapa_colores = {
        'IPUF BAJO': '#22c55e',  # Verde
        'IPUF MEDIO': '#eab308',  # Amarillo
        'IPUF ALTO': '#ef4444'  # Rojo
    }

    if gdf is None or gdf.empty:
        # Fallback explícito seguro
        return dl.Map(
            [dl.TileLayer()],
            id="mapa-principal",
            center=[4.6097, -74.0817],
            zoom=12,
            style={'height': '75vh', 'width': '100%', 'borderRadius': '8px'}
        )

    # Asignamos los colores
    if 'categoria_perdidas' in gdf.columns:
        gdf['color_hex'] = gdf['categoria_perdidas'].map(mapa_colores)
    else:
        gdf['color_hex'] = None
        
    gdf['color_hex'] = gdf['color_hex'].fillna('#9ca3af')

    minx, miny, maxx, maxy = gdf.total_bounds
    
    # Prevenir errores si se filtra a un solo punto o geometrías sin área
    if minx == maxx and miny == maxy:
        limites_mapa = [[float(miny) - 0.01, float(minx) - 0.01], [float(maxy) + 0.01, float(maxx) + 0.01]]
    else:
        limites_mapa = [[float(miny), float(minx)], [float(maxy), float(maxx)]]

    datos_geojson = json.loads(gdf.to_json())

    mapa = dl.Map(
        [
            dl.TileLayer(
                url="https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png",
                attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>'
            ),
            dl.GeoJSON(
                data=datos_geojson,
                options=dict(
                    style=estilo_poligonos
                ),
                hoverStyle=dict(weight=3, color='#666', dashArray=''),
                id="capa-sectores-leaflet",
                children=[dl.Tooltip(id="tooltip-mapa")] 
            )
        ],
        id="mapa-principal",
        # REGLA ORO DE LEAFLET: Todo mapa necesita un center y zoom explícito al iniciar
        # Aún si usas bounds o viewport.
        center=[4.6097, -74.0817],
        zoom=11,
        # Mantener solo bounds en la creación inicial es más seguro
        bounds=limites_mapa,
        style={'height': '75vh', 'width': '100%', 'borderRadius': '8px', 'zIndex': 0}
    )

    return mapa
