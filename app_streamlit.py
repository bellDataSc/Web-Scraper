
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime

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

@st.cache_data
def load_data():
    """Carrega dados do arquivo Excel"""
    try:
        df = pd.read_excel("20251222 - Empresas mapeadas.xlsx", sheet_name="Mapeamento")
        return df
    except FileNotFoundError:
        st.error("20251222 - Empresas mapeadas.xlsx nao encontrado")
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
    
    with st.expander("Informacoes Detalhadas"):
        st.write(f"Total de registros processados: {len(df)}")
        st.write(f"Empresas unicas: {len(unique_companies)}")
        st.write(f"Periodicidade: Trimestral")
        st.write(f"Data de atualizacao: {datetime.now().strftime('%d/%m/%Y %H:%M')}")

if __name__ == "__main__":
    main()
