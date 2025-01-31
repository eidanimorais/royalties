import streamlit as st
import pandas as pd
import requests
import io

# Configuração inicial do app Streamlit
st.set_page_config(layout="centered")

# URLs das planilhas do Google Sheets exportadas como CSV
SHEET_URL_1 = "https://docs.google.com/spreadsheets/d/1oWUAgZLemNm3DhPx-MkXndRmLnQqQzskCAJvFSqdBSA/export?format=csv"
SHEET_URL_2 = "https://docs.google.com/spreadsheets/d/10NfrtCpSjBAwedzf3YLmlQRxvQAxDDAGzyll_b34AQo/export?format=csv"

# Função para carregar e corrigir os dados
@st.cache_data
def load_data(url1, url2):
    try:
        # Desativa a verificação SSL para evitar erros de certificado
        responses = [requests.get(url, verify=False) for url in [url1, url2]]
        for response in responses:
            response.raise_for_status()
        
        dfs = [pd.read_csv(io.StringIO(response.text), encoding='utf-8') for response in responses]
        for df in dfs:
            df.columns = [col.encode('latin1', 'ignore').decode('utf-8', 'ignore') for col in df.columns]
            for col in df.select_dtypes(include=['object']).columns:
                df[col] = df[col].apply(lambda x: x.encode('latin1', 'ignore').decode('utf-8', 'ignore') if isinstance(x, str) else x)
        return dfs
    except Exception as e:
        st.error(f"Erro ao carregar os dados: {e}")
        return [pd.DataFrame(), pd.DataFrame()]

# Carregar dados de ambas as planilhas em cache
df1, df2 = load_data(SHEET_URL_1, SHEET_URL_2)

# Obter todas as plataformas exclusivas das planilhas
@st.cache_data
def get_unique_platforms(df1, df2):
    platforms = []
    for df in [df1, df2]:
        if "PLATAFORMA" in df.columns:
            platforms += [platform.strip() for platform in df["PLATAFORMA"].dropna().astype(str).unique()]
    return sorted(set(platforms))

platform_options = ["Todas"] + get_unique_platforms(df1, df2)

# Título do app
st.markdown("<h1 style='text-align: center;'>Calculadora de Royalties</h1>", unsafe_allow_html=True)

# Filtros e campo de pesquisa logo abaixo do título
with st.container():
    col1, col2, col3 = st.columns([1, 1, 2])
    with col1:
        trimestre = st.selectbox("Filtrar por Trimestre", options=["Todos", "2024-Q1", "2024-Q2", "2024-Q3", "2024-Q4"])
    with col2:
        plataforma = st.selectbox("Filtrar por Plataforma", options=platform_options)
    with col3:
        search_query = st.text_input("Pesquisar por Música ou Artista", placeholder="Digite aqui para buscar...")

# Função para aplicar filtros dinamicamente (otimizado para pré-carregamento de pesquisa)
@st.cache_data
def apply_filters_cached(df, trimestre, plataforma):
    if not df.empty:
        df = df.applymap(lambda x: str(x).strip() if isinstance(x, str) else x)  # Remove espaços extras
        if trimestre != "Todos" and "TRIMESTRE" in df.columns:
            df = df[df["TRIMESTRE"].fillna("").str.contains(trimestre, case=False, na=False)]
        if plataforma != "Todas" and "PLATAFORMA" in df.columns:
            df = df[df["PLATAFORMA"].fillna("").str.contains(plataforma, case=False, na=False)]
    return df

# Aplicar filtros básicos antes da pesquisa
df1_filtered_base = apply_filters_cached(df1.copy(), trimestre, plataforma)
df2_filtered_base = apply_filters_cached(df2.copy(), trimestre, plataforma)

# Filtrar por pesquisa dinâmica
if search_query:
    query = search_query.lower()
    df1_filtered = df1_filtered_base[df1_filtered_base.apply(lambda row: query in " ".join(row.astype(str).str.lower()), axis=1)]
    df2_filtered = df2_filtered_base[df2_filtered_base.apply(lambda row: query in " ".join(row.astype(str).str.lower()), axis=1)]
else:
    df1_filtered = df1_filtered_base
    df2_filtered = df2_filtered_base

# Exibir Planilha 1 (Renomeada para Royalties)
st.subheader("Royalties")
if not df1_filtered.empty:
    st.dataframe(df1_filtered, use_container_width=True)
    # Soma dos royalties
    if "ROYALTIES" in df1_filtered.columns:
        try:
            df1_filtered["ROYALTIES_CLEANED"] = df1_filtered["ROYALTIES"].replace(
                {r'[R$\s,]': '', r'\.(?=\d{3})': '', r',': '.'}, regex=True
            ).astype(float)
            total_royalties = df1_filtered["ROYALTIES_CLEANED"].sum() / 100  # Ajuste para remover dois zeros extras
            st.write(f"**Soma total de royalties:** R$ {total_royalties:,.2f}")
        except ValueError:
            st.error("Erro ao calcular a soma dos royalties. Verifique os dados.")
else:
    st.write("Nenhum dado encontrado na Planilha 1.")

# Exibir Planilha 2
st.subheader("Planilha 2")
if not df2_filtered.empty:
    st.dataframe(df2_filtered, use_container_width=True)
else:
    st.write("Nenhum dado encontrado na Planilha 2.")