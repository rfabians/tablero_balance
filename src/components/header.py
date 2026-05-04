import dash_mantine_components as dmc
import pandas as pd
from dash import html
from dash_iconify import DashIconify

from models import FiltrosTablero


_LOGO_URL = (
    "https://www.acueducto.com.co/wps/portal/EAB2/Home/inicio/!ut/p/z1/"
    "hY5BCsIwEEXP4iLb5pugqLtUpCKiVARrNhJrrJG2KWlqr2_AlVBxYBbz581j"
    "qKQZlbV6mUJ5Y2tVhvksp5dpusR4BrZDegDSdL7nCT-yZMPp6R8gwxo_SiDc"
    "ywFEID6wmAPJng0CX44NlUVpr593RX3ls4JKp-_aaRd1LsQP75t2QUDQ932k8"
    "k7futzbKLdV6JA2LUFjnVclwUrEjGBtK01gapMbO-R92NbTbEhHmyrDc1K-tm"
    "I0egOHroG0/images/logo-acueducto-2021.png"
)


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
    opciones = sorted(str(v) for v in df_filtrado[columna].unique() if v != "M")
    val = _get_val(valor_actual)
    if val and val != "M" and val not in opciones:
        opciones.append(val)
    return opciones


def crear_encabezado(
    filtro_actual: FiltrosTablero,
    df: pd.DataFrame,
    titulo: str = "Balance Hídrico",
    color_fondo: str = "#001529",
) -> dmc.AppShellHeader:
    """Retorna el AppShellHeader con filtros y branding de EAAB."""

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

    select_style = {"minWidth": 130, "maxWidth": 190, "flex": "1 1 130px"}

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
                size="sm", variant="filled", radius="md",
                style=select_style,
            ),
            dmc.Select(
                id="filtro-aps",
                placeholder="APS",
                clearable=True,
                value=_get_val(filtro_actual.aps),
                data=aps_opc,
                size="sm", variant="filled", radius="md",
                style=select_style,
            ),
            dmc.Select(
                id="filtro-zona",
                placeholder="Zona",
                clearable=True,
                value=_get_val(filtro_actual.zona),
                data=zonas_opc,
                size="sm", variant="filled", radius="md",
                style=select_style,
            ),
            dmc.Select(
                id="filtro-sector",
                placeholder="Sector",
                clearable=True,
                value=_get_val(filtro_actual.sector),
                data=sectores_opc,
                size="sm", variant="filled", radius="md",
                style=select_style,
            ),
            dmc.Button(
                "Limpiar",
                id="btn-limpiar-filtros",
                variant="white",
                color="dark",
                size="xs",
                leftSection=DashIconify(icon="tabler:filter-cancel", height=16, color=color_fondo),
                style={"flexShrink": 0},
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
                # Branding (nunca se encoge en mobile)
                dmc.Group(
                    gap="sm",
                    align="center",
                    wrap="nowrap",
                    style={"flexShrink": 0},
                    children=[
                        html.Img(src=_LOGO_URL, style={"height": 38, "width": "auto"}),
                        dmc.Stack(
                            gap=1,
                            align="flex-start",
                            children=[
                                dmc.Text(titulo, c="white", fw=700, size="md"),
                                # Subtítulo oculto en mobile para ahorrar espacio
                                dmc.Text(
                                    "Gerencia Corporativa Analítica y Pérdidas",
                                    c="white", fw=300, size="xs",
                                    visibleFrom="sm",
                                ),
                            ],
                        ),
                    ],
                ),
                # Filtros: scroll horizontal en mobile, inline en desktop
                dmc.ScrollArea(
                    type="never",
                    style={"flex": 1, "minWidth": 0},
                    children=html.Div(
                        filtros,
                        style={"paddingLeft": 10, "paddingRight": 4},
                    ),
                ),
            ],
        ),
        bg=color_fondo,
        style={"borderBottom": "none"},
    )