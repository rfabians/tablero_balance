# components/header.py
import dash_mantine_components as dmc
import pandas as pd
from dash import html
from dash_iconify import DashIconify

from models import FiltrosTablero


def crear_encabezado(filtro_actual: FiltrosTablero,
                     df: pd.DataFrame,
                     titulo="Balance Hídrico", color_fondo="#001529"):
    """
    Retorna el componente AppShellHeader configurado.
    """
    print(f'Filtro Actual {filtro_actual.__dict__}')
    
    def get_val(val):
        if isinstance(val, list):
            return val[0] if len(val) > 0 else None
        return val

    # Filtrar el DataFrame según los valores actuales del filtro
    df_filtrado = df.copy()
    if filtro_actual.mes:
        meses = filtro_actual.mes if isinstance(filtro_actual.mes, list) else [filtro_actual.mes]
        df_filtrado = df_filtrado[df_filtrado['mescalculo'].isin(meses)]
    if filtro_actual.aps:
        aps = filtro_actual.aps if isinstance(filtro_actual.aps, list) else [filtro_actual.aps]
        df_filtrado = df_filtrado[df_filtrado['aps'].isin(aps)]
    if filtro_actual.zona:
        zonas = filtro_actual.zona if isinstance(filtro_actual.zona, list) else [filtro_actual.zona]
        df_filtrado = df_filtrado[df_filtrado['zona'].isin(zonas)]
    if filtro_actual.sector:
        sectores = filtro_actual.sector if isinstance(filtro_actual.sector, list) else [filtro_actual.sector]
        sectores_str = [str(s) for s in sectores]
        df_filtrado = df_filtrado[df_filtrado['sector_hidraulico'].astype(str).isin(sectores_str)]
    
    # Calcular las opciones disponibles basadas en los datos filtrados
    # Nota: Si el usuario borra un filtro, queremos que todas las opciones originales 
    # vuelvan a estar disponibles si están dentro de los otros filtros.
    # Por eso aplicamos los filtros y luego tomamos los valores únicos de df_filtrado.

    meses_opciones = [mes for mes in df_filtrado['mescalculo'].unique() if mes != 'M']
    aps_opciones = [aps for aps in df_filtrado['aps'].unique() if aps != 'M']
    zonas_opciones = [zona for zona in df_filtrado['zona'].unique() if zona != 'M']
    sectores_opciones = [str(sector) for sector in df_filtrado['sector_hidraulico'].unique() if sector != 'M']

    # Si hay un valor seleccionado que ya no es válido, se sigue mostrando como opción
    # para evitar problemas de UI, pero normalmente esto se maneja deseleccionando o
    # simplemente actualizando el selector. Aquí agregaremos la opción seleccionada 
    # si no está para que no crashee si cambias un filtro padre.
    
    def ensure_val_in_options(val, options):
        if val is not None and val not in options and val != 'M':
            options.append(val)
        return options

    meses_opciones = ensure_val_in_options(get_val(filtro_actual.mes), meses_opciones)
    aps_opciones = ensure_val_in_options(get_val(filtro_actual.aps), aps_opciones)
    zonas_opciones = ensure_val_in_options(get_val(filtro_actual.zona), zonas_opciones)
    sectores_opciones = ensure_val_in_options(get_val(filtro_actual.sector), sectores_opciones)


    return dmc.AppShellHeader(
        dmc.Group(
            [
                dmc.Group([
                    html.Img(
                        src="https://www.acueducto.com.co/wps/portal/EAB2/Home/inicio/!ut/p/z1/hY5BCsIwEEXP4iLb5pugqLtUpCKiVARrNhJrrJG2KWlqr2_AlVBxYBbz581jqKQZlbV6mUJ5Y2tVhvksp5dpusR4BrZDegDSdL7nCT-yZMPp6R8gwxo_SiDcywFEID6wmAPJng0CX44NlUVpr593RX3ls4JKp-_aaRd1LsQP75t2QUDQ932k8k7futzbKLdV6JA2LUFjnVclwUrEjGBtK01gapMbO-R92NbTbEhHmyrDc1K-tmI0egOHroG0/images/logo-acueducto-2021.png",
                        style={"height": "40px", "width": "auto"}
                        # Ajustamos la altura para que encaje en los 60px del header
                    ),
                    dmc.Stack([
                        dmc.Text(titulo, c="white", fw=700, size="md"),
                        dmc.Text('Gerencia Corporativa Analítica y Pérdidas', c="white", fw=300, size="sm"),
                        dmc.Text('Dirección Analítica', c="white", fw=300, size="sm"),
                    ],
                        align="start",
                        gap=2,
                    ),
                ],
                    align="center",
                ),
                dmc.Group(
                    [
                        dmc.Select(
                            id="filtro-mes",
                            placeholder="Mes Calculo",
                            clearable=False,
                            allowDeselect=False,
                            value=get_val(filtro_actual.mes),
                            data=sorted(meses_opciones),
                            w=180,
                            size="sm",
                            variant="filled",
                            radius="md"
                        ),
                        dmc.Select(
                            id="filtro-aps",
                            placeholder="APS",
                            clearable=True,
                            value=get_val(filtro_actual.aps),
                            data=sorted(aps_opciones),
                            w=180,
                            size="sm",
                            variant="filled",
                            radius="md"
                        ),
                        dmc.Select(
                            id="filtro-zona",
                            placeholder="Zona",
                            clearable=True,
                            value=get_val(filtro_actual.zona),
                            data=sorted(zonas_opciones),
                            w=180,
                            size="sm",
                            variant="filled",
                            radius="md"
                        ),
                        dmc.Select(
                            id="filtro-sector",
                            placeholder="Sector",
                            clearable=True,
                            value=get_val(filtro_actual.sector),
                            data=sorted(sectores_opciones),
                            w=180,
                            size="sm",
                            variant="filled",
                            radius="md"
                        ),
                        dmc.Button(
                            "Limpiar",
                            id="btn-limpiar-filtros",
                            variant="white",
                            color="dark",
                            size="xs",
                            leftSection=DashIconify(icon="tabler:filter-cancel", height=30, color=color_fondo)
                        ),
                    ],
                    gap="md",
                ),
            ],
            justify="space-between",
            align="center",
            h="100%",
            px="xl",
        ),
        bg=color_fondo,
        # Se elimina position fixed para que dmc.AppShell maneje el layout automáticamente
        style={"borderBottom": "none"}
    )
