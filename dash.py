import streamlit as st
import geopandas as gpd
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

def carregar_shapefile(caminho, calcular_percentuais=True):
    gdf = gpd.read_file(caminho)
    gdf["geometry"] = gdf["geometry"].apply(lambda geom: geom.buffer(0) if not geom.is_valid else geom)
    gdf = gdf[gdf["geometry"].notnull() & gdf["geometry"].is_valid]
    gdf_proj = gdf.to_crs("EPSG:31983")
    gdf_proj["area_calc_km2"] = gdf_proj.geometry.area / 1e6
    if "area_km2" in gdf.columns:
        gdf["area_km2"] = gdf["area_km2"].replace(0, None)
        gdf["area_km2"] = gdf["area_km2"].fillna(gdf_proj["area_calc_km2"])
    else:
        gdf["area_km2"] = gdf_proj["area_calc_km2"]
    if calcular_percentuais:
        if "alerta_km2" in gdf.columns:
            gdf["perc_alerta"] = (gdf["alerta_km2"] / gdf["area_km2"]) * 100
        else:
            gdf["perc_alerta"] = 0
        if "sigef_km2" in gdf.columns:
            gdf["perc_sigef"] = (gdf["sigef_km2"] / gdf["area_km2"]) * 100
        else:
            gdf["perc_sigef"] = 0
    else:
        gdf["perc_alerta"] = 0
        gdf["perc_sigef"] = 0
    gdf["id"] = gdf.index.astype(str)
    gdf = gdf.to_crs("EPSG:4326")
    return gdf

caminho_shapefile_cnuc = r'C:\Users\wwrm_\Desktop\Projetos\exec\cnuc.shp'
caminho_shapefile_sigef = r'C:\Users\wwrm_\Desktop\Projetos\exec\sigef.shp'
caminho_csv = r'C:\Users\wwrm_\Desktop\Projetos\exec\CPT-PA-count.csv'
gdf_cnuc = carregar_shapefile(caminho_shapefile_cnuc)
gdf_sigef = carregar_shapefile(caminho_shapefile_sigef, calcular_percentuais=False)
df_csv = pd.read_csv(caminho_csv)
gdf_cnuc["base"] = "cnuc"
gdf_sigef["base"] = "sigef"

limites = gdf_cnuc.total_bounds
centro = {"lat": (limites[1] + limites[3]) / 2, "lon": (limites[0] + limites[2]) / 2}

df_csv = pd.read_csv(caminho_csv)
df_csv = df_csv.rename(columns={"Unnamed: 0": "Município"})
colunas_ocorrencias = ["Áreas de conflitos", "Assassinatos", "Conflitos por Terra", "Ocupações Retomadas", "Tentativas de Assassinatos", "Trabalho Escravo"]
df_csv["total_ocorrencias"] = df_csv[colunas_ocorrencias].sum(axis=1)

def criar_figura(ids_selecionados=None, invadindo_opcao=None):
    fig = px.choropleth_mapbox(
        gdf_cnuc,
        geojson=gdf_cnuc.__geo_interface__,
        locations="id",
        color_discrete_sequence=["#DDDDDD"],
        hover_data=["nome_uc", "municipio", "perc_alerta", "perc_sigef", "alerta_km2", "sigef_km2", "area_km2"],
        mapbox_style="open-street-map",
        center=centro,
        zoom=4,
        opacity=0.7,
        title="Porcentagem de Área Sobreposta por Alertas e SIGEF"
    )
    if ids_selecionados:
        gdf_sel = gdf_cnuc[gdf_cnuc["id"].isin(ids_selecionados)]
        fig_sel = px.choropleth_mapbox(
            gdf_sel,
            geojson=gdf_cnuc.__geo_interface__,
            locations="id",
            color_discrete_sequence=["#0074D9"],
            hover_data=["nome_uc", "municipio", "perc_alerta", "perc_sigef", "alerta_km2", "sigef_km2", "area_km2"],
            mapbox_style="open-street-map",
            center=centro,
            zoom=4,
            opacity=0.8,
        )
        for trace in fig_sel.data:
            fig.add_trace(trace)
    if invadindo_opcao is not None:
        if invadindo_opcao.lower() == "todos":
            gdf_sigef_filtrado = gdf_sigef
        else:
            gdf_sigef_filtrado = gdf_sigef[gdf_sigef["invadindo"].str.strip().str.lower() == invadindo_opcao.strip().lower()]
        trace_sigef = go.Choroplethmapbox(
            geojson=gdf_sigef_filtrado.__geo_interface__,
            locations=gdf_sigef_filtrado["id"],
            z=[1] * len(gdf_sigef_filtrado),
            colorscale=[[0, "#FF4136"], [1, "#FF4136"]],
            marker_opacity=0.5,
            marker_line_width=1,
            name="SIGEF",
            showlegend=True,
            showscale=False
        )
        fig.add_trace(trace_sigef)
    if "Município" in df_csv.columns:
        cidades = df_csv["Município"].unique()
        cores_paleta = px.colors.qualitative.Pastel
        color_map = {cidade: cores_paleta[i % len(cores_paleta)] for i, cidade in enumerate(cidades)}
        for cidade in cidades:
            df_cidade = df_csv[df_csv["Município"] == cidade]
            base_size = list(df_cidade["total_ocorrencias"] * 3)
            outline_size = [s + 4 for s in base_size]
            trace_cpt_outline = go.Scattermapbox(
                lat=df_cidade["Latitude"],
                lon=df_cidade["Longitude"],
                mode="markers",
                marker=dict(
                    size=outline_size,
                    color="black",
                    sizemode="area"
                ),
                hoverinfo="none",
                showlegend=False
            )
            trace_cpt = go.Scattermapbox(
                lat=df_cidade["Latitude"],
                lon=df_cidade["Longitude"],
                mode="markers",
                marker=dict(
                    size=base_size,
                    color=color_map[cidade],
                    sizemode="area"
                ),
                text=df_cidade.apply(lambda linha: (
                    f"Município: {linha['Município']}<br>"
                    f"Áreas de conflitos: {linha['Áreas de conflitos']}<br>"
                    f"Assassinatos: {linha['Assassinatos']}<br>"
                    f"Conflitos por Terra: {linha['Conflitos por Terra']}<br>"
                    f"Ocupações Retomadas: {linha['Ocupações Retomadas']}<br>"
                    f"Tentativas de Assassinatos: {linha['Tentativas de Assassinatos']}<br>"
                    f"Trabalho Escravo: {linha['Trabalho Escravo']}"
                ), axis=1),
                hoverinfo="text",
                name=f"Ocorrências - {cidade}",
                showlegend=True
            )
            fig.add_trace(trace_cpt_outline)
            fig.add_trace(trace_cpt)
    else:
        trace_cpt = go.Scattermapbox(
            lat=df_csv["Latitude"],
            lon=df_csv["Longitude"],
            mode="markers",
            marker=dict(
                size=df_csv["total_ocorrencias"] * 3,
                color="red",
                sizemode="area"
            ),
            text=df_csv.apply(lambda linha: (
                f"Áreas de conflitos: {linha['Áreas de conflitos']}<br>"
                f"Assassinatos: {linha['Assassinatos']}<br>"
                f"Conflitos por Terra: {linha['Conflitos por Terra']}<br>"
                f"Ocupações Retomadas: {linha['Ocupações Retomadas']}<br>"
                f"Tentativas de Assassinatos: {linha['Tentativas de Assassinatos']}<br>"
                f"Trabalho Escravo: {linha['Trabalho Escravo']}"
            ), axis=1),
            hoverinfo="text",
            name="Ocorrências",
            showlegend=True
        )
        fig.add_trace(trace_cpt)
    for trace in fig.data:
        if trace.type != "scattermapbox":
            trace.showlegend = False
    fig.update_layout(
        coloraxis_showscale=False,
        legend=dict(title="Legenda", x=0, y=1),
        height=700,
        margin={"r": 10, "t": 50, "l": 10, "b": 10},
        title_font=dict(size=22),
    )
    return fig

def criar_cards(ids_selecionados=None):
    filtro = gdf_cnuc[gdf_cnuc["id"].isin(ids_selecionados)] if ids_selecionados else gdf_cnuc
    total_alerta = filtro["c_alertas"].sum()
    total_sigef = filtro["c_sigef"].sum()
    total_area = filtro["area_km2"].sum()
    perc_alerta = (total_alerta / total_area * 100) if total_area else 0
    perc_sigef = (total_sigef / total_area * 100) if total_area else 0
    total_unidades = filtro.shape[0]
    estilo_card = {"backgroundColor": "#0074D9", "color": "white", "padding": "10px", "borderRadius": "5px", "textAlign": "center", "width": "150px", "height": "150px", "margin": "5px", "display": "flex", "flexDirection": "column", "justifyContent": "center", "alignItems": "center", "boxSizing": "border-box", "overflow": "hidden"}
    cartoes_shapefile = st.columns(3)
    cartoes_shapefile[0].metric("Percentual de Alerta", f"{perc_alerta:.2f}%")
    cartoes_shapefile[1].metric("Percentual SIGEF", f"{perc_sigef:.2f}%")
    cartoes_shapefile[2].metric("Total de Unidades", f"{total_unidades}")
    contagem_alerta = filtro["c_alertas"].sum()
    contagem_sigef = filtro["c_sigef"].sum()
    cartoes_contagens = st.columns(2)
    cartoes_contagens[0].metric("Contagem Alerta", f"{contagem_alerta}")
    cartoes_contagens[1].metric("Contagem SIGEF", f"{contagem_sigef}")

def get_invadindo_filtro(value):
    return value

opcoes_invadindo = ["Todos"] + sorted(gdf_sigef["invadindo"].unique().tolist())

bar_fig = px.bar(
    gdf_cnuc,
    x='nome_uc',
    y=['alerta_km2', 'sigef_km2', 'area_km2'],
    labels={'value': "Contagens", "nome_uc": "Nome UC"},
    barmode="group",
    color_discrete_map={
        "alerta_km2": px.colors.qualitative.Pastel[0],
        "sigef_km2": px.colors.qualitative.Pastel[1],
        "area_km2": px.colors.qualitative.Pastel[2]
    }
)
bar_fig.update_layout(legend_title_text='Métricas')

pie_fig = px.pie(
    df_csv,
    values='Áreas de conflitos',
    names='Município',
    title='Áreas de conflitos',
    color_discrete_sequence=px.colors.qualitative.Pastel
)
pie_fig.update_traces(textposition='inside', textinfo='percent+label')
pie_fig.update_layout(font_size=14)

st.title("Dashboard de Monitoramento")

invadindo_opcao = st.selectbox("Selecione a área (invadindo)", opcoes_invadindo)

fig = criar_figura(invadindo_opcao=invadindo_opcao)
st.plotly_chart(fig, use_container_width=True)

criar_cards()

col1, col2 = st.columns(2)
with col1:
    st.plotly_chart(bar_fig, use_container_width=True)
with col2:
    st.plotly_chart(pie_fig, use_container_width=True)