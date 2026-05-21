import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium

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
    def extrair_lat_lon(txt):
        try:
            partes = str(txt).split(',')
            return float(partes[0].strip()), float(partes[1].strip())
        except:
            return None, None
            
    coordenadas_limpas = df_util['coordenada'].apply(extrair_lat_lon)
    df_util['lat'] = [c[0] for c in coordenadas_limpas]
    df_util['lon'] = [c[1] for c in coordenadas_limpas]
    
    # Remove o que não conseguiu converter para número
    df_util = df_util.dropna(subset=['lat', 'lon'])
    
    # Trata os retornos vazios "" do seu SEERRO/PROCX
    df_util['classificacao_cor'] = df_util['classificacao'].fillna("Não Encontrado").astype(str).str.strip()
    df_util.loc[df_util['classificacao_cor'] == "", 'classificacao_cor'] = "Não Encontrado"
    
    df_util['descricao_popup'] = df_util['descricao'].fillna("Sem descrição").astype(str).str.strip()
    df_util.loc[df_util['descricao_popup'] == "", 'descricao_popup'] = "Sem descrição"
    
    return df_util

try:
    df_mapa = carregar_dados()
except Exception as e:
    st.error(f"Erro ao processar as colunas H, J ou L da planilha. Detalhes: {e}")
    st.stop()

def obter_cor(classificacao):
    # Converte para maiúsculo para bater certinho com a sua regra
    classe = str(classificacao).upper().strip()
    
    if 'PREVENTIVA' in classe:
        return '#008000' # Verde
    elif 'IMPLANTAÇÃO' in classe or 'IMPLANTACAO' in classe:
        return '#1f77b4' # Azul
    elif 'CORRETIVA' in classe:
        return '#FFA500' # Laranja
    elif 'APOIO' in classe:
        return '#4F4F4F' # Cinza Escuro
    else:
        return '#D3D3D3' # Cinza Claro para qualquer outro tipo ou vazio do PROCX

st.sidebar.header("🔍 Centralizar Coordenada")
coordenada_livre = st.sidebar.text_input("Digite ou cole a coordenada (Lat, Lon):", placeholder="-31.9460, -51.9617")

if len(df_mapa) > 0:
    centro_lat, centro_lon = df_mapa['lat'].mean(), df_mapa['lon'].mean()
else:
    centro_lat, centro_lon = -15.7801, -47.9292 # Padrão Brasil caso a planilha zere
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

# Desenhando as bolinhas diretamente no mapa (sem o agrupador) para ficarem fixas
for _, linha in df_mapa.iterrows():
    cor = obter_cor(linha['classificacao_cor'])
    texto = f"<b>Classificação:</b> {linha['classificacao_cor']}<br><b>Descrição:</b> {linha['descricao_popup']}"
    
    folium.CircleMarker(
        location=[linha['lat'], linha['lon']], 
        radius=5, # Bolinhas levemente menores para não poluir o mapa estático
        color=cor, 
        fill=True, 
        fill_color=cor, 
        fill_opacity=0.8, 
        popup=folium.Popup(texto, max_width=300)
    ).add_to(m)

# Mantém o mapa leve
