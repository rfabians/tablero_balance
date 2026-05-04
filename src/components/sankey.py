import json
import hashlib
from dash import html
import pandas as pd


# ---------------------------------------------------------------------------
# Colores semánticos para balance de pérdidas de agua (acueducto)
# ---------------------------------------------------------------------------
_COLOR_OVERRIDES = [
    ("volumen total",     "#74c0fc"),
    ("agua no facturada", "#f03e3e"),
    ("no facturada",      "#f03e3e"),
    ("agua facturada",    "#2f9e44"),
    ("facturada",         "#2f9e44"),
    ("real",              "#e8590c"),
    ("física",            "#e8590c"),
    ("fisica",            "#e8590c"),
    ("fuga",              "#e8590c"),
    ("rotura",            "#e8590c"),
    ("rebose",            "#e8590c"),
    ("aparen",            "#7048e8"),
    ("comerc",            "#7048e8"),
    ("hurto",             "#7048e8"),
    ("ilegal",            "#7048e8"),
    ("medición",          "#7048e8"),
    ("medicion",          "#7048e8"),
    ("no medida",         "#f59f00"),
    ("medida",            "#1971c2"),
    ("servicio propio",   "#0c8599"),
    ("uso propio",        "#0c8599"),
    ("incendio",          "#c92a2a"),
]

_PALETTE_FALLBACK = [
    "#4dabf7", "#38d9a9", "#ff8787", "#fcc419",
    "#b197fc", "#ff922b", "#69db7c", "#f06595",
    "#66d9e8", "#a9e34b", "#da77f2", "#ffa94d",
]


def _color_for(name: str) -> str:
    key = name.lower().strip()
    for pattern, color in _COLOR_OVERRIDES:
        if pattern in key:
            return color
    idx = int(hashlib.md5(name.encode("utf-8")).hexdigest(), 16) % len(_PALETTE_FALLBACK)
    return _PALETTE_FALLBACK[idx]


# ---------------------------------------------------------------------------
# Generador principal
# ---------------------------------------------------------------------------

def generar_sankey(df):
    """
    Sankey con Apache ECharts (iframe).
    Niveles: Volumen Total → nivel0 → nivel1 → nivel2 → nivel3_cra → descripcion
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

    # depth de cada nivel; el último recibe +2 extra → gap triple con el anterior
    # (cada +1 duplica el espacio; +2 lo cuadruplica respecto al gap base)
    level_to_depth = {col: idx for idx, col in enumerate(columnas_niveles)}
    level_to_depth[ultimo_nivel] = len(columnas_niveles) + 1   # 5 → 7

    # 1. Construir nodos y enlaces
    nodes_seen = {}
    nodes_list = []
    links = []

    def add_node(name, level_col):
        if name not in nodes_seen:
            nodes_seen[name] = True
            nodes_list.append({
                "name":      name,
                "depth":     level_to_depth[level_col],
                "itemStyle": {"color": _color_for(name)}
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
            links.append({"source": src, "target": tgt, "value": float(row["volumen"])})

    if not links:
        return html.Div(
            "No hay datos para mostrar",
            style={"color": "#adb5bd", "textAlign": "center", "padding": "40px"}
        )

    # 2. Altura: la mitad de la fórmula anterior
    n_ultimo = df_sankey[ultimo_nivel].dropna().nunique()
    height   = max(220, (n_ultimo * 36 + 60) // 2)

    # 3. Opciones ECharts (funciones JS se inyectan después, JSON no las soporta)
    option = {
        "backgroundColor": "transparent",
        "tooltip": {"show": False},
        "series": [{
            "type": "sankey",
            "data": nodes_list,
            "links": links,
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

    # Formateador: valores numéricos → M m³ / k m³ / m³
    js_fmt = """
function fmtVal(v) {
    if (v >= 1e6) return (v / 1e6).toFixed(2) + ' M m\u00b3';
    if (v >= 1e3) return (v / 1e3).toFixed(1) + ' k m\u00b3';
    return v.toFixed(0) + ' m\u00b3';
}
option.series[0].label.formatter = function(p) {
    return fmtVal(p.value) + '  ' + p.name;
};
"""

    # 4. HTML completo para el Iframe
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