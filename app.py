# Aplicación de ejemplo del proyecto final: cantones de Costa Rica con su población.
# Ejecución: streamlit run apps/07-app-proyecto.py
import copy

import folium
import geopandas as gpd
import pandas as pd
import plotly.express as px
import streamlit as st
import plotly.graph_objects as go
from shapely.geometry import Point
from streamlit_folium import st_folium

DATOS = "https://github.com/nestorveas/proyecto/raw/refs/heads/main/"

# ---------- Configuración de la página (primera llamada a streamlit) ----------
st.set_page_config(page_title="ASADAS de Costa Rica", page_icon="🗺️", layout="wide")

st.title("ASADAS de Costa Rica")
st.caption("Servicios y distribución espacial a nivel nacional")

st.markdown(
    """La siguiente aplicación web fue desarrollada durante el curso *[Programación en SIG (GF-0657)](https://gf0657-programacionsig.github.io/2026-ii/)* y busca dar respuestas rápidas a consultas respecto a diferentes datos de las diferentes Asociaciones Administradoras de Acueducto y Alcantarillado Rural, comúnmente llamadas *ASADAS*, en Costa Rica.

Esta figura legal es una de las cuatro que Costa Rica tiene autorizada para brindar el servicio público de abastecimiento de agua potable y saneamiento, siendo las otras tres el propio Instituto Costarricense de Acueductos y Alcantarillados (AyA), Municipalidades, y la Empresa de Servicios Públicos de Heredia (ESPH).

Los datos utilizados provienen del Sistema de Apoyo a la Gestión de ASADAS (SAGA) del AyA, los cuales se encuentran en una capa digital de puntos donde cada uno corresponde a una oficina de Asada, junto con su correspondiente información. La información de cantones proviene del Sistema Nacional de Información Territorial (SNIT) del Registro Nacional.

Para este trabajo la información se centra en la cantidad de servicios (medidores) que tiene cada ASADA, y su relación espacial a nivel provincial, cantonal y distrital. Para poder visualizar esta información el usuario puede utilizar diferentes filtros dependiendo de su necesidad de información."""
)
# ---------- Datos, en caché ----------

@st.cache_data
def cargar_cantones():
    return gpd.read_file(DATOS + "cantones-2020-simplificados.gpkg").to_crs(4326)

@st.cache_data
def cargar_asadas():
    gdf_cantones = cargar_cantones()
    gdf_asadas = gpd.read_file(DATOS + "Asadas.gpkg").to_crs(4326)
    return gdf_asadas.sjoin(gdf_cantones[["cod_canton", "canton", "provincia", "geometry"]], how="left", predicate="within")

cantones_gdf = cargar_cantones()
asadas = cargar_asadas()

#Para el gráfico

ETIQUETAS = {"Servicios_": "Servicios (medidores)"}

ETIQUETAS_EJES = {
    "PROVINCIA": "Provincia",
    "Cantón": "Cantón",
    "DISTRITO": "Distrito",
}


#--------------- CONTROLES --------------
# Controles en la barra lateral: cada uno retorna el valor elegido
st.sidebar.header("Filtros")

provincias = ["Todas"] + sorted(asadas["PROVINCIA"].unique())
provincia = st.sidebar.selectbox("Provincia", provincias)

# Filtrar por provincia antes de construir la lista de cantones
if provincia == "Todas":
    df_provincia = asadas
else:
    df_provincia = asadas[asadas["PROVINCIA"] == provincia]

cantones = ["Todos"] + sorted(df_provincia["Cantón"].dropna().unique())
canton = st.sidebar.selectbox("Cantón", cantones)

#Filtrar por cantón antes de construir la lista de distritos
if canton == "Todos":
    df_canton = df_provincia
else:
    df_canton = df_provincia[df_provincia["Cantón"] == canton]

distritos = ["Todos"] + sorted(df_canton["DISTRITO"].dropna().unique())
distrito = st.sidebar.selectbox("Distrito", distritos)

servicios_minimos = st.sidebar.slider(
    "Servicios mínimos",
    min_value=0,
    max_value=5000,
    value=0,
    step=50,
)

# El filtrado es pandas con los valores de los controles 
# Es importante que esto vaya primero, porque de esta selección se derivan los demás datos YA FILTRADOS
seleccion = asadas
if provincia != "Todas":
    seleccion = seleccion[seleccion["PROVINCIA"] == provincia]
if canton != "Todos":
    seleccion = seleccion[seleccion["Cantón"] == canton]
if distrito != "Todos":
    seleccion = seleccion[seleccion["DISTRITO"] == distrito]
if servicios_minimos > 0:
    seleccion = seleccion[seleccion["Servicios_"].fillna(0) >= servicios_minimos]

# Nivel de agrupación dinámico 

if provincia == "Todas":
    col_agrupacion = "PROVINCIA"
    ambito = "todas las provincias"
elif canton == "Todos":
    col_agrupacion = "Cantón"
    ambito = f"provincia de {provincia}"
elif distrito == "Todos":
    col_agrupacion = "DISTRITO"
    ambito = f"cantón de {canton}"
else:
    col_agrupacion = "DISTRITO"
    ambito = f"distrito de {distrito}, {canton}"

# Indicadores en tres columnas

total_asadas = len(seleccion)
total_servicios = seleccion["Servicios_"].sum()
densidad = (total_servicios / total_asadas) if total_asadas > 0 else 0.0

col1, col2, col3 = st.columns(3) #Estos col son los datos fuertes y concretos que salen al inicio arriba
col1.metric("Asadas", len(seleccion)) #Len me muestra la suma de la cantidad de filas, en este caso la cantidad de Asadas
col2.metric("Servicios (medidores)", f"{seleccion['Servicios_'].sum():,.0f}".replace(",", " "))
col3.metric("Densidad (Servicios/Asada)",  f"{seleccion['Servicios_'].sum()/len(seleccion):,.1f}".replace(",", " "))

# Tabla interactiva: sin la columna de geometría, que no es una columna de datos
columnas = ["Ente_Opera", "PROVINCIA", "Cantón", "DISTRITO","Servicios_", "Hidrantes"]
tabla = seleccion.sort_values("Servicios_", ascending=False)[columnas]

# Pestañas: cada bloque with dibuja dentro de su pestaña
pestana_tabla, pestana_grafico, pestana_mapa = st.tabs(["Tabla", "Gráfico", "Mapa"])
with pestana_tabla:
    st.dataframe(
    tabla,
    hide_index=True,
    width="stretch",
    column_config={ #las columnas que quiero que se vean en la tabla
        "Ente_Opera": "Ente Operador",
        "PROVINCIA": "Provincia",
        "Cantón": "Cantón",
        "DISTRITO": "Distrito",  
        "Servicios_": st.column_config.NumberColumn("Servicios", format="%.0f"),
        "Hidrantes": st.column_config.NumberColumn("Hidrantes", format="%.1f")
    }
)

#with st.expander("Acerca de los datos"):
    #st.markdown("ASADAS de Costa Rica (Año 2024), datos obtenidos de SAGA-AyA)")

with pestana_grafico:
    variable = st.selectbox(
        "Variable para el gráfico",
        options=list(ETIQUETAS.keys()),
        format_func=lambda col: ETIQUETAS[col],
    )

    if seleccion.empty:
        st.info("No hay datos para los filtros seleccionados.")
    else:
        df_grafico = (
            seleccion.dropna(subset=[col_agrupacion])
            .groupby(col_agrupacion, as_index=False)[variable]
            .sum()
            .sort_values(variable, ascending=False)
            .head(15)
        )
        etiqueta_x = ETIQUETAS_EJES[col_agrupacion]
        grafico = px.bar(
            df_grafico,
            x=col_agrupacion,
            y=variable,
            labels={col_agrupacion: etiqueta_x, variable: ETIQUETAS[variable]},
            title=f"{ETIQUETAS[variable]} abastecidos por Asadas en 2024 a nivel de {etiqueta_x.lower()} ({ambito})",
            text_auto=",.0f",
        )
        st.plotly_chart(grafico, use_container_width=True)

with pestana_mapa:
    if seleccion.empty:
        st.info("No hay ASADAS para mostrar en el mapa con los filtros actuales.")
    else:
        mapa_cantones = cantones_gdf.copy()
        if provincia != "Todas":
            mapa_cantones = mapa_cantones[
                mapa_cantones["provincia"].str.lower() == provincia.lower()
            ]
        if canton != "Todos":
            mapa_cantones = mapa_cantones[
                mapa_cantones["canton"].str.lower() == canton.lower()
            ]
        if mapa_cantones.empty:
            mapa_cantones = cantones_gdf.copy()

        servicios_canton = (
            seleccion.dropna(subset=["cod_canton"])
            .groupby("cod_canton", as_index=False)["Servicios_"]
            .sum()
        )
        mapa_cantones = mapa_cantones.merge(servicios_canton, on="cod_canton", how="left")
        mapa_cantones["Servicios_"] = mapa_cantones["Servicios_"].fillna(0)

        geojson_cantones = mapa_cantones.__geo_interface__

        pts = seleccion.geometry.apply(
            lambda g: g if g.geom_type == "Point" else g.representative_point()
        )
        lats = pts.y
        lons = pts.x

        hover_text = [
            f"<b>{row['Ente_Opera']}</b><br>"
            f"Cantón: {row['Cantón']} | Distrito: {row['DISTRITO']}<br>"
            f"Servicios: {row['Servicios_']:,.0f}"
            for _, row in seleccion.iterrows()
        ]

        minx, miny, maxx, maxy = seleccion.total_bounds
        centro_lat = (miny + maxy) / 2
        centro_lon = (minx + maxx) / 2
        span = max(maxx - minx, maxy - miny)
        if span < 0.25:
            zoom = 10.5
        elif span < 0.8:
            zoom = 8.8
        elif span < 2.0:
            zoom = 7.8
        else:
            zoom = 7.0

        fig_mapa = go.Figure()

        fig_mapa.add_trace(
            go.Choroplethmap(
                geojson=geojson_cantones,
                locations=mapa_cantones["cod_canton"],
                featureidkey="properties.cod_canton",
                z=mapa_cantones["Servicios_"],
                colorscale="Blues",
                marker_opacity=0.45,
                marker_line_width=1.2,
                marker_line_color="#1f4e78",
                text=mapa_cantones["canton"],
                hovertemplate="<b>%{text}</b><br>Servicios ASADAS: %{z:,.0f}<extra></extra>",
                colorbar=dict(title="Servicios"),
            )
        )

        fig_mapa.add_trace(
            go.Scattermap(
                lat=lats,
                lon=lons,
                mode="markers",
                marker=dict(size=8, color="#d62728", opacity=0.85),
                text=hover_text,
                hovertemplate="%{text}<extra></extra>",
                name="ASADAS",
            )
        )

        fig_mapa.update_layout(
            map=dict(
                style="open-street-map",
                center=dict(lat=centro_lat, lon=centro_lon),
                zoom=zoom,
            ),
            margin=dict(r=0, t=40, l=0, b=0),
            title=f"Distribución espacial de ASADAS ({ambito}), 2024",
            height=550,
        )

        st.plotly_chart(fig_mapa, use_container_width=True)

st.caption("Fuentes: Instituto Costarricense de Acueductos y Alcantarillados (AyA, 2024) e Instituto Geográfico Nacional (SNIT,2024)")
st.caption("Los datos se encuentran en el [repositorio de este proyecto](https://github.com/nestorveas/proyecto/raw/refs/heads/main).")
st.caption("Se utilizó el asistente de IA *Gemini*. El texto completo y la la revisión de resultados y gráficos fueron realizados por el autor.")