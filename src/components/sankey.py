import json
import hashlib
from collections import defaultdict, deque
from dash import html
import pandas as pd


# ---------------------------------------------------------------------------
# Paleta base — colores raíz por rama semántica
# Se aplican por subcadena (case-insensitive) sobre el nombre del nodo.
# Los nodos que no coincidan heredan el color de su ancestro nivel0.
# ---------------------------------------------------------------------------
_COLOR_OVERRIDES = [
    # Raíz
    ("volumen total",       "#74c0fc"),   # azul agua

    # nivel0 — dos grandes bloques
    ("agua no facturada",   "#e03131"),   # rojo — pérdidas
    ("no facturada",        "#e03131"),
    ("agua facturada",      "#2f9e44"),   # verde — ingreso
    ("facturada",           "#2f9e44"),
]

# Paleta de respaldo (nodos que no coincidan con ningún override NI tengan ancestro)
_FALLBACK = [
    "#4dabf7", "#38d9a9", "#ff8787", "#fcc419",
    "#b197fc", "#ff922b", "#69db7c", "#f06595",
]


def _match_override(name: str):
    """Retorna el color del primer patrón que coincida, o None."""
    key = name.lower().strip()
    for pattern, color in _COLOR_OVERRIDES:
        if pattern in key:
            return color
    return None


def _hash_color(name: str) -> str:
    idx = int(hashlib.md5(name.encode("utf-8")).hexdigest(), 16) % len(_FALLBACK)
    return _FALLBACK[idx]


def _lighten(hex_color: str, amount: float) -> str:
    """Aclara un color hex mezclándolo con blanco (amount ∈ [0,1])."""
    r = int(hex_color[1:3], 16)
    g = int(hex_color[3:5], 16)
    b = int(hex_color[5:7], 16)
    r = min(255, int(r + (255 - r) * amount))
    g = min(255, int(g + (255 - g) * amount))
    b = min(255, int(b + (255 - b) * amount))
    return f"#{r:02x}{g:02x}{b:02x}"


# ---------------------------------------------------------------------------
# Generador principal
# ---------------------------------------------------------------------------

def generar_sankey(df):
    """
    Sankey con Apache ECharts (iframe).
    Niveles: Volumen Total → nivel0 → nivel1 → nivel2 → nivel3_cra → descripcion
    Colores: herencia BFS desde nivel0; aclaramiento proporcional a la profundidad.
    """
    if df is None or df.empty:
        return html.Div(
            "No hay datos para mostrar",
            style={"color": "#adb5bd", "textAlign": "center", "padding": "40px",
                   "fontFamily": "system-ui, sans-serif"}
        )

    df_sankey = df.copy()
    df_sankey["Volumen Total"] = "Volumen Total"

    ultimo_nivel = "descripcion" if "descripcion" in df_sankey.columns else "nivel3_eaab"
    columnas_niveles = ["Volumen Total", "nivel0", "nivel1", "nivel2", "nivel3_cra", ultimo_nivel]

    for col in columnas_niveles:
        if col not in df_sankey.columns:
            df_sankey[col] = "Sin " + col

    # depth de cada nivel; último recibe +2 → gap triple con el penúltimo
    level_to_depth = {col: idx for idx, col in enumerate(columnas_niveles)}
    level_to_depth[ultimo_nivel] = len(columnas_niveles) + 1   # 5 → 7

    # -----------------------------------------------------------------------
    # 1. Construir nodos (con color placeholder) y enlaces
    # -----------------------------------------------------------------------
    nodes_seen    = {}    # name → index in nodes_list
    nodes_list    = []
    links         = []
    adj           = defaultdict(list)   # source_name → [target_names]
    has_semantic  = set()               # nodos con color semántico propio

    def add_node(name, level_col):
        if name not in nodes_seen:
            nodes_seen[name] = len(nodes_list)
            color = _match_override(name)
            if color:
                has_semantic.add(name)
            else:
                color = "#cccccc"       # placeholder; se reasigna en el BFS
            nodes_list.append({
                "name":      name,
                "depth":     level_to_depth[level_col],
                "itemStyle": {"color": color}
            })

    for i in range(len(columnas_niveles) - 1):
        fuente  = columnas_niveles[i]
        destino = columnas_niveles[i + 1]
        df_val  = df_sankey.dropna(subset=[fuente, destino, "volumen"])
        agrupado = (
            df_val.groupby([fuente, destino], as_index=False)["volumen"]
            .sum()
            .pipe(lambda x: x[x["volumen"] > 0])
        )
        for _, row in agrupado.iterrows():
            src = str(row[fuente])
            tgt = str(row[destino])
            add_node(src, fuente)
            add_node(tgt, destino)
            adj[src].append(tgt)
            links.append({"source": src, "target": tgt, "value": float(row["volumen"])})

    if not links:
        return html.Div(
            "No hay datos para mostrar",
            style={"color": "#adb5bd", "textAlign": "center", "padding": "40px"}
        )

    # -----------------------------------------------------------------------
    # 2. BFS: propagar color del ancestro nivel0 a todos sus descendientes
    #    El aclaramiento es proporcional a la profundidad relativa al nivel0.
    # -----------------------------------------------------------------------
    node_by_name = {n["name"]: n for n in nodes_list}

    # Primero: encontrar el color del ancestro nivel0 para cada nodo
    nivel0_ancestor = {}   # node_name → color del nivel0 que lo originó

    # Sembrar con los nodos de nivel0 (depth=1)
    queue = deque()
    for n in nodes_list:
        if n["depth"] == 1:
            nivel0_ancestor[n["name"]] = n["itemStyle"]["color"]
            queue.append(n["name"])

    visited = set(nivel0_ancestor.keys())
    while queue:
        cur = queue.popleft()
        anc_color = nivel0_ancestor[cur]
        for tgt in adj[cur]:
            if tgt not in visited:
                nivel0_ancestor[tgt] = anc_color
                visited.add(tgt)
                queue.append(tgt)

    # Reasignar colores: semánticos se mantienen; el resto hereda con aclaramiento
    MAX_DEPTH = level_to_depth[ultimo_nivel]
    for n in nodes_list:
        if n["name"] in has_semantic:
            continue                        # color semántico definido: se conserva
        anc = nivel0_ancestor.get(n["name"])
        if anc:
            depth    = n["depth"]
            amount   = min(0.55, (depth - 1) * 0.13)   # hasta 55 % más claro
            n["itemStyle"]["color"] = _lighten(anc, amount)
        else:
            n["itemStyle"]["color"] = _hash_color(n["name"])

    # -----------------------------------------------------------------------
    # 3. Altura dinámica
    # -----------------------------------------------------------------------
    n_ultimo = df_sankey[ultimo_nivel].dropna().nunique()
    height   = max(220, (n_ultimo * 36 + 60) // 2)

    # -----------------------------------------------------------------------
    # 4. Opciones ECharts
    # -----------------------------------------------------------------------
    # levels → tamaño de fuente diferente por profundidad
    levels_cfg = [
        {"depth": 0, "label": {"fontSize": 12, "fontWeight": "bold"}},
        {"depth": 1, "label": {"fontSize": 12, "fontWeight": "bold"}},
        {"depth": 2, "label": {"fontSize": 10}},
        {"depth": 3, "label": {"fontSize": 10}},
        {"depth": 4, "label": {"fontSize": 10}},
        {"depth": 5, "label": {"fontSize": 10}},
        {"depth": 6, "label": {"fontSize": 10}},
        {"depth": 7, "label": {"fontSize": 11}},
    ]

    option = {
        "backgroundColor": "transparent",
        "tooltip": {"show": False},
        "series": [{
            "type": "sankey",
            "data": nodes_list,
            "links": links,
            "levels": levels_cfg,
            "orient": "horizontal",
            "nodeWidth": 10,
            "nodeGap": 14,
            "layoutIterations": 64,
            "emphasis": {"focus": "adjacency"},
            "left":   "1%",
            "right":  "26%",
            "top":    "3%",
            "bottom": "3%",
            "label": {
                "show": True,
                "position": "right",
                "fontFamily": "system-ui, sans-serif",
                "fontSize": 11,
                "color": "#495057"
            },
            "lineStyle": {
                "color": "source",
                "opacity": 0.3,
                "curveness": 0.5
            },
            "itemStyle": {"borderWidth": 0}
        }]
    }

    # Formateador JS: truncado por nivel + valores en M/k
    js_fmt = """
function fmtVal(v) {
    if (v >= 1e6) return (v / 1e6).toFixed(2) + ' M m\u00b3';
    if (v >= 1e3) return (v / 1e3).toFixed(1) + ' k m\u00b3';
    return v.toFixed(0) + ' m\u00b3';
}
option.series[0].label.formatter = function(p) {
    var depth  = p.data ? p.data.depth : 0;
    var name   = p.name;
    var maxLen = (depth <= 1) ? 50 : (depth >= 7) ? 45 : 18;
    if (name.length > maxLen) name = name.substring(0, maxLen) + '\u2026';
    return fmtVal(p.value) + '  ' + name;
};
"""

    # -----------------------------------------------------------------------
    # 5. HTML completo para el Iframe
    # -----------------------------------------------------------------------
    html_doc = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<script src="https://cdn.jsdelivr.net/npm/echarts@5.4.3/dist/echarts.min.js"></script>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ background: transparent; overflow: hidden; }}
#chart {{ width: 100%; height: {height}px; }}
</style>
</head>
<body>
<div id="chart"></div>
<script>
var chart = echarts.init(document.getElementById('chart'), null, {{ renderer: 'canvas' }});
var option = {json.dumps(option, ensure_ascii=False)};
{js_fmt}
chart.setOption(option);
window.addEventListener('resize', function () {{ chart.resize(); }});
</script>
</body>
</html>"""

    return html.Iframe(
        srcDoc=html_doc,
        style={
            "width":   "100%",
            "height":  f"{height}px",
            "border":  "none",
            "display": "block"
        }
    )