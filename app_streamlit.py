import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import os
from localization_api import LocalizationAPI, get_regional_stats

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
    
    tab1, tab2, tab3 = st.tabs(["Analise Geral", "Regioes Metropolitanas", "Validacao de Localidades"])
    
    with tab1:
        col1, col2 = st.columns(2)
        
        with col1:
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
        
        with col2:
            st.subheader("Top 10 Empresas por Itens")
            top_10 = unique_companies.nlargest(10, 'Total_Itens')
            
            fig_top = go.Figure(data=[
                go.Bar(
                    y=top_10['Empresa'].str[:30],
                    x=top_10['Total_Itens'],
                    orientation='h',
                    marker_color=colors['secondary'],
                    text=top_10['Total_Itens'],
                    textposition='auto'
                )
            ])
            fig_top.update_layout(
                xaxis_title="Quantidade de Itens",
                height=400,
                showlegend=False,
                template="plotly_white"
            )
            st.plotly_chart(fig_top, use_container_width=True)
        
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
    
    with tab2:
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
    
    with tab3:
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
