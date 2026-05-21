import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from datetime import datetime

st.set_page_config(layout="wide", page_title="Mapa de Engenharia")
st.title("🗺️ Mapa da Engenharia")

ID_PLANILHA = "1i52bMXlaOCrvKFjZPwxmV_NvpdVzf6tHrCIGUMGZnDQ"
URL_CSV = f"https://docs.google.com/spreadsheets/d/{ID_PLANILHA}/export?format=csv"

@st.cache_data(ttl=300)
def carregar_dados():
    # Lê a planilha bruta sem cabeçalho para garantir mapeamento fixo pelas colunas físicas
    df = pd.read_csv(URL_CSV, header=None)
    
    df_util = pd.DataFrame()
    # Mapeamento exato informado:
    # B=1 (Tipo), D=3 (Abertura), E=4 (Encerramento), H=7 (Coordenada), I=8 (Categoria), J=9 (Classificação), L=11 (Info)
    df_util['tipo_protocolo'] = df[1].fillna("Não Informado").astype(str).str.strip()
    df_util['data_abertura_str'] = df[3].fillna("").astype(str).str.strip()
    df_util['data_encerramento_str'] = df[4].fillna("").astype(str).str.strip()
    df_util['coordenada'] = df[7].astype(str).str.strip()
    df_util['categoria'] = df[8].fillna("Não Informado").astype(str).str.strip()
    df_util['classificacao'] = df[9].fillna("Não Informado").astype(str).str.strip()
    df_util['descricao_base'] = df[11].fillna("").astype(str).str.strip()
    
    # Remove a linha de cabeçalho do Sheets se ela vier junta
    df_util = df_util[~df_util['coordenada'].astype(str).str.lower().str.contains('coordenada', na=False)]
    
    # Limpa linhas sem coordenadas válidas
    df_util = df_util[df_util['coordenada'] != ""]
    df_util = df_util[df_util['coordenada'] != "nan"]
    df_util = df_util[df_util['coordenada'].str.contains(',', na=False)]
    
    if df_util.empty:
        return pd.DataFrame()

    # Extrai Latitude e Longitude
    def extrair_lat_lon(txt):
        try:
            partes = str(txt).split(',')
            return float(partes[0].strip()), float(partes[1].strip())
        except:
            return None, None
            
    coordenadas_limpas = df_util['coordenada'].apply(extrair_lat_lon)
    df_util['lat'] = [c[0] for c in coordenadas_limpas]
    df_util['lon'] = [c[1] for c in coordenadas_limpas]
    df_util = df_util.dropna(subset=['lat', 'lon'])
    
    # Converte as colunas de data para o formato real do Python para podermos filtrar por período
    def converter_data(txt):
        for fmt in ('%d/%m/%Y', '%Y-%m-%d', '%d/%m/%y'):
            try:
                return pd.to_datetime(txt, format=fmt).date()
            except:
                continue
        return None

    df_util['dt_abertura'] = df_util['data_abertura_str'].apply(converter_data)
    df_util['dt_encerramento'] = df_util['data_encerramento_str'].apply(converter_data)
    
    return df_util

try:
    df_mapa = carregar_dados()
except Exception as e:
    st.error(f"Erro ao ler os dados da planilha: {e}")
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

# --- PAINEL LATERAL DE FILTROS ---
st.sidebar.header("🔍 Filtros do Mapa")

if not df_mapa.empty:
    # 1. Filtro de Classificação
    lista_classif = sorted(df_mapa['classificacao'].unique())
    classif_selecionadas = st.sidebar.multiselect("Classificação:", lista_classif, default=lista_classif)

    # 2. Filtro de Categoria
    lista_categ = sorted(df_mapa['categoria'].unique())
    categ_selecionadas = st.sidebar.multiselect("Categoria:", lista_categ, default=lista_categ)

    # 3. Filtro de Tipo de Protocolo
    lista_tipos = sorted(df_mapa['tipo_protocolo'].unique())
    tipos_selecionados = st.sidebar.multiselect("Tipo de Protocolo:", lista_tipos, default=lista_tipos)

    # 4. Filtro por Data de Abertura
    df_datas_ab = df_mapa[df_mapa['dt_abertura'].notnull()]
    if not df_datas_ab.empty:
        min_ab, max_ab = min(df_datas_ab['dt_abertura']), max(df_datas_ab['dt_abertura'])
        data_ab_sel = st.sidebar.date_input("Período de Abertura:", [min_ab, max_ab], min_value=min_ab, max_value=max_ab)
    else:
        data_ab_sel = None

    # 5. Filtro por Data de Encerramento
    df_datas_enc = df_mapa[df_mapa['dt_encerramento'].notnull()]
    if not df_datas_enc.empty:
        min_enc, max_enc = min(df_datas_enc['dt_encerramento']), max(df_datas_enc['dt_encerramento'])
        data_enc_sel = st.sidebar.date_input("Período de Encerramento:", [min_enc, max_enc], min_value=min_enc, max_value=max_enc)
    else:
        data_enc_sel = None

    # --- APLICAÇÃO DOS FILTROS NO DATAFRAME ---
    df_filtrado = df_mapa[
        (df_mapa['classificacao'].isin(classif_selecionadas)) &
        (df_mapa['categoria'].isin(categ_selecionadas)) &
        (df_mapa['tipo_protocolo'].isin(tipos_selecionados))
    ]

    # Aplica filtro de data de abertura se o usuário selecionou o range completo [inicio, fim]
    if data_ab_sel and len(data_ab_sel) == 2:
        df_filtrado = df_filtrado[
            (df_filtrado['dt_abertura'] >= data_ab_sel[0]) & 
            (df_filtrado['dt_abertura'] <= data_ab_sel[1])
        ]
        
    # Aplica filtro de data de encerramento
    if data_enc_sel and len(data_enc_sel) == 2:
        df_filtrado = df_filtrado[
            (df_filtrado['dt_encerramento'] >= data_enc_sel[0]) & 
            (df_filtrado['dt_encerramento'] <= data_enc_sel[1])
        ]
else:
    df_filtrado = pd.DataFrame()

# Campo opcional para centralizar coordenada livre (Mantido por utilidade)
coordenada_livre = st.sidebar.text_input("Centralizar mapa em (Lat, Lon):", placeholder="-31.9460, -51.9617")

# Define o centro geográfico dinâmico com base no que sobrou filtrado
if coordenada_livre:
    try:
        plat, plon = map(float, coordenada_livre.split(','))
        centro_lat, centro_lon, zoom_inicial = plat, plon, 17
    except:
        centro_lat, centro_lon, zoom_inicial = -31.7655, -52.3376, 12
elif not df_filtrado.empty:
    centro_lat, centro_lon = df_filtrado['lat'].mean(), df_filtrado['lon'].mean()
    zoom_inicial = 12
else:
    centro_lat, centro_lon = -31.7655, -52.3376
    zoom_inicial = 12

m = folium.Map(location=[centro_lat, centro_lon], zoom_start=zoom_inicial, control_scale=True)

# Renderiza apenas os pontos que passaram pelos filtros da barra lateral
if not df_filtrado.empty:
    st.write(f"🟢 Mostrando **{len(df_filtrado)}** pontos no mapa após os filtros aplicados.")
    for _, linha in df_filtrado.iterrows():
        cor = obter_cor(linha['classificacao'])
        
        # Identação inteligente e inserção da coordenada requisitada dentro da descrição do ponto
        desc_formatada = linha['descricao_popup'] if 'descricao_popup' in df_filtrado.columns else linha['descricao_base']
        desc_formatada = desc_formatada.replace("Tipo de Protocolo:", "<br><b>Tipo de Protocolo:</b>")
        desc_formatada = desc_formatada.replace("Abertura:", "<br><b>Abertura:</b>")
        desc_formatada = desc_formatada.replace("Encerramento:", "<br><b>Encerramento:</b>")
        desc_formatada = desc_formatada.replace("Categoria:", "<br><b>Categoria:</b>")
        
        texto_popup = f"""
        <b>Classificação:</b> {linha['classificacao']}<br>
        <b>Coordenada:</b> {linha['coordenada']}<br>
        <b>Descrição:</b><br>
        {desc_formatada}
        """
        
        folium.CircleMarker(
            location=[linha['lat'], linha['lon']], 
            radius=5, 
            color=cor, 
            fill=True, 
            fill_color=cor, 
            fill_opacity=0.8, 
            popup=folium.Popup(texto_popup, max_width=350)
        ).add_to(m)
else:
    st.warning("Nenhum registro encontrado para os filtros selecionados.")

st_folium(m, width=1300, height=700, returned_objects=[], key="mapa_engenharia_filtros")
