import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import os
from localization_api import LocalizationAPI
from cnpj_scraper import CNPJScraper
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

@st.cache_resource
def init_cnpj_scraper():
    """Inicializa scraper de CNPJ"""
    return CNPJScraper()

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

def main():
    st.title("Mapeamento de Empresas Fornecedoras")
    st.markdown("Sistema de Geolocalização por CNPJ - FGV IBRE")
    
    loc_api = init_localization_api()
    cnpj_scraper = init_cnpj_scraper()
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
        st.subheader("Consultar Dados de Empresa por CNPJ")
        st.markdown("Realiza web scraping da Receita Federal e Sintegra para obter informacoes cadastrais completas")
        st.warning("Processamento pode levar alguns segundos por CNPJ. Use com moderacao para nao sobrecarregar as fontes.")
        
        col1, col2 = st.columns([3, 1])
        
        with col1:
            search_cnpj = st.text_input(
                "Digite o CNPJ",
                placeholder="XX.XXX.XXX/XXXX-XX ou somente numeros",
                key="search_cnpj_input"
            )
        
        with col2:
            search_button = st.button("Buscar", key="search_cnpj_button", use_container_width=True)
        
        if search_button and search_cnpj:
            with st.spinner("Buscando dados na Receita Federal e Sintegra..."):
                result = cnpj_scraper.scrape_cnpj(search_cnpj)
                
                if result['status'] == 'encontrado':
                    st.success("Empresa encontrada!")
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.metric("CNPJ", result['cnpj'])
                        st.metric("Cidade", result['cidade'])
                        st.metric("UF", result['uf'])
                        st.metric("CEP", result['cep'])
                    
                    with col2:
                        st.metric("Razao Social", result['razao_social'])
                        st.metric("Nome Fantasia", result['nome_fantasia'])
                        st.metric("Endereco", f"{result['logradouro']}, {result['numero']}")
                        st.metric("Fonte", result['fonte'].replace('_', ' ').title())
                
                elif result['status'] == 'nao_encontrado':
                    st.warning("Empresa nao encontrada em Receita Federal ou Sintegra")
                    st.info("Verifique se o CNPJ foi digitado corretamente")
                else:
                    st.error(f"Erro ao buscar: {result['status']}")
        
        st.divider()
        st.subheader("Realizar Web Scraping em Lote")
        st.markdown("""**Atencao**: Processamento em lote pode levar muito tempo (aprox. 2-3 segundos por CNPJ). 
Para ã visualizar resultados parciais, monitore o progresso.""")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            quantidade = st.number_input(
                "Quantos CNPJs processar (começando pelos primeiros)",
                min_value=1,
                max_value=len(unique_companies),
                value=10,
                step=1
            )
        
        with col2:
            if st.button("Iniciar Scraping", key="scrape_all", use_container_width=True):
                st.session_state.scraping_started = True
        
        with col3:
            if st.button("Parar Scraping", key="stop_scrape", use_container_width=True):
                st.session_state.scraping_started = False
                st.info("Scraping pausado")
        
        if st.session_state.get('scraping_started', False):
            progress_bar = st.progress(0)
            status_text = st.empty()
            results_container = st.container()
            
            def progress_callback(current, total):
                progress = current / total
                progress_bar.progress(progress)
                status_text.text(f"Processados {current} de {total} CNPJs - Aprox. {current * 2} segundos decorridos")
            
            cnpjs_to_process = unique_companies.head(quantidade)['CNPJ'].tolist()
            scraping_results = cnpj_scraper.scrape_batch(
                cnpjs_to_process,
                progress_callback=progress_callback
            )
            
            scraping_results = scraping_results[['cnpj', 'razao_social', 'nome_fantasia', 'cidade', 'uf', 'logradouro', 'numero', 'cep', 'status', 'fonte']]
            scraping_results.columns = ['CNPJ', 'Razao Social', 'Nome Fantasia', 'Cidade', 'UF', 'Logradouro', 'Numero', 'CEP', 'Status', 'Fonte']
            
            st.success(f"Busca concluida! {len(scraping_results)} registros processados")
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Encontrados", len(scraping_results[scraping_results['Status'] == 'encontrado']))
            with col2:
                st.metric("Nao Encontrados", len(scraping_results[scraping_results['Status'] == 'nao_encontrado']))
            with col3:
                st.metric("Erros", len(scraping_results[scraping_results['Status'] == 'erro']))
            
            st.divider()
            st.subheader("Resultados")
            st.dataframe(scraping_results, use_container_width=True, height=500)
            
            csv = scraping_results.to_csv(index=False)
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
        st.markdown("Verifica cidades contra banco de dados IBGE")
        
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
    with st.expander("Informacoes Detalhadas"):
        st.write(f"Total de registros processados: {len(df)}")
        st.write(f"Empresas unicas: {len(unique_companies)}")
        st.write(f"Periodicidade: Trimestral")
        st.write(f"Data de atualizacao: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
        st.write("""**Fontes de dados CNPJ:**
        - Receita Federal (Prioridade)
        - Sintegra - Sistema de Integrados Estaduais (Fallback)
        """)

if __name__ == "__main__":
    main()
