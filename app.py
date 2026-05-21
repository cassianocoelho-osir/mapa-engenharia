import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from folium.plugins import MarkerCluster
from geopy.distance import geodesic

st.set_page_config(layout="wide", page_title="Mapa de Engenharia")
st.title("🗺️ Mapa da Engenharia - Alta Volumetria em Tempo Real")

# --- LINK DA SUA PLANILHA DO GOOGLE DRIVE ---
# Substitua o ID abaixo pelo ID real da sua planilha do Google Sheets
ID_PLANILHA = "1i52bMXlaOCrvKFjZPwxmV_NvpdVzf6tHrCIGUMGZnDQ"
URL_CSV = f"https://docs.google.com/spreadsheets/d/{ID_PLANILHA}/export?format=csv"

@st.cache_data(ttl=300)
def carregar_dados():
    df = pd.read_csv(URL_CSV)
    df = df.dropna(subset=['Coordenada'])
    df[['lat', 'lon']] = df['Coordenada'].str.split(',', expand=True).astype(float)
    return df

try:
    df_mapa = carregar_dados()
except Exception as e:
    st.error(f"Erro ao conectar com a planilha. Verifique se está pública. Erro: {e}")
    st.stop()

# --- PAINEL LATERAL DE BUSCA LIVRE ---
st.sidebar.header("🔍 Pesquisa por Proximidade")
coordenada_livre = st.sidebar.text_input(
    "Cola qualquer coordenada livre (Lat, Lon):", 
    placeholder="-31.9460, -51.9617"
)
raio_busca = st.sidebar.slider("Raio de verificação (em metros):", 100, 10000, 2000)

centro_lat, centro_lon = df_mapa['lat'].mean(), df_mapa['lon'].mean()
ponto_pesquisado = None

if coordenada_livre:
    try:
        plat, plon = map(float, coordenada_livre.split(','))
        centro_lat, centro_lon = plat, plon
        ponto_pesquisado = (plat, plon)
        st.sidebar.success("Coordenada localizada!")
    except:
        st.sidebar.error("Formato inválido. Use: -31.9460, -51.9617")

# --- FILTRO MATEMÁTICO DE ALTA PERFORMANCE ---
if ponto_pesquisado:
    def calcular_distancia(linha):
        return geodesic(ponto_pesquisado, (linha['lat'], merge_lon:=linha['lon'])).meters <= raio_busca
    df_filtrado = df_mapa[df_mapa.apply(calcular_distancia, axis=1)]
    st.subheader(f"📌 Encontrados {len(df_filtrado)} pontos no raio de {raio_busca} metros.")
else:
    df_filtrado = df_mapa
    st.subheader(f"📊 Exibindo base completa ({len(df_mapa)} registros).")

# --- CRIAÇÃO DO MAPA ---
m = folium.Map(location=[centro_lat, centro_lon], zoom_start=12, control_scale=True)

if ponto_pesquisado:
    folium.Marker(ponto_pesquisado, popup=f"Busca: {coordenada_livre}", icon=folium.Icon(color="red", icon="search")).add_to(m)
    folium.Circle(radius=raio_busca, location=ponto_pesquisado, color="red", fill=True, fill_opacity=0.08).add_to(m)

# Cluster para não travar com 100k pontos
marker_cluster = MarkerCluster().add_to(m)

for _, linha in df_filtrado.iterrows():
    detalhes = f"<b>Protocolo:</b> {linha.get('numero_protocolo', '')}<br><b>Status:</b> {linha.get('status', '')}"
    folium.Marker([linha['lat'], linha['lon']], popup=folium.Popup(detalhes, max_width=300)).add_to(marker_cluster)

st_folium(m, width=1300, height=700)
