import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from folium.plugins import MarkerCluster

st.set_page_config(layout="wide", page_title="Mapa de Engenharia")
st.title("🗺️ Mapa da Engenharia")

ID_PLANILHA = "1i52bMXlaOCrvKFjZPwxmV_NvpdVzf6tHrCIGUMGZnDQ"
URL_CSV = f"https://docs.google.com/spreadsheets/d/{ID_PLANILHA}/export?format=csv"

@st.cache_data(ttl=600)
def carregar_dados():
    df = pd.read_csv(URL_CSV)
    col_coordenada = 'Coordenada' if 'Coordenada' in df.columns else df.columns[7]
    col_classificacao = df.columns[9]
    col_descricao = df.columns[11]
    
    df = df.dropna(subset=[col_coordenada])
    df[['lat', 'lon']] = df[col_coordenada].str.split(',', expand=True).astype(float)
    df['classificacao_cor'] = df[col_classificacao].astype(str).str.strip()
    df['descricao_popup'] = df[col_descricao].astype(str)
    return df

try:
    df_mapa = carregar_dados()
except Exception as e:
    st.error(f"Erro ao carregar os dados: {e}")
    st.stop()

def obter_cor(classificacao):
    classe = classificacao.lower()
    if 'alta' in classe or 'urgente' in classe or 'a' in classe:
        return '#FF0000'
    elif 'media' in classe or 'morna' in classe or 'b' in classe:
        return '#FFA500'
    elif 'baixa' in classe or 'fria' in classe or 'c' in classe:
        return '#008000'
    return '#1f77b4'

st.sidebar.header("🔍 Centralizar Coordenada")
coordenada_livre = st.sidebar.text_input("Digite ou cole a coordenada (Lat, Lon):", placeholder="-31.9460, -51.9617")

centro_lat, centro_lon = df_mapa['lat'].mean(), df_mapa['lon'].mean()
zoom_inicial = 12

if coordenada_livre:
    try:
        plat, plon = map(float, coordenada_livre.split(','))
        centro_lat, centro_lon = plat, plon
        zoom_inicial = 16
        st.sidebar.success("Centralizado!")
    except:
        st.sidebar.error("Formato inválido. Use: -31.9460, -51.9617")

m = folium.Map(location=[centro_lat, centro_lon], zoom_start=zoom_inicial, control_scale=True)

if coordenada_livre:
    folium.CircleMarker(location=[centro_lat, centro_lon], radius=10, color="black", fill=True, fill_color="yellow", fill_opacity=1, popup="Sua busca").add_to(m)

marker_cluster = MarkerCluster(disable_clustering_at_zoom=16).add_to(m)

for _, linha in df_mapa.iterrows():
    cor = obter_cor(linha['classificacao_cor'])
    texto = f"<b>Classificação:</b> {linha['classificacao_cor']}<br><b>Descrição:</b> {linha['descricao_popup']}"
    folium.CircleMarker(location=[linha['lat'], linha['lon']], radius=6, color=cor, fill=True, fill_color=cor, fill_opacity=0.8, popup=folium.Popup(texto, max_width=300)).add_to(marker_cluster)

st_folium(m, width=1300, height=700, returned_objects=[])
