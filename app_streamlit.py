#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import streamlit as st
import pandas as pd
import requests
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import time

st.set_page_config(
    page_title="Consultor CNPJ com Localidades",
    page_icon="search",
    layout="wide"
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class APILocalidades:
    def __init__(self):
        self.cache_municipios = {}
        self.base_url = "https://servicodados.ibge.gov.br/api/v1/localidades"
    
    def obter_municipios_por_uf(self, uf: str) -> List[str]:
        if uf in self.cache_municipios:
            return self.cache_municipios[uf]
        
        try:
            url = f"{self.base_url}/estados/{uf}/municipios"
            response = requests.get(url, timeout=5)
            
            if response.status_code == 200:
                municipios = [m['nome'].upper() for m in response.json()]
                self.cache_municipios[uf] = municipios
                return municipios
        except Exception as e:
            logger.warning(f"Erro ao obter municipios: {e}")
        
        return []
    
    def normalizar_municipio(self, municipio: str, uf: str) -> Optional[str]:
        municipios = self.obter_municipios_por_uf(uf)
        municipio_upper = municipio.upper()
        
        if municipio_upper in municipios:
            return municipio_upper
        
        for mun in municipios:
            if municipio_upper in mun or mun in municipio_upper:
                return mun
        
        return None

class ConsultorCNPJ:
    def __init__(self):
        self.cache = {}
        self.headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        self.api_localidades = APILocalidades()
    
    def consultar_brasilapi(self, cnpj: str) -> Optional[Dict]:
        try:
            cnpj_limpo = cnpj.replace('.', '').replace('/', '').replace('-', '')
            
            if cnpj_limpo in self.cache:
                return self.cache[cnpj_limpo]
            
            url = f"https://brasilapi.com.br/api/cnpj/v1/{cnpj_limpo}"
            response = requests.get(url, headers=self.headers, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                resultado = {
                    'cnpj': cnpj,
                    'razao_social': data.get('razao_social', 'N/A'),
                    'nome_fantasia': data.get('nome_fantasia', 'N/A'),
                    'municipio': data.get('municipio', 'N/A'),
                    'uf': data.get('uf', 'N/A'),
                    'logradouro': data.get('logradouro', 'N/A'),
                    'numero': data.get('numero', 'N/A'),
                    'bairro': data.get('bairro', 'N/A'),
                    'cep': data.get('cep', 'N/A'),
                    'cnae': data.get('cnae_fiscal_descricao', 'N/A'),
                    'cnae_codigo': data.get('cnae_fiscal', 'N/A'),
                    'natureza_juridica': data.get('natureza_juridica_descricao', 'N/A'),
                    'status': 'ATIVO' if data.get('status') == 'ATIVA' else 'INATIVO',
                    'data_consulta': datetime.now().isoformat()
                }
                self.cache[cnpj_limpo] = resultado
                return resultado
        except Exception as e:
            logger.warning(f"Erro ao consultar: {e}")
        
        return None
    
    def consultar_cnpj(self, cnpj: str) -> Dict:
        resultado = self.consultar_brasilapi(cnpj)
        
        if resultado is None:
            resultado = {
                'cnpj': cnpj,
                'razao_social': 'N/A',
                'nome_fantasia': 'N/A',
                'municipio': 'N/A',
                'uf': 'N/A',
                'logradouro': 'N/A',
                'numero': 'N/A',
                'bairro': 'N/A',
                'cep': 'N/A',
                'cnae': 'N/A',
                'cnae_codigo': 'N/A',
                'natureza_juridica': 'N/A',
                'status': 'ERRO',
                'data_consulta': datetime.now().isoformat()
            }
        
        return resultado
    
    def validar_municipio(self, municipio: str, uf: str) -> Tuple[bool, Optional[str]]:
        if uf not in ['AC', 'AL', 'AP', 'AM', 'BA', 'CE', 'DF', 'ES', 'GO', 'MA', 
                      'MT', 'MS', 'MG', 'PA', 'PB', 'PR', 'PE', 'PI', 'RJ', 'RN', 
                      'RS', 'RO', 'RR', 'SC', 'SP', 'SE', 'TO']:
            return False, None
        
        municipio_normalizado = self.api_localidades.normalizar_municipio(municipio, uf)
        
        if municipio_normalizado:
            return True, municipio_normalizado
        
        return False, None

def main():
    st.title("Consultor CNPJ com Validacao de Localidades")
    st.markdown("Busque dados completos de CNPJs e valide localizacao geografica")
    
    consultor = ConsultorCNPJ()
    
    tab1, tab2, tab3 = st.tabs(["Consulta Individual", "Upload em Massa", "Analise"])
    
    with tab1:
        st.header("Consulta Individual de CNPJ")
        
        col1, col2 = st.columns(2)
        
        with col1:
            cnpj_input = st.text_input(
                "Digite o CNPJ",
                placeholder="00.000.000/0000-00"
            )
        
        with col2:
            if st.button("Consultar", key="btn_consultar"):
                if cnpj_input:
                    with st.spinner("Consultando API..."):
                        resultado = consultor.consultar_cnpj(cnpj_input)
                        
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.subheader("Dados Basicos")
                            st.write(f"**CNPJ:** {resultado['cnpj']}")
                            st.write(f"**Razao Social:** {resultado['razao_social']}")
                            st.write(f"**Nome Fantasia:** {resultado['nome_fantasia']}")
                            st.write(f"**Status:** {resultado['status']}")
                        
                        with col2:
                            st.subheader("Localizacao")
                            st.write(f"**Municipio:** {resultado['municipio']}")
                            st.write(f"**UF:** {resultado['uf']}")
                            st.write(f"**CEP:** {resultado['cep']}")
                            
                            if resultado['uf'] != 'N/A' and resultado['municipio'] != 'N/A':
                                valido, mun_norm = consultor.validar_municipio(
                                    resultado['municipio'],
                                    resultado['uf']
                                )
                                if valido:
                                    st.success(f"Municipio validado: {mun_norm}")
                                else:
                                    st.warning("Municipio nao encontrado no IBGE")
                        
                        st.subheader("Endereco Completo")
                        endereco = f"{resultado['logradouro']}, {resultado['numero']} - {resultado['bairro']} - {resultado['municipio']}/{resultado['uf']} - {resultado['cep']}"
                        st.text(endereco)
                        
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.subheader("Atividade")
                            st.write(f"**Codigo CNAE:** {resultado['cnae_codigo']}")
                            st.write(f"**Descricao:** {resultado['cnae']}")
                        
                        with col2:
                            st.subheader("Informacoes Adicionais")
                            st.write(f"**Natureza Juridica:** {resultado['natureza_juridica']}")
                            st.write(f"**Data Consulta:** {resultado['data_consulta']}")
                else:
                    st.error("Digite um CNPJ valido")
    
    with tab2:
        st.header("Upload em Massa")
        
        uploaded_file = st.file_uploader("Selecione arquivo Excel", type=['xlsx'])
        
        if uploaded_file:
            df = pd.read_excel(uploaded_file)
            
            st.write(f"Arquivo carregado: {len(df)} registros")
            st.dataframe(df.head())
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                coluna_cnpj = st.selectbox("Coluna com CNPJ", df.columns)
            
            with col2:
                coluna_uf = st.selectbox("Coluna com UF", df.columns)
            
            with col3:
                coluna_municipio = st.selectbox("Coluna com Municipio (opcional)", 
                                                ["Nenhuma"] + list(df.columns))
            
            if st.button("Processar em Massa", key="btn_processar"):
                resultados = []
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                for idx, row in df.iterrows():
                    cnpj = str(row[coluna_cnpj]).strip()
                    uf_base = str(row[coluna_uf]).strip()
                    
                    resultado = consultor.consultar_cnpj(cnpj)
                    
                    valido, mun_norm = consultor.validar_municipio(
                        resultado['municipio'],
                        resultado['uf']
                    )
                    
                    resultado['Validacao_Municipio'] = 'SIM' if valido else 'NAO'
                    resultado['UF_Base'] = uf_base
                    resultado['Match_UF'] = 'SIM' if uf_base == resultado['uf'] else 'NAO'
                    
                    resultados.append(resultado)
                    
                    progress = (idx + 1) / len(df)
                    progress_bar.progress(progress)
                    status_text.text(f"Processados {idx + 1}/{len(df)}")
                    
                    time.sleep(0.2)
                
                df_resultado = pd.DataFrame(resultados)
                
                st.success("Processamento concluido!")
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    total_processados = len(df_resultado)
                    st.metric("Total Processados", total_processados)
                
                with col2:
                    validos = len(df_resultado[df_resultado['Validacao_Municipio'] == 'SIM'])
                    st.metric("Municipios Validados", validos)
                
                with col3:
                    match_uf = len(df_resultado[df_resultado['Match_UF'] == 'SIM'])
                    st.metric("UF Coincidentes", match_uf)
                
                st.subheader("Dados Processados")
                st.dataframe(df_resultado, use_container_width=True)
                
                csv = df_resultado.to_csv(index=False, sep=';', encoding='utf-8')
                st.download_button(
                    label="Download CSV",
                    data=csv,
                    file_name=f"relatorio_cnpj_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv"
                )
    
    with tab3:
        st.header("Analise de Dados")
        st.info("Carregue um arquivo em massa na aba anterior para ver analises")

if __name__ == "__main__":
    main()
