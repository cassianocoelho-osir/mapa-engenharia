import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from folium.plugins import MarkerCluster

st.set_page_config(layout="wide", page_title="Mapa de Engenharia")
st.title("🗺️ Mapa da Engenharia")

# --- LINK DA SUA PLANILHA ---
ID_PLANILHA = "1i52bMXlaOCrvKFjZPwxmV_NvpdVzf6tHrCIGUMGZnDQ"
URL_CSV = f"https://docs.google.com/spreadsheets/d/{ID_PLANILHA}/export?format=csv"

@st.cache_data(ttl=600)
def carregar_dados():
    # Carrega a planilha forçando o nome das colunas principais pelas letras
    df = pd.read_csv(URL_CSV)
    
    # Ajuste automático caso os nomes das colunas variem (pega por posição se necessário)
    # Coluna H (Posição 7), Coluna J (Posição 9), Coluna L (Posição 11)
    col_coordenada = 'Coordenada' if 'Coordenada' in df.columns else df.columns[7]
    col_classificacao = df.columns[9]
    col_descricao = df.columns[11]
    
    df = df.dropna(subset=[col_coordenada])
    df[['lat', 'lon']] = df[col_coordenada].str.split(',', expand=True).astype(float)
    
    # Padroniza os nomes internos para o código funcionar sempre
    df['classificacao_cor'] = df[col_classificacao].astype(str).str.strip()
    df['descricao_popup'] = df[col_descricao].astype(str)
    
    return df

try:
    df_mapa = carregar_dados()
except Exception as e:
    st.error(f"Erro ao carregar os dados. Verifique as colunas H, J e L. Erro: {e}")
    st.stop()

# --- FUNÇÃO PARA DEFINIR CORES POR CLASSIFICAÇÃO (Coluna J) ---
def obter_cor(classificacao):
    # Transforma em minúsculo para evitar problemas com espaços ou maiúsculas
    classe = classificacao.lower()
    if 'alta' in classe or 'urgente' in classe or 'a' in classe:
        return '#FF0000' # Vermelho
    elif 'media' in classe or 'morna' in classe or 'b' in classe:
        return '#FFA500' # Laranja
    elif 'baixa' in classe or 'fria' in classe or 'c' in classe:
        return '#008000' # Verde
    else:
        return '#1f77b4' # Azul Padrão (Caso mude o texto na coluna J)

# --- PAINEL LATERAL DE BUSCA ---
st.sidebar.header("🔍 Centralizar Coordenada")
coordenada_livre = st.sidebar.text_input(
    "Digite ou cole a coordenada (Lat, Lon):", 
    placeholder="-31.9460, -51.9617"
)

# Define o centro padrão do mapa (média de todos os pontos)
centro_lat, centro_lon = df_mapa['lat'].mean(), df_mapa['lon'].mean()
zoom_inicial = 12

# Se o usuário pesquisar uma coordenada, o mapa muda o centro para lá
if coordenada_livre:
    try:
        plat, plon = map(float, coordenada_livre.split(','))
        centro_lat, centro_lon = plat, plon
        zoom_inicial = 16  # Dá um zoom maior para focar no ponto pesquisado
        st.sidebar.success("Centralizado na coordenada com sucesso!")
    except:
        st.sidebar.error("Formato inválido. Use o padrão: -31.9460, -51.9617")

# --- CRIAÇÃO DO MAPA ---
m = folium.Map(location=[centro_lat, centro_lon], zoom_start=zoom_inicial, control_scale=True)

# Adiciona um marcador de destaque caso tenha pesquisado uma coordenada específica
if coordenada_livre:
    folium.CircleMarker(
        location=[centro_lat, centro_lon],
        radius=10,
        color="black",
        fill=True,
        fill_color="yellow",
        fill_opacity=1,
        popup="Sua busca"
    ).add_to(m)

# Agrupamento (Cluster) para alta volumetria de pontos
marker_cluster = MarkerCluster(disable_clustering_at_zoom=16).add_to(m)

# Desenha os pontos na tela
for _, linha in df_mapa.iterrows():
    cor_ponto = obter_cor(linha
