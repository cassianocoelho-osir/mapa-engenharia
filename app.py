import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from folium.plugins import MarkerCluster

st.set_page_config(layout="wide", page_title="Mapa de Engenharia")
st.title("🗺️ Mapa da Engenharia")

ID_PLANILHA = "1i52bMXlaOCrvKFjZPwxmV_NvpdVzf6tHrCIGUMGZnDQ"
URL_CSV = f"https://docs.google.com/spreadsheets/d/{ID_PLANILHA}/export?format=csv"

@st.cache_data(ttl=300)
def carregar_dados():
    # Lê a planilha sem usar a primeira linha como cabeçalho para mapear as letras certas
    df = pd.read_csv(URL_CSV, header=None)
    
    # Mapeia as colunas por posição física exata das letras:
    # A=0, B=1, C=2, D=3, E=4, F=5, G=6, H=7, I=8, J=9, K=10, L=11
    df_util = pd.DataFrame()
    df_util['coordenada'] = df[7] # Coluna H
    df_util['classificacao'] = df[9] # Coluna J
    df_util['descricao'] = df[11] # Coluna L
    
    # Remove a primeira linha caso ela seja o título da coluna (ex: "Coordenada")
    if df_util['coordenada'].iloc[0] in ['Coordenada', 'coordenada', 'COORDENADA']:
        df_util = df_util.iloc[1:].reset_index(drop=True)
        
    # Limpa linhas onde a coordenada está realmente vazia, nula ou sobrou "" da fórmula
    df_util = df_util.dropna(subset=['coordenada'])
    df_util = df_util[df_util['coordenada'].astype(str).str.strip() != ""]
    
    # Divide a coordenada em Lat e Lon tratando erros de digitação
    def extrair_lat_lon(
