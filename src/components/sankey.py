import json
import hashlib
from collections import defaultdict, deque
from dash import html
import pandas as pd


# ---------------------------------------------------------------------------
# Paleta base — colores WinUI claro por rama semántica
# ---------------------------------------------------------------------------
_COLOR_OVERRIDES = [
    ("volumen total",       "#0078D4"),   # Azul WinUI — entrada del sistema
    ("agua no facturada",   "#D83B01"),   # Naranja-rojo — pérdidas
    ("no facturada",        "#D83B01"),
    ("agua facturada",      "#107C10"),   # Verde WinUI — ingreso
    ("facturada",           "#107C10"),
]

_FALLBACK = [
    "#0078D4", "#107C10", "#D83B01", "#FF8C00",
    "#744DA9", "#CA5010", "#00B294", "#0063B1",
]


def _match_override(name: str):
    key = name.lower().strip()
    for pattern, color in _COLOR_OVERRIDES:
        if pattern in key:
            return color
    return None


def _hash_color(name: str) -> str:
    idx = int(hashlib.md5(name.encode("utf-8")).hexdigest(), 16) % len(_FALLBACK)
    return _FALLBACK[idx]


def _lighten(hex_color: str, amount: float) -> str:
    r = int(hex_color[1:3], 16)
    g = int(hex_color[3:5], 16)
    b = int(hex_color[5:7], 16)
    r = min(255, int(r + (255 - r) * amount))
    g = min(255, int(g + (255 - g) * amount))
    b = min(255, int(b + (255 - b) * amount))
    return f"#{r:02x}{g:02x}{b:02x}"


# ---------------------------------------------------------------------------
# Bloque JS de formatters — string literal (no f-string) para que las
# llaves de JS no colisionen con la interpolación de Python.
# ---------------------------------------------------------------------------
_JS_FORMATTERS = r"""
// ── helpers ───────────────────────────────────────────────────────────────
function fmtVal(v) {
    return (v / 1e6).toFixed(3) + ' M m\u00b3';
}
function fmtPct(v) {
    if (volTotal <= 0) return '—';
    return (v / volTotal * 100).toFixed(1) + '%';
}
function truncate(s, n) {
    return s.length > n ? s.substring(0, n) + '\u2026' : s;
}

// ── label de cada nodo ─────────────────────────────────────────────────────
option.series[0].label.formatter = function(p) {
    var depth  = p.data ? p.data.depth : 0;
    var name   = p.name;
    var maxLen = depth <= 1 ? 52 : depth >= 7 ? 46 : 24;
    name = truncate(name, maxLen);
    return fmtVal(p.value) + '   ' + name;
};

// ── tooltip de nodo y arista ───────────────────────────────────────────────
option.tooltip.formatter = function(params) {
    var S = "font-family:'Segoe UI','Inter',system-ui,sans-serif;";

    // ── Arista (link) ──────────────────────────────────────────────────────
    if (params.dataType === 'edge') {
        var ev  = params.data.value;
        var src = truncate(params.data.source, 36);
        var tgt = truncate(params.data.target, 36);
        return '<div style="' + S + 'min-width:220px;max-width:320px;word-break:break-word;overflow-wrap:break-word">'
             + '<div style="font-size:11px;color:#5E5E5E;margin-bottom:5px;white-space:normal;word-break:break-word">'
             +     src + ' &rarr; ' + tgt
             + '</div>'
             + '<div style="font-size:17px;font-weight:700;color:#1A1D1E;line-height:1.2">'
             +     fmtVal(ev)
             + '</div>'
             + '<div style="font-size:15px;font-weight:600;color:#0078D4;margin-top:1px">'
             +     fmtPct(ev) + ' del total'
             + '</div>'
             + '</div>';
    }

    // ── Nodo ──────────────────────────────────────────────────────────────
    var name     = params.name;
    var val      = params.value;
    var pct      = fmtPct(val);
    var children = (outMap[name] || []).slice(0, 8);

    // Color del badge de porcentaje — semántico por magnitud
    var pctNum   = volTotal > 0 ? val / volTotal * 100 : 0;
    var badgeClr = pctNum >= 40 ? '#0078D4' : pctNum >= 15 ? '#107C10' : '#D83B01';

    var html = '<div style="' + S + 'min-width:270px;max-width:360px;word-break:break-word;overflow-wrap:break-word">'
             // cabecera
             + '<div style="font-weight:700;font-size:14px;color:#1A1D1E;'
             +   'border-bottom:2px solid ' + badgeClr + ';padding-bottom:7px;margin-bottom:9px;'
             +   'white-space:normal;word-break:break-word;overflow-wrap:break-word">'
             +   name
             + '</div>'
             // fila volumen + porcentaje
             + '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:3px">'
             +   '<span style="color:#5E5E5E;font-size:12px">Volumen</span>'
             +   '<span style="font-weight:600;color:#1A1D1E;font-size:13px">' + fmtVal(val) + '</span>'
             + '</div>'
             + '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px">'
             +   '<span style="color:#5E5E5E;font-size:12px">Participación del total</span>'
             +   '<span style="font-weight:700;font-size:20px;color:' + badgeClr + ';line-height:1">' + pct + '</span>'
             + '</div>';

    // barra de contexto del nodo actual
    var selfW = Math.max(2, Math.round(pctNum));
    html += '<div style="background:#F0F2F5;height:6px;border-radius:3px;margin-bottom:10px;overflow:hidden">'
          +   '<div style="background:' + badgeClr + ';height:6px;border-radius:3px;width:' + selfW + '%"></div>'
          + '</div>';

    // hijos
    if (children.length > 0) {
        html += '<div style="border-top:1px solid #E8ECF0;padding-top:8px">'
              + '<div style="font-size:10px;font-weight:700;color:#8A8A8A;'
              +   'text-transform:uppercase;letter-spacing:0.7px;margin-bottom:7px">Flujo hacia</div>';

        children.forEach(function(c) {
            var cName = truncate(c.target, 40);
            var cPct  = fmtPct(c.value);
            var cPctN = volTotal > 0 ? c.value / volTotal * 100 : 0;
            // barra relativa al nodo padre (visual), texto = % del total
            var barW  = Math.max(2, Math.round(c.value / val * 100));
            var cClr  = cPctN >= 40 ? '#0078D4' : cPctN >= 15 ? '#107C10' : '#FF8C00';

            html += '<div style="margin-bottom:7px">'
                  +   '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:3px">'
                  +     '<span style="font-size:12px;color:#323232;flex:1;margin-right:10px">' + cName + '</span>'
                  +     '<span style="font-size:13px;font-weight:700;color:' + cClr + ';white-space:nowrap">' + cPct + '</span>'
                  +   '</div>'
                  +   '<div style="background:#F0F2F5;height:5px;border-radius:3px;overflow:hidden">'
                  +     '<div style="background:' + cClr + ';height:5px;border-radius:3px;width:' + barW + '%"></div>'
                  +   '</div>'
                  + '</div>';
        });

        html += '</div>';
    }

    html += '</div>';
    return html;
};
"""


# ---------------------------------------------------------------------------
# Generador principal
# ---------------------------------------------------------------------------

def generar_sankey(df):
    """
    Sankey con Apache ECharts (iframe) — estilo WinUI claro.
    Niveles: Volumen Total → nivel0 → nivel1 → nivel2 → nivel3_cra → descripcion
    Tooltip: % de participación sobre el volumen total + mini barras de distribución.
    """
    if df is None or df.empty:
        return html.Div(
            "No hay datos para mostrar",
            style={"color": "#5E5E5E", "textAlign": "center", "padding": "40px",
                   "fontFamily": "'Segoe UI', 'Inter', system-ui, sans-serif"}
        )

    df_sankey = df.copy()
    df_sankey["Volumen Total"] = "Volumen Total"

    ultimo_nivel = "descripcion" if "descripcion" in df_sankey.columns else "nivel3_eaab"
    columnas_niveles = ["Volumen Total", "nivel0", "nivel1", "nivel2", "nivel3_cra", ultimo_nivel]

    for col in columnas_niveles:
        if col not in df_sankey.columns:
            df_sankey[col] = "Sin " + col

    level_to_depth = {col: idx for idx, col in enumerate(columnas_niveles)}
    level_to_depth[ultimo_nivel] = len(columnas_niveles) + 1

    # -----------------------------------------------------------------------
    # 1. Nodos y enlaces
    # -----------------------------------------------------------------------
    nodes_seen   = {}
    nodes_list   = []
    links        = []
    adj          = defaultdict(list)
    has_semantic = set()

    def add_node(name, level_col):
        if name not in nodes_seen:
            nodes_seen[name] = len(nodes_list)
            color = _match_override(name)
            if color:
                has_semantic.add(name)
            else:
                color = "#cccccc"
            nodes_list.append({
                "name":      name,
                "depth":     level_to_depth[level_col],
                "itemStyle": {"color": color},
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
            style={"color": "#5E5E5E", "textAlign": "center", "padding": "40px"}
        )

    # -----------------------------------------------------------------------
    # 2. BFS: propagar color del ancestro nivel0
    # -----------------------------------------------------------------------
    nivel0_ancestor = {}
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

    for n in nodes_list:
        if n["name"] in has_semantic:
            continue
        anc = nivel0_ancestor.get(n["name"])
        if anc:
            amount = min(0.50, (n["depth"] - 1) * 0.12)
            n["itemStyle"]["color"] = _lighten(anc, amount)
        else:
            n["itemStyle"]["color"] = _hash_color(n["name"])

    # -----------------------------------------------------------------------
    # 3. Datos para el tooltip (Python → JS)
    # -----------------------------------------------------------------------
    vol_total_js = sum(lnk["value"] for lnk in links if lnk["source"] == "Volumen Total")
    if vol_total_js == 0:
        vol_total_js = 1.0

    out_map: dict[str, list] = defaultdict(list)
    for lnk in links:
        out_map[lnk["source"]].append({"target": lnk["target"], "value": lnk["value"]})
    out_map_sorted = {k: sorted(v, key=lambda x: -x["value"]) for k, v in out_map.items()}

    # Variables JS que requieren valores de Python (f-string seguro: sin llaves JS)
    js_vars = (
        f"var volTotal = {vol_total_js};\n"
        f"var outMap   = {json.dumps(out_map_sorted, ensure_ascii=False)};"
    )

    # -----------------------------------------------------------------------
    # 4. Altura dinámica
    # -----------------------------------------------------------------------
    n_ultimo = df_sankey[ultimo_nivel].dropna().nunique()
    height   = max(340, (n_ultimo * 44 + 100) // 2)

    # -----------------------------------------------------------------------
    # 5. Opciones ECharts
    # -----------------------------------------------------------------------
    levels_cfg = [
        {"depth": 0, "label": {"fontSize": 15, "fontWeight": "bold",  "color": "#0078D4"}},
        {"depth": 1, "label": {"fontSize": 14, "fontWeight": "bold",  "color": "#1A1D1E"}},
        {"depth": 2, "label": {"fontSize": 13, "fontWeight": "600",   "color": "#1A1D1E"}},
        {"depth": 3, "label": {"fontSize": 12, "color": "#323232"}},
        {"depth": 4, "label": {"fontSize": 12, "color": "#323232"}},
        {"depth": 5, "label": {"fontSize": 11, "color": "#5E5E5E"}},
        {"depth": 6, "label": {"fontSize": 11, "color": "#5E5E5E"}},
        {"depth": 7, "label": {"fontSize": 12, "color": "#323232"}},
    ]

    option = {
        "backgroundColor": "transparent",
        "tooltip": {
            "trigger":    "item",
            "triggerOn":  "mousemove",
            "backgroundColor": "rgba(255,255,255,0.97)",
            "borderColor": "#E1E5EA",
            "borderWidth": 1,
            "extraCssText": (
                "border-radius:10px;"
                "box-shadow:0 6px 24px rgba(0,0,0,0.13);"
                "padding:12px 16px;"
            ),
            "textStyle": {
                "fontFamily": "'Segoe UI','Inter',system-ui,sans-serif",
                "color": "#1A1D1E",
                "fontSize": 13,
            },
        },
        "series": [{
            "type":             "sankey",
            "data":             nodes_list,
            "links":            links,
            "levels":           levels_cfg,
            "orient":           "horizontal",
            "nodeWidth":        14,
            "nodeGap":          18,
            "layoutIterations": 64,
            "emphasis":         {"focus": "adjacency"},
            "left":    "1%",
            "right":   "30%",
            "top":     "4%",
            "bottom":  "4%",
            "label": {
                "show":       True,
                "position":   "right",
                "fontFamily": "'Segoe UI','Inter',system-ui,sans-serif",
                "fontSize":   12,
                "fontWeight": "500",
                "color":      "#323232",
            },
            "lineStyle": {
                "color":     "source",
                "opacity":   0.22,
                "curveness": 0.5,
            },
            "itemStyle": {"borderWidth": 0},
        }]
    }

    # -----------------------------------------------------------------------
    # 6. HTML del iframe
    # -----------------------------------------------------------------------
    html_doc = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<script src="https://cdn.jsdelivr.net/npm/echarts@5.4.3/dist/echarts.min.js"></script>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
html, body {{
  background:#FFFFFF;
  overflow:hidden;
  font-family:'Segoe UI','Inter',system-ui,sans-serif;
}}
#chart {{ width:100%; height:{height}px; }}
</style>
</head>
<body>
<div id="chart"></div>
<script>
var chart = echarts.init(
  document.getElementById('chart'), null,
  {{ renderer:'canvas', backgroundColor:'transparent' }}
);
var option = {json.dumps(option, ensure_ascii=False)};
{js_vars}
{_JS_FORMATTERS}
chart.setOption(option);
window.addEventListener('resize', function() {{ chart.resize(); }});
</script>
</body>
</html>"""

    return html.Iframe(
        srcDoc=html_doc,
        style={
            "width":   "100%",
            "height":  f"{height}px",
            "border":  "none",
            "display": "block",
        }
    )
