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
    df = pd.read_csv(URL_CSV, header=None)
    
    df_util = pd.DataFrame()
    df_util['tipo_protocolo'] = df[1].fillna("Não Informado").astype(str).str.strip()
    df_util['data_abertura_str'] = df[3].fillna("").astype(str).str.strip()
    df_util['data_encerramento_str'] = df[4].fillna("").astype(str).str.strip()
    df_util['coordenada'] = df[7].astype(str).str.strip()
    df_util['categoria'] = df[8].fillna("Não Informado").astype(str).str.strip()
    df_util['classificacao'] = df[9].fillna("Não Informado").astype(str).str.strip()
    df_util['descricao_base'] = df[11].fillna("").astype(str).str.strip()
    
    df_util = df_util[~df_util['coordenada'].astype(str).str.lower().str.contains('coordenada', na=False)]
    df_util = df_util[df_util['coordenada'] != ""]
    df_util = df_util[df_util['coordenada'] != "nan"]
    df_util = df_util[df_util['coordenada'].str.contains(',', na=False)]
    
    if df_util.empty:
        return pd.DataFrame()

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
    
    # ATUALIZAÇÃO: Nova cor para Rompimento (Vermelho Sangue)
    if 'ROMPIMENTO' in classe:
        return '#8B0000' # Vermelho Sangue
    elif 'PREVENTIVA' in classe:
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
    lista_classif = sorted(df_mapa['classificacao'].unique())
    classif_selecionadas = st.sidebar.multiselect("Classificação:", lista_classif, default=lista_classif)

    lista_categ = sorted(df_mapa['categoria'].unique())
    categ_selecionadas = st.sidebar.multiselect("Categoria:", lista_categ, default=lista_categ)

    lista_tipos = sorted(df_mapa['tipo_protocolo'].unique())
    tipos_selecionados = st.sidebar.multiselect("Tipo de Protocolo:", lista_tipos, default=lista_tipos)

    df_datas_ab = df_mapa[df_mapa['dt_abertura'].notnull()]
    if not df_datas_ab.empty:
        min_ab, max_ab = min(df_datas_ab['dt_abertura']), max(df_datas_ab['dt_abertura'])
        data_ab_sel = st.sidebar.date_input("Período de Abertura:", [min_ab, max_ab], min_value=min_ab, max_value=max_ab)
    else:
        data_ab_sel = None

    df_datas_enc = df_mapa[df_mapa['dt_encerramento'].notnull()]
    if not df_datas_enc.empty:
        min_enc, max_enc = min(df_datas_enc['dt_encerramento']), max(df_datas_enc['dt_encerramento'])
        data_enc_sel = st.sidebar.date_input("Período de Encerramento:", [min_enc, max_enc], min_value=min_enc, max_value=max_enc)
    else:
        data_enc_sel = None

    df_filtrado = df_mapa[
        (df_mapa['classificacao'].isin(classif_selecionadas)) &
        (df_mapa['categoria'].isin(categ_selecionadas)) &
        (df_mapa['tipo_protocolo'].isin(tipos_selecionados))
    ]

    if data_ab_sel and len(data_ab_sel) == 2:
        df_filtrado = df_filtrado[
            (df_filtrado['dt_abertura'] >= data_ab_sel[0]) & 
            (df_filtrado['dt_abertura'] <= data_ab_sel[1])
        ]
        
    if data_enc_sel and len(data_enc_sel) == 2:
        df_filtrado = df_filtrado[
            (df_filtrado['dt_encerramento'] >= data_enc_sel[0]) & 
            (df_filtrado['dt_encerramento'] <= data_enc_sel[1])
        ]
else:
    df_filtrado = pd.DataFrame()

coordenada_livre = st.sidebar.text_input("Centralizar mapa em (Lat, Lon):", placeholder="-31.9460, -51.9617")

ponto_pesquisado = None
if coordenada_livre:
    try:
        plat, plon = map(float, coordenada_livre.split(','))
        centro_lat, centro_lon, zoom_inicial = plat, plon, 17
        ponto_pesquisado = (plat, plon)
        st.sidebar.success("Coordenada localizada!")
    except:
        st.sidebar.error("Formato inválido. Use: -31.9460, -51.9617")
        if not df_filtrado.empty:
            centro_lat, centro_lon, zoom_inicial = df_filtrado['lat'].mean(), df_filtrado['lon'].mean(), 12
        else:
            centro_lat, centro_lon, zoom_inicial = -31.7655, -52.3376, 12
elif not df_filtrado.empty:
    centro_lat, centro_lon = df_filtrado['lat'].mean(), df_filtrado['lon'].mean()
    zoom_inicial = 12
else:
    centro_lat, centro_lon = -31.7655, -52.3376
    zoom_inicial = 12

m = folium.Map(location=[centro_lat, centro_lon], zoom_start=zoom_inicial, control_scale=True)

if not df_filtrado.empty:
    st.write(f"🟢 Mostrando **{len(df_filtrado)}** pontos no mapa após os filtros aplicados.")
    for _, linha in df_filtrado.iterrows():
        cor = obter_cor(linha['classificacao'])
        
        desc_formatada = linha['descricao_base']
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

if ponto_pesquisado:
    folium.Marker(
        location=ponto_pesquisado,
        popup=folium.Popup(f"<b>Sua Busca:</b><br>{coordenada_livre}", max_width=200),
        icon=folium.Icon(color="red", icon="info-sign")
    ).add_to(m)

st_folium(m, width=1300, height=700, returned_objects=[], key="mapa_engenharia_filtros_v3")
