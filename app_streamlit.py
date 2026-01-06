import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import os
from localization_api import LocalizationAPI, get_regional_stats
import requests
from bs4 import BeautifulSoup
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

st.set_page_config(
    page_title="Empresas - Geolocalização",
    page_icon="earth_globe",
    layout="wide"
)

colors = {
    'primary': '#003398',
    'secondary': '#0066CC',
    'background': '#f8f9fa',
    'text': '#1a1a1a'
}

st.markdown(f"""
    <style>
        [data-testid="stAppViewContainer"] {{
            background-color: {colors['background']};
        }}
        h1, h2, h3 {{
            color: {colors['primary']};
            font-weight: 700;
        }}
        .stButton>button {{
            background-color: {colors['primary']};
            color: white;
        }}
        .stButton>button:hover {{
            background-color: {colors['secondary']};
        }}
    </style>
""", unsafe_allow_html=True)

@st.cache_resource
def init_localization_api():
    """Inicializa API de localidades"""
    return LocalizationAPI()

@st.cache_data
def load_data():
    """Carrega dados do arquivo Excel"""
    file_names = [
        "20251222 - Empresas mapeadas.xlsx",
        "20251222-Empresas-mapeadas.xlsx"
    ]
    
    df = None
    for file_name in file_names:
        try:
            if os.path.exists(file_name):
                df = pd.read_excel(file_name, sheet_name="Mapeamento")
                st.info(f"Carregado: {file_name}")
                return df
        except Exception as e:
            continue
    
    st.error("Arquivo Excel nao encontrado. Verifique se existe na pasta raiz.")
    return None

@st.cache_data
def get_unique_companies(df):
    """Extrai empresas unicas com agregacoes"""
    unique = df.groupby('CNPJ').agg({
        'Empresa': 'first',
        'UF do preço': 'first',
        'Item': 'count'
    }).reset_index()
    unique.columns = ['CNPJ', 'Empresa', 'UF', 'Total_Itens']
    return unique.sort_values('Total_Itens', ascending=False)

def scrape_cnpj_data(cnpj: str) -> dict:
    """
    Realiza web scraping para obter dados da empresa pelo CNPJ
    Utiliza API publica de CNPJ
    """
    try:
        clean_cnpj = cnpj.replace('.', '').replace('-', '').replace('/', '')
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        url = f"https://www.sintegra.gov.br/index.php"
        params = {
            'tipobusca': 1,
            'cnpj': clean_cnpj
        }
        
        response = requests.get(url, params=params, headers=headers, timeout=5)
        
        if response.status_code == 200:
            try:
                soup = BeautifulSoup(response.content, 'html.parser')
                
                result = {
                    'cnpj': cnpj,
                    'status': 'encontrado',
                    'cidade': 'Nao especificada',
                    'uf': 'Nao especificada'
                }
                
                text_content = soup.get_text()
                
                if 'MUNICIPIO' in text_content or 'municipio' in text_content:
                    result['status'] = 'encontrado'
                else:
                    result['status'] = 'incompleto'
                
                return result
            except:
                return {
                    'cnpj': cnpj,
                    'status': 'erro_parse',
                    'cidade': 'Erro ao processar',
                    'uf': 'Erro'
                }
        else:
            return {
                'cnpj': cnpj,
                'status': 'nao_encontrado',
                'cidade': 'Nao disponivel',
                'uf': 'Nao disponivel'
            }
    
    except Exception as e:
        logger.error(f"Erro ao scraping CNPJ {cnpj}: {str(e)}")
        return {
            'cnpj': cnpj,
            'status': 'erro',
            'cidade': f'Erro: {str(e)[:30]}',
            'uf': 'Erro'
        }

def main():
    st.title("Mapeamento de Empresas Fornecedoras")
    st.markdown("Sistema de Geolocalização por CNPJ - FGV IBRE")
    
    loc_api = init_localization_api()
    df = load_data()
    
    if df is None:
        return
    
    unique_companies = get_unique_companies(df)
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Registros", f"{len(df):,}")
    with col2:
        st.metric("CNPJs Unicos", len(unique_companies))
    with col3:
        st.metric("Estados", df['UF do preço'].nunique())
    with col4:
        st.metric("Ultima Atualizacao", datetime.now().strftime("%d/%m/%Y"))
    
    st.divider()
    
    tab1, tab2, tab3, tab4 = st.tabs(["Web Scraping CNPJ", "Analise Geral", "Regioes Metropolitanas", "Validacao de Localidades"])
    
    with tab1:
        st.subheader("Buscar Dados de Empresa por CNPJ")
        st.markdown("Realiza web scraping para obter informacoes de localização da empresa")
        
        col1, col2 = st.columns([3, 1])
        
        with col1:
            search_cnpj = st.text_input(
                "Digite o CNPJ",
                placeholder="XX.XXX.XXX/XXXX-XX",
                key="search_cnpj_input"
            )
        
        with col2:
            search_button = st.button("Buscar", key="search_cnpj_button", use_container_width=True)
        
        if search_button and search_cnpj:
            with st.spinner("Buscando dados..."):
                result = scrape_cnpj_data(search_cnpj)
                
                if result['status'] == 'encontrado':
                    st.success("Empresa encontrada!")
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("CNPJ", result['cnpj'])
                    with col2:
                        st.metric("Cidade", result['cidade'])
                    with col3:
                        st.metric("UF", result['uf'])
                    with col4:
                        st.metric("Status", result['status'])
                else:
                    st.warning(f"Status: {result['status']}")
        
        st.divider()
        st.subheader("Scraping em Lote")
        st.markdown("Realiza web scraping para todos os CNPJs da planilha")
        
        if st.button("Iniciar Scraping de Todos os CNPJs", key="scrape_all"):
            progress_bar = st.progress(0)
            status_text = st.empty()
            results_container = st.container()
            
            scraping_results = []
            total = len(unique_companies)
            
            for idx, (_, row) in enumerate(unique_companies.iterrows()):
                cnpj = row['CNPJ']
                empresa = row['Empresa']
                
                result = scrape_cnpj_data(cnpj)
                result['empresa'] = empresa
                result['uf_base'] = row['UF']
                result['total_itens'] = row['Total_Itens']
                scraping_results.append(result)
                
                progress = (idx + 1) / total
                progress_bar.progress(progress)
                status_text.text(f"Processados {idx + 1} de {total} CNPJs")
            
            results_df = pd.DataFrame(scraping_results)
            results_df = results_df[['cnpj', 'empresa', 'uf_base', 'status', 'cidade', 'total_itens']]
            results_df.columns = ['CNPJ', 'Empresa', 'UF Base', 'Status Scraping', 'Cidade', 'Total Itens']
            
            st.success(f"Scraping concluido! {len(results_df)} registros processados")
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Encontrados", len(results_df[results_df['Status Scraping'] == 'encontrado']))
            with col2:
                st.metric("Nao Encontrados", len(results_df[results_df['Status Scraping'] == 'nao_encontrado']))
            with col3:
                st.metric("Erros", len(results_df[results_df['Status Scraping'].isin(['erro', 'erro_parse'])]))
            
            st.divider()
            st.subheader("Resultados do Scraping")
            st.dataframe(results_df, use_container_width=True, height=500)
            
            csv = results_df.to_csv(index=False)
            st.download_button(
                label="Baixar Resultados em CSV",
                data=csv,
                file_name="scraping_resultados.csv",
                mime="text/csv"
            )
    
    with tab2:
        st.subheader("Distribuicao por UF")
        uf_dist = df['UF do preço'].value_counts()
        
        fig_uf = go.Figure(data=[
            go.Bar(
                x=uf_dist.index,
                y=uf_dist.values,
                marker_color=colors['primary'],
                text=uf_dist.values,
                textposition='auto'
            )
        ])
        fig_uf.update_layout(
            xaxis_title="Estado",
            yaxis_title="Quantidade",
            height=400,
            showlegend=False,
            template="plotly_white"
        )
        st.plotly_chart(fig_uf, use_container_width=True)
        
        st.divider()
        st.subheader("Dados Completos")
        
        cols_display = ['Empresa', 'CNPJ', 'UF', 'Total_Itens']
        df_display = unique_companies[cols_display].copy()
        df_display.columns = ['Empresa', 'CNPJ', 'UF', 'Itens']
        
        st.dataframe(
            df_display,
            use_container_width=True,
            height=400
        )
    
    with tab3:
        st.subheader("Mapa de Regioes Metropolitanas")
        
        if st.button("Analisar Empresas em Regioes Metropolitanas"):
            with st.spinner("Processando dados..."):
                try:
                    metro_analysis = []
                    
                    for idx, row in unique_companies.iterrows():
                        uf = row['UF']
                        empresa = row['Empresa']
                        
                        if uf in loc_api.metropolitan_regions:
                            region_data = loc_api.metropolitan_regions[uf]
                            metro_analysis.append({
                                'UF': uf,
                                'Empresa': empresa,
                                'Regiao Metropolitana': region_data['name'],
                                'Total_Itens': row['Total_Itens']
                            })
                    
                    if metro_analysis:
                        metro_df = pd.DataFrame(metro_analysis)
                        
                        st.success(f"Encontradas {len(metro_df)} empresas em regioes metropolitanas")
                        
                        metro_dist = metro_df['Regiao Metropolitana'].value_counts()
                        fig_metro = go.Figure(data=[
                            go.Bar(
                                x=metro_dist.index,
                                y=metro_dist.values,
                                marker_color=colors['primary']
                            )
                        ])
                        fig_metro.update_layout(
                            title="Distribuicao de Empresas por Regiao Metropolitana",
                            xaxis_title="Regiao Metropolitana",
                            yaxis_title="Quantidade de Empresas",
                            height=400,
                            template="plotly_white"
                        )
                        st.plotly_chart(fig_metro, use_container_width=True)
                        
                        st.subheader("Empresas em Regioes Metropolitanas")
                        st.dataframe(
                            metro_df,
                            use_container_width=True,
                            height=400
                        )
                        
                        csv = metro_df.to_csv(index=False)
                        st.download_button(
                            label="Baixar dados em CSV",
                            data=csv,
                            file_name="empresas_regioes_metropolitanas.csv",
                            mime="text/csv"
                        )
                    else:
                        st.warning("Nenhuma empresa encontrada em regioes metropolitanas")
                
                except Exception as e:
                    st.error(f"Erro ao processar: {str(e)}")
    
    with tab4:
        st.subheader("Validacao de Localidades")
        st.markdown("Verifica se cidades existem em banco de dados IBGE e identifica regioes metropolitanas")
        
        col1, col2 = st.columns(2)
        
        with col1:
            selected_uf = st.selectbox(
                "Selecione um Estado",
                sorted(loc_api.metropolitan_regions.keys())
            )
        
        with col2:
            if st.button("Carregar Cidades", key="load_cities"):
                cities = loc_api.get_cities_by_uf(selected_uf)
                st.success(f"Carregadas {len(cities)} cidades de {selected_uf}")
                
                cities_df = pd.DataFrame({
                    'Cidade': cities,
                    'Regiao Metropolitana': [loc_api.is_metropolitan_area(selected_uf, city)[1] or 'Nao' for city in cities]
                })
                
                st.dataframe(cities_df, use_container_width=True)
        
        st.divider()
        
        st.subheader("Validar Empresa Especifica")
        
        col1, col2 = st.columns(2)
        
        with col1:
            search_uf = st.selectbox("Selecione UF", sorted(unique_companies['UF'].unique()), key="search_uf")
            companies_in_uf = unique_companies[unique_companies['UF'] == search_uf]
            company_options = companies_in_uf['Empresa'].tolist()
            selected_company = st.selectbox("Selecione Empresa", company_options, key="select_company")
        
        with col2:
            if st.button("Validar Empresa", key="validate"):
                company_data = companies_in_uf[companies_in_uf['Empresa'] == selected_company].iloc[0]
                
                st.write(f"**Empresa:** {company_data['Empresa']}")
                st.write(f"**CNPJ:** {company_data['CNPJ']}")
                st.write(f"**UF:** {company_data['UF']}")
                st.write(f"**Total Itens:** {company_data['Total_Itens']}")
                
                is_metro, metro_name = loc_api.is_metropolitan_area(search_uf, "")
                if metro_name:
                    st.success(f"Esta empresa esta em: **{metro_name}**")
                else:
                    st.info("Esta empresa nao esta em regiao metropolitana mapeada")
    
    st.divider()
    with st.expander("Informacoes Detalhadas"):
        st.write(f"Total de registros processados: {len(df)}")
        st.write(f"Empresas unicas: {len(unique_companies)}")
        st.write(f"Periodicidade: Trimestral")
        st.write(f"Data de atualizacao: {datetime.now().strftime('%d/%m/%Y %H:%M')}")

if __name__ == "__main__":
    main()
