import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from pathlib import Path
import numpy as np
from datetime import datetime

st.set_page_config(
    page_title="Mapa de Empresas - FGV/IBRE",
    page_icon="🗺️",
    layout="wide",
    initial_sidebar_state="expanded"
)

colors_fgv = {
    'primary': '#003398',      # Azul FGV
    'secondary': '#0066CC',    # Azul claro
    'accent': '#FFB81C',       # Amarelo
    'dark': '#1a1a1a',
    'light': '#f8f9fa',
    'white': '#ffffff'
}

st.markdown(f"""
    <style>
        :root {{
            --primary-color: {colors_fgv['primary']};
            --secondary-color: {colors_fgv['secondary']};
        }}
        
        * {{
            margin: 0;
            padding: 0;
        }}
        
        html, body, [data-testid="stAppViewContainer"] {{
            background-color: {colors_fgv['light']};
        }}
        
        [data-testid="stHeader"] {{
            background-color: {colors_fgv['primary']};
        }}
        
        .main {{
            background-color: {colors_fgv['light']};
        }}
        
        h1, h2, h3 {{
            color: {colors_fgv['primary']};
            font-weight: 700;
        }}
        
        .stButton>button {{
            background-color: {colors_fgv['primary']};
            color: white;
            border-radius: 8px;
            border: none;
            padding: 10px 24px;
            font-weight: 600;
            transition: all 0.3s ease;
        }}
        
        .stButton>button:hover {{
            background-color: {colors_fgv['secondary']};
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0, 51, 152, 0.3);
        }}
        
        .metric-card {{
            background: white;
            padding: 20px;
            border-radius: 12px;
            border-left: 4px solid {colors_fgv['primary']};
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
        }}
        
        .header-bar {{
            background: linear-gradient(135deg, {colors_fgv['primary']} 0%, {colors_fgv['secondary']} 100%);
            padding: 40px;
            border-radius: 12px;
            margin-bottom: 30px;
            color: white;
            box-shadow: 0 4px 16px rgba(0, 51, 152, 0.2);
        }}
        
        .info-box {{
            background: linear-gradient(135deg, rgba(0, 51, 152, 0.1) 0%, rgba(0, 102, 204, 0.05) 100%);
            padding: 20px;
            border-radius: 10px;
            border: 1px solid {colors_fgv['primary']};
            margin: 15px 0;
        }}
        
        .status-badge {{
            display: inline-block;
            padding: 6px 16px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 600;
        }}
        
        .status-processado {{
            background-color: #d4edda;
            color: #155724;
        }}
        
        .status-pendente {{
            background-color: #fff3cd;
            color: #856404;
        }}
        
        .status-erro {{
            background-color: #f8d7da;
            color: #721c24;
        }}
        
    </style>
""", unsafe_allow_html=True)

def load_data():
    """Carrega dados do Excel"""
    try:
        df = pd.read_excel("20251222-Empresas-mapeadas.xlsx", sheet_name="Mapeamento")
        return df
    except FileNotFoundError:
        return None

def get_unique_companies(df):
    """Extrai lista única de empresas"""
    unique = df.groupby('CNPJ').agg({
        'Empresa': 'first',
        'UF do preço': 'first',
        'Item': 'count'
    }).reset_index()
    unique.columns = ['CNPJ', 'Empresa', 'UF', 'Total_Itens']
    return unique.sort_values('Total_Itens', ascending=False)

def display_header():
    """Exibe header com branding FGV"""
    st.markdown("""
        <div class="header-bar">
            <h1 style="margin: 0; color: white;">🗺️ Mapa de Empresas Fornecedoras</h1>
            <p style="margin: 10px 0 0 0; color: rgba(255,255,255,0.9); font-size: 16px;">
                Sistema de Geolocalização de CNPJs - FGV/IBRE
            </p>
        </div>
    """, unsafe_allow_html=True)

def display_statistics(df, unique_companies):
    """Exibe estatísticas principais"""
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            label="Total de Registros",
            value=f"{len(df):,}",
            delta="Produtos/Serviços",
            delta_color="off"
        )
    
    with col2:
        st.metric(
            label="CNPJs Únicos",
            value=len(unique_companies),
            delta="Empresas",
            delta_color="off"
        )
    
    with col3:
        st.metric(
            label="Estados Representados",
            value=df['UF do preço'].nunique(),
            delta="UFs",
            delta_color="off"
        )
    
    with col4:
        st.metric(
            label="Periodicidade",
            value="Trimestral",
            delta="Atualização",
            delta_color="off"
        )

def display_company_table(unique_companies):
    """Exibe tabela de empresas com formatação"""
    st.subheader("📊 Empresas Mapeadas")
    
    cols_display = ['Empresa', 'CNPJ', 'UF', 'Total_Itens']
    df_display = unique_companies[cols_display].copy()
    df_display.columns = ['Empresa', 'CNPJ', 'UF', 'Itens']
    
    st.dataframe(
        df_display,
        use_container_width=True,
        height=400,
        column_config={
            "Empresa": st.column_config.TextColumn("Empresa"),
            "CNPJ": st.column_config.TextColumn("CNPJ"),
            "UF": st.column_config.TextColumn("UF", width="small"),
            "Itens": st.column_config.NumberColumn("Itens", width="small")
        }
    )

def display_distribution_charts(df, unique_companies):
    """Exibe gráficos de distribuição"""
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📈 Distribuição por UF")
        uf_dist = df['UF do preço'].value_counts()
        
        fig_uf = go.Figure(data=[
            go.Bar(
                x=uf_dist.index,
                y=uf_dist.values,
                marker_color=colors_fgv['primary'],
                text=uf_dist.values,
                textposition='auto',
            )
        ])
        fig_uf.update_layout(
            xaxis_title="Estado",
            yaxis_title="Quantidade",
            height=400,
            showlegend=False,
            template="plotly_white",
            hovermode='x unified',
            font=dict(size=11, color=colors_fgv['dark'])
        )
        st.plotly_chart(fig_uf, use_container_width=True)
    
    with col2:
        st.subheader("🏢 Top 10 Empresas por Itens")
        top_10 = unique_companies.nlargest(10, 'Total_Itens')
        
        fig_top = go.Figure(data=[
            go.Bar(
                y=top_10['Empresa'].str[:25],
                x=top_10['Total_Itens'],
                orientation='h',
                marker_color=colors_fgv['secondary'],
                text=top_10['Total_Itens'],
                textposition='auto',
            )
        ])
        fig_top.update_layout(
            xaxis_title="Quantidade de Itens",
            height=400,
            showlegend=False,
            template="plotly_white",
            hovermode='y unified',
            font=dict(size=11, color=colors_fgv['dark'])
        )
        st.plotly_chart(fig_top, use_container_width=True)

def display_status_info():
    """Exibe informações sobre o status do scraping"""
    st.markdown("""
        <div class="info-box">
            <h3 style="margin-top: 0;">🤖 Status do Web Scraper</h3>
            <p><strong>Funcionalidade:</strong> Sistema automático para extração de cidades por CNPJ</p>
            <p><strong>Fontes disponíveis:</strong></p>
            <ul style="margin: 10px 0;">
                <li>Sintegra (Base de dados de ICMS)</li>
                <li>Receita Federal</li>
                <li>CNJ (Conselho Nacional de Justiça)</li>
            </ul>
            <p><strong>Status:</strong> 
                <span class="status-badge status-pendente">Pronto para Deploy</span>
            </p>
        </div>
    """, unsafe_allow_html=True)

def main():
    display_header()
    
    df = load_data()
    
    if df is None:
        st.error("❌ Erro ao carregar arquivo. Verifique se '20251222-Empresas-mapeadas.xlsx' está na pasta.")
        return
    
    unique_companies = get_unique_companies(df)
    
    st.markdown("---")
    display_statistics(df, unique_companies)
    
    st.markdown("---")
    display_distribution_charts(df, unique_companies)
    
    st.markdown("---")
    display_company_table(unique_companies)
    
    st.markdown("---")
    col1, col2 = st.columns([2, 1])
    
    with col1:
        display_status_info()
    
    with col2:
        st.markdown(f"""
            <div class="info-box">
                <h3 style="margin-top: 0;">ℹ️ Informações</h3>
                <p><strong>Última atualização:</strong><br>{datetime.now().strftime('%d/%m/%Y %H:%M')}</p>
                <p><strong>Total registros:</strong><br>{len(df):,}</p>
                <p><strong>Empresas únicas:</strong><br>{len(unique_companies)}</p>
            </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    st.markdown("""
        <div style="text-align: center; margin-top: 40px; color: #666; font-size: 12px;">
            <p>Desenvolvido por FGV/IBRE • 2026</p>
            <p style="margin-top: 5px;">
                Visite: <a href="https://www.fgv.br/ibre" target="_blank">FGV IBRE</a> | 
                <a href="https://github.com" target="_blank">GitHub</a>
            </p>
        </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
