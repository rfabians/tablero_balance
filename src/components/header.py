import dash_mantine_components as dmc
import pandas as pd
from dash import html
from dash_iconify import DashIconify

from models import FiltrosTablero


_LOGO_URL = "/assets/logo-acueducto.png"


def _get_val(val):
    """Extrae el primer elemento si es lista, o devuelve el valor directo."""
    if isinstance(val, list):
        return val[0] if val else None
    return val


def _opciones_filtro(df_filtrado: pd.DataFrame, columna: str, valor_actual) -> list:
    """
    Devuelve opciones únicas de una columna (sin 'M'),
    garantizando que el valor actualmente seleccionado esté incluido.
    """
    opciones = sorted(str(v) for v in df_filtrado[columna].unique() if v != "M" and str(v) != "nan")
    val = _get_val(valor_actual)
    if val and val != "M" and val not in opciones:
        opciones.append(val)
    return opciones


def crear_encabezado(
    filtro_actual: FiltrosTablero,
    df: pd.DataFrame,
    titulo: str = "Balance Hídrico",
    color_fondo: str = "#FFFFFF",
) -> dmc.AppShellHeader:
    """Retorna el AppShellHeader con filtros y branding de EAAB — estilo WinUI claro."""

    # Aplicar filtros activos para calcular opciones disponibles
    df_fil = df
    if filtro_actual.mes:
        meses = filtro_actual.mes if isinstance(filtro_actual.mes, list) else [filtro_actual.mes]
        df_fil = df_fil[df_fil["mescalculo"].isin(meses)]
    if filtro_actual.aps:
        aps_l = filtro_actual.aps if isinstance(filtro_actual.aps, list) else [filtro_actual.aps]
        df_fil = df_fil[df_fil["aps"].isin(aps_l)]
    if filtro_actual.zona:
        zonas = filtro_actual.zona if isinstance(filtro_actual.zona, list) else [filtro_actual.zona]
        df_fil = df_fil[df_fil["zona"].isin(zonas)]
    if filtro_actual.sector:
        sectores = [str(s) for s in (
            filtro_actual.sector if isinstance(filtro_actual.sector, list) else [filtro_actual.sector]
        )]
        df_fil = df_fil[df_fil["sector_hidraulico"].astype(str).isin(sectores)]

    meses_opc    = _opciones_filtro(df_fil, "mescalculo", filtro_actual.mes)
    aps_opc      = _opciones_filtro(df_fil, "aps",        filtro_actual.aps)
    zonas_opc    = _opciones_filtro(df_fil, "zona",       filtro_actual.zona)
    sectores_opc = _opciones_filtro(
        df_fil.assign(sector_hidraulico=df_fil["sector_hidraulico"].astype(str)),
        "sector_hidraulico", filtro_actual.sector,
    )

    select_style = {
        "minWidth": 120, "maxWidth": 180, "flex": "1 1 120px",
    }

    filtros = dmc.Group(
        gap="xs",
        wrap="nowrap",
        children=[
            dmc.Select(
                id="filtro-mes",
                placeholder="Mes",
                clearable=False,
                allowDeselect=False,
                value=_get_val(filtro_actual.mes),
                data=meses_opc,
                size="sm", variant="default", radius="md",
                style=select_style,
                leftSection=DashIconify(icon="tabler:calendar", height=15, color="#0078D4"),
            ),
            dmc.Select(
                id="filtro-aps",
                placeholder="APS",
                clearable=True,
                value=_get_val(filtro_actual.aps),
                data=aps_opc,
                size="sm", variant="default", radius="md",
                style=select_style,
                leftSection=DashIconify(icon="tabler:building", height=15, color="#107C10"),
            ),
            dmc.Select(
                id="filtro-zona",
                placeholder="Zona",
                clearable=True,
                value=_get_val(filtro_actual.zona),
                data=zonas_opc,
                size="sm", variant="default", radius="md",
                style=select_style,
                leftSection=DashIconify(icon="tabler:map-pin", height=15, color="#D83B01"),
            ),
            dmc.Select(
                id="filtro-sector",
                placeholder="Sector",
                clearable=True,
                value=_get_val(filtro_actual.sector),
                data=sectores_opc,
                size="sm", variant="default", radius="md",
                style=select_style,
                leftSection=DashIconify(icon="tabler:hexagon", height=15, color="#0078D4"),
            ),
            dmc.Button(
                "Limpiar",
                id="btn-limpiar-filtros",
                variant="light",
                color="blue",
                size="sm",
                radius="md",
                leftSection=DashIconify(icon="tabler:filter-off", height=15),
                style={"flexShrink": 0, "fontWeight": "600", "fontSize": "13px"},
            ),
        ],
    )

    return dmc.AppShellHeader(
        dmc.Group(
            justify="space-between",
            align="center",
            h="100%",
            px="md",
            wrap="nowrap",
            children=[
                # Branding
                dmc.Group(
                    gap="sm",
                    align="center",
                    wrap="nowrap",
                    style={"flexShrink": 0},
                    children=[
                        html.Div(
                            html.Img(src=_LOGO_URL, style={
                                "height": 36, "width": "auto",
                                "display": "block",
                            }),
                            style={
                                "background": "#0D2240",
                                "borderRadius": "8px",
                                "padding": "5px 10px",
                                "lineHeight": 0,
                            },
                        ),
                        html.Div(style={
                            "width": "1px", "height": "32px",
                            "background": "#E1E5EA", "margin": "0 4px",
                        }),
                        dmc.Stack(
                            gap=2,
                            align="flex-start",
                            children=[
                                dmc.Text(
                                    titulo,
                                    fw=700,
                                    size="md",
                                    style={"color": "#0078D4", "letterSpacing": "0.3px"},
                                ),
                                dmc.Text(
                                    "Gerencia Corporativa Analítica y Pérdidas",
                                    fw=400,
                                    size="xs",
                                    style={"color": "#5E5E5E"},
                                    visibleFrom="sm",
                                ),
                            ],
                        ),
                    ],
                ),
                # Filtros
                dmc.ScrollArea(
                    type="never",
                    style={"flex": 1, "minWidth": 0},
                    children=html.Div(
                        filtros,
                        style={"paddingLeft": 16, "paddingRight": 4},
                    ),
                ),
            ],
        ),
        bg=color_fondo,
        style={
            "borderBottom": "1px solid #E1E5EA",
            "boxShadow": "0 1px 4px rgba(0,0,0,0.06)",
        },
    )
