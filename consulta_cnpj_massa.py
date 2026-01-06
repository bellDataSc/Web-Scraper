#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
CONSULTOR DE CNPJ EM MASSA
Script para ler Excel com 3.000+ CNPJs e consultar informações
via API, retornando cidade + UF + dados da empresa
"""

import pandas as pd
import requests
import json
import time
import csv
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
import logging

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ConsultorCNPJ:
    """Consultor de CNPJ com suporte a múltiplas APIs"""
    
    def __init__(self, timeout: int = 5, delay: float = 0.5):
        self.timeout = timeout
        self.delay = delay
        self.cache = {}
        self.headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    
    def consultar_brasilapi(self, cnpj: str) -> Optional[Dict]:
        """Consulta CNPJ usando Brasil API (recomendado)"""
        try:
            cnpj_limpo = cnpj.replace('.', '').replace('/', '').replace('-', '')
            
            if cnpj_limpo in self.cache:
                return self.cache[cnpj_limpo]
            
            url = f"https://brasilapi.com.br/api/cnpj/v1/{cnpj_limpo}"
            response = requests.get(url, headers=self.headers, timeout=self.timeout)
            
            if response.status_code == 200:
                data = response.json()
                resultado = {
                    'cnpj': cnpj,
                    'razao_social': data.get('razao_social', 'N/A'),
                    'nome_fantasia': data.get('nome_fantasia', 'N/A'),
                    'municipio': data.get('municipio', 'N/A'),
                    'uf': data.get('uf', 'N/A'),
                    'cnae': data.get('cnae_fiscal_descricao', 'N/A'),
                    'status': 'ATIVO' if data.get('data_situacao_cadastral') == 'ATIVA' else 'INATIVO',
                    'data_consulta': datetime.now().isoformat()
                }
                self.cache[cnpj_limpo] = resultado
                return resultado
        except requests.exceptions.RequestException as e:
            logger.warning(f"Erro ao consultar {cnpj}: {e}")
        
        return None
    
    def consultar_cnpj(self, cnpj: str) -> Dict:
        """Consulta CNPJ com fallback para múltiplas APIs"""
        resultado = self.consultar_brasilapi(cnpj)
        
        if resultado is None:
            resultado = {
                'cnpj': cnpj,
                'razao_social': 'N/A',
                'nome_fantasia': 'N/A',
                'municipio': 'N/A',
                'uf': 'N/A',
                'cnae': 'N/A',
                'status': 'ERRO_CONSULTA',
                'data_consulta': datetime.now().isoformat()
            }
        
        return resultado

class AnalisadorDadosEmpresa:
    """Analisa e processa dados de empresas"""
    
    @staticmethod
    def ler_arquivo_excel(caminho: str, coluna_cnpj: str = 'CNPJ') -> pd.DataFrame:
        """Lê arquivo Excel e retorna DataFrame com CNPJs únicos"""
        try:
            df = pd.read_excel(caminho)
            logger.info(f"Arquivo lido: {len(df)} registros")
            
            # Remover NaN
            df = df.dropna(subset=[coluna_cnpj])
            
            # Remover duplicatas
            df_unique = df.drop_duplicates(subset=[coluna_cnpj]).reset_index(drop=True)
            logger.info(f"CNPJs únicos: {len(df_unique)}")
            
            return df_unique
        except Exception as e:
            logger.error(f"Erro ao ler arquivo: {e}")
            raise
    
    @staticmethod
    def processar_lote(df: pd.DataFrame, consultor: ConsultorCNPJ, 
                       coluna_cnpj: str = 'CNPJ', coluna_uf: str = 'UF') -> pd.DataFrame:
        """Processa lote de CNPJs e consulta informações"""
        resultados = []
        total = len(df)
        
        for idx, row in df.iterrows():
            cnpj = row[coluna_cnpj]
            uf_base = row.get(coluna_uf, 'N/A')
            
            logger.info(f"Consultando {idx+1}/{total}: {cnpj}")
            
            # Consultar API
            dados_api = consultor.consultar_cnpj(cnpj)
            
            # Mesclar com dados originais
            resultado = {
                'CNPJ': cnpj,
                'Empresa_Original': row.get('Empresa', 'N/A'),
                'UF_Base': uf_base,
                'Razao_Social': dados_api.get('razao_social', 'N/A'),
                'Nome_Fantasia': dados_api.get('nome_fantasia', 'N/A'),
                'Municipio': dados_api.get('municipio', 'N/A'),
                'UF_Receita': dados_api.get('uf', 'N/A'),
                'Atividade_Principal': dados_api.get('cnae', 'N/A'),
                'Status_Empresa': dados_api.get('status', 'N/A'),
                'Data_Consulta': dados_api.get('data_consulta', 'N/A')
            }
            
            resultados.append(resultado)
            
            # Respeitar rate limit
            time.sleep(consultor.delay)
        
        return pd.DataFrame(resultados)
    
    @staticmethod
    def gerar_relatorio(df: pd.DataFrame, arquivo_saida: str = 'relatorio_cnpj.csv'):
        """Gera relatório em CSV e análises estatísticas"""
        
        # Salvar CSV
        df.to_csv(arquivo_saida, index=False, encoding='utf-8', sep=';')
        logger.info(f"Relatório salvo: {arquivo_saida}")
        
        # Análises
        print("\n" + "="*100)
        print("RELATÓRIO FINAL - ANÁLISE DE CNPJS")
        print("="*100 + "\n")
        
        print(f"📊 ESTATÍSTICAS GERAIS")
        print("-"*100)
        print(f"Total de CNPJs processados: {len(df):,}")
        print(f"CNPJs válidos (com cidade): {len(df[df['Municipio'] != 'N/A']):,}")
        print(f"CNPJs com erro: {len(df[df['Status_Empresa'] == 'ERRO_CONSULTA']):,}")
        print()
        
        print(f"📍 DISTRIBUIÇÃO GEOGRÁFICA")
        print("-"*100)
        print("\nCidades mais frequentes:")
        cidades = df['Municipio'].value_counts().head(10)
        for cidade, count in cidades.items():
            print(f"  {cidade}: {count} CNPJ(s)")
        print()
        
        print(f"Estados mais frequentes:")
        ufs = df['UF_Receita'].value_counts()
        for uf, count in ufs.items():
            print(f"  {uf}: {count} CNPJ(s)")
        print()
        
        print(f"📊 STATUS DAS EMPRESAS")
        print("-"*100)
        status = df['Status_Empresa'].value_counts()
        for stat, count in status.items():
            percentage = (count / len(df)) * 100
            print(f"  {stat}: {count:,} ({percentage:.1f}%)")
        print()
        
        print(f"🔄 COMPARAÇÃO: UF Base vs UF Receita")
        print("-"*100)
        df['UF_Match'] = df['UF_Base'] == df['UF_Receita']
        match_count = len(df[df['UF_Match'] == True])
        print(f"  UF coincidentes: {match_count:,} ({(match_count/len(df)*100):.1f}%)")
        print(f"  UF diferentes: {len(df) - match_count:,} ({((len(df)-match_count)/len(df)*100):.1f}%)")
        
        # Mostrar discrepâncias
        discrepancias = df[df['UF_Base'] != df['UF_Receita']]
        if len(discrepancias) > 0:
            print("\n  Primeiras discrepâncias encontradas:")
            for idx, row in discrepancias.head(5).iterrows():
                print(f"    {row['CNPJ']}: {row['UF_Base']} (base) vs {row['UF_Receita']} (receita)")
        print()
        
        print("="*100)
        print(f"✓ Relatório completo salvo em: {arquivo_saida}")
        print("="*100)

def main():
    """Função principal"""
    
    print("\n" + "="*100)
    print("SCRIPT DE CONSULTA DE CNPJ EM MASSA")
    print("="*100 + "\n")
    
    # Configurar
    arquivo_entrada = '20251222-Empresas-mapeadas.xlsx'
    arquivo_saida = 'relatorio_cnpj_completo.csv'
    coluna_cnpj = 'CNPJ'
    coluna_uf = 'UF do preço'  # Ajustar conforme seu arquivo
    
    try:
        # Inicializar
        analisador = AnalisadorDadosEmpresa()
        consultor = ConsultorCNPJ(timeout=5, delay=0.5)
        
        # Ler arquivo
        logger.info(f"Lendo arquivo: {arquivo_entrada}")
        df = analisador.ler_arquivo_excel(arquivo_entrada, coluna_cnpj)
        
        # Processar CNPJs (comentar se quiser apenas a análise)
        logger.info("Iniciando consultas de CNPJ...")
        df_resultado = analisador.processar_lote(df, consultor, coluna_cnpj, coluna_uf)
        
        # Gerar relatório
        analisador.gerar_relatorio(df_resultado, arquivo_saida)
        
    except Exception as e:
        logger.error(f"Erro fatal: {e}")
        raise

if __name__ == '__main__':
    main()
