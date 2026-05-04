import plotly.graph_objects as go
from dash import dcc
import pandas as pd

def generar_sankey(df):
    """
    Genera un diagrama Sankey con un diseño minimalista, moderno y altamente estético.
    - Agrega un nodo raíz "Volumen Total".
    - Usa la columna 'descripcion' para las etiquetas del último nivel.
    - Deja espacio a la derecha para las etiquetas.
    """
    if df is None or df.empty:
        return dcc.Graph(figure=go.Figure(layout={"annotations": [{"text": "No hay datos para mostrar", "showarrow": False, "font": {"size": 16, "family": "system-ui, sans-serif", "color": "#adb5bd"}}]}))

    # Preprocesamiento: Crear el "Volumen Total" como origen maestro
    df_sankey = df.copy()
    df_sankey['Volumen Total'] = 'Volumen Total'
    
    columnas_niveles = ['Volumen Total', 'nivel0', 'nivel1', 'nivel2', 'nivel3_cra', 'nivel3_eaab']
    for col in columnas_niveles:
        if col not in df_sankey.columns:
            df_sankey[col] = 'Sin ' + col

    # 1. Construir las conexiones (source, target, value)
    links = []
    def agrupar_niveles(df_sub, fuente, destino):
        df_val = df_sub.dropna(subset=[fuente, destino, 'volumen'])
        agrupado = df_val.groupby([fuente, destino], as_index=False)['volumen'].sum()
        agrupado = agrupado[agrupado['volumen'] > 0].copy()
        if agrupado.empty:
            return pd.DataFrame(columns=['source_name', 'target_name', 'volumen'])
        agrupado['source_name'] = fuente + ": " + agrupado[fuente].astype(str)
        agrupado['target_name'] = destino + ": " + agrupado[destino].astype(str)
        return agrupado[['source_name', 'target_name', 'volumen']]

    for i in range(len(columnas_niveles) - 1):
        links.append(agrupar_niveles(df_sankey, columnas_niveles[i], columnas_niveles[i+1]))

    df_links = pd.concat(links, ignore_index=True)

    if df_links.empty:
        return dcc.Graph(figure=go.Figure(layout={"annotations": [{"text": "No hay datos para mostrar", "showarrow": False, "font": {"size": 16, "family": "system-ui, sans-serif", "color": "#adb5bd"}}]}))

    # 2. Procesar Nodos
    all_node_names = pd.concat([df_links['source_name'], df_links['target_name']]).unique()
    df_nodes = pd.DataFrame({'full_name': all_node_names})
    df_nodes['level'] = df_nodes['full_name'].apply(lambda x: x.split(": ", 1)[0])
    df_nodes['label_code'] = df_nodes['full_name'].apply(lambda x: x.split(": ", 1)[1])

    # Mapa de descripción para el último nivel
    if 'descripcion' in df.columns and 'nivel3_eaab' in df.columns:
        descripcion_map = df.drop_duplicates(subset=['nivel3_eaab']).set_index('nivel3_eaab')['descripcion'].to_dict()
    else:
        descripcion_map = {}

    def get_final_label(row):
        if row['level'] == 'nivel3_eaab':
            return descripcion_map.get(row['label_code'], row['label_code'])
        return row['label_code']

    df_nodes['label'] = df_nodes.apply(get_final_label, axis=1)
    
    incoming = df_links.groupby('target_name')['volumen'].sum().rename('incoming')
    outgoing = df_links.groupby('source_name')['volumen'].sum().rename('outgoing')
    df_nodes = df_nodes.join(incoming, on='full_name').join(outgoing, on='full_name').fillna(0)
    df_nodes['value'] = df_nodes[['incoming', 'outgoing']].max(axis=1)
    
    def format_volume(v):
        if v >= 1_000_000: return f"{v/1_000_000:,.1f}M"
        elif v >= 1_000: return f"{v/1_000:,.0f}k"
        return f"{v:,.0f}"

    df_nodes['display_label'] = df_nodes.apply(lambda row: f"{row['label']} ({format_volume(row['value'])})", axis=1)

    # 3. Asignar colores
    color_palette = ['#4dabf7', '#38d9a9', '#ff8787', '#fcc419', '#b197fc', '#ff922b', '#69db7c', '#f06595']
    unique_labels = df_nodes['label'].unique()
    color_map = {label: '#868e96' if label == 'Volumen Total' else color_palette[i % len(color_palette)] for i, label in enumerate(unique_labels)}
    df_nodes['color'] = df_nodes['label'].map(color_map)

    # 4. Mapear a índices para Plotly
    node_map = {name: i for i, name in enumerate(df_nodes['full_name'])}
    df_links['source_idx'] = df_links['source_name'].map(node_map)
    df_links['target_idx'] = df_links['target_name'].map(node_map)

    source_colors = df_links['source_name'].map(df_nodes.set_index('full_name')['color'])
    link_colors = [f"rgba({int(c[1:3], 16)}, {int(c[3:5], 16)}, {int(c[5:7], 16)}, 0.35)" for c in source_colors]

    # 5. Crear figura Sankey
    fig = go.Figure(data=[go.Sankey(
        arrangement='snap',
        node=dict(
            pad=30, thickness=8, line=dict(color="rgba(0,0,0,0)", width=0),
            label=df_nodes['display_label'],
            color=df_nodes['color'],
            hovertemplate='<b>%{label}</b><br>Total: %{value:,.0f} m³<extra></extra>'
        ),
        link=dict(
            source=df_links['source_idx'], target=df_links['target_idx'], value=df_links['volumen'],
            color=link_colors,
            hovertemplate='<b>%{source.label}</b> ➔ <b>%{target.label}</b><br>Volumen: %{value:,.0f} m³<extra></extra>'
        )
    )])

    fig.update_layout(
        font=dict(family="system-ui, sans-serif", size=12, color="#495057"),
        margin=dict(l=10, r=200, t=20, b=20), # Margen derecho aumentado
        height=500,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)'
    )

    return dcc.Graph(figure=fig, style={"width": "100%", "height": "100%"}, config={'displayModeBar': False})
