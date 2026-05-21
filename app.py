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
    # Lê a planilha bruta
    df = pd.read_csv(URL_CSV, header=None)
    
    df_util = pd.DataFrame()
    # Pega as colunas físicas H (7), J (9) e L (11) e força tudo para texto limpo
    df_util['coordenada'] = df[7].astype(str).str.strip()
    df_util['classificacao'] = df[9].fillna("").astype(str).str.strip()
    df_util['descricao'] = df[11].fillna("").astype(str).str.strip()
    
    # CORREÇÃO: Garante a conversão para texto antes do .str.lower() para evitar o erro 'Series' object has no attribute 'lower'
    df_util = df_util[~df_util['coordenada'].astype(str).str.lower().str.contains('coordenada', na=False)]
    
    # Limpa linhas vazias, nulas ou com o "" do SEERRO da sua fórmula
    df_util = df_util[df_util['coordenada'] != ""]
    df_util = df_util[df_util['coordenada'] != "nan"]
    df_util = df_util[df_util['coordenada'].str.contains(',', na=False)]
    
    if df_util.empty:
        return pd.DataFrame(columns=['lat', 'lon', 'classificacao_cor', 'descricao_popup'])

    # Extrai latitude e longitude com segurança contra erros de digitação
    def extrair_lat_lon(txt):
        try:
            partes = str(txt).split(',')
            return float(partes[0].strip()), float(partes[1].strip())
        except:
            return None, None
            
    coordenadas_limpas = df_util['coordenada'].apply(extrair_lat_lon)
    df_util['lat'] = [c[0] for c in coordenadas_limpas]
    df_util['lon'] = [c[1] for c in coordenadas_limpas]
    
    # Remove qualquer linha inválida
    df_util = df_util.dropna(subset=['lat', 'lon'])
    
    # Substitui vazios pelos nomes padrões
    df_util['classificacao_cor'] = df_util['classificacao'].replace("", "Outro tipo")
    df_util['descricao_popup'] = df_util['descricao'].replace("", "Sem descrição")
    
    return df_util

try:
    df_mapa = carregar_dados()
except Exception as e:
    st.error(f"Erro ao ler a planilha: {e}")
    st.stop()

def obter_cor(classificacao):
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
        return '#D3D3D3' # Cinza Claro

st.sidebar.header("🔍 Centralizar Coordenada")
coordenada_livre = st.sidebar.text_input("Digite ou cole a coordenada (Lat, Lon):", placeholder="-31.9460, -51.9617")

if not df_mapa.empty:
    centro_lat, centro_lon = df_mapa['lat'].mean(), df_mapa['lon'].mean()
    zoom_inicial = 12
else:
    centro_lat, centro_lon = -31.7655, -52.3376 # Pelotas/RS caso falte dados
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

# Insere as bolinhas separadas diretamente no mapa
if not df_mapa.empty:
    for _, linha in df_mapa.iterrows():
        cor = obter_cor(linha['classificacao_cor'])
        texto = f"<b>Classificação:</b> {linha['classificacao_cor']}<br><b>Descrição:</b> {linha['descricao_popup']}"
        
        folium.CircleMarker(
            location=[linha['lat'], linha['lon']], 
            radius=5, 
            color=cor, 
            fill=True, 
            fill_color=cor, 
            fill_opacity=0.8, 
            popup=folium.Popup(texto, max_width=300)
        ).add_to(m)
else:
    st.warning("Nenhuma coordenada válida foi encontrada na coluna H da planilha.")

st_folium(m, width=1300, height=700, returned_objects=[])
