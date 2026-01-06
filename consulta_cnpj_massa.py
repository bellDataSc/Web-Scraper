#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
CONSULTOR DE CNPJ EM MASSA
Script para ler Excel com 3.000+ CNPJs e consultar informações
via API, retornando cidade + UF + dados da empresa com validação geográfica
"""

import pandas as pd
import requests
import json
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class APILocalidades:
    """API de localidades (IBGE) para validação de UF/Município"""
    
    def __init__(self):
        self.cache_municipios = {}
        self.cache_ufs = {}
        self.base_url = "https://servicodados.ibge.gov.br/api/v1/localidades"
    
    def obter_municipios_por_uf(self, uf: str) -> List[str]:
        """Retorna lista de municípios para um UF"""
        if uf in self.cache_municipios:
            return self.cache_municipios[uf]
        
        try:
            url = f"{self.base_url}/estados/{uf}/municipios"
            response = requests.get(url, timeout=5)
            
            if response.status_code == 200:
                municipios = [m['nome'].upper() for m in response.json()]
                self.cache_municipios[uf] = municipios
                logger.info(f"Carregados {len(municipios)} municipios para {uf}")
                return municipios
        except Exception as e:
            logger.warning(f"Erro ao obter municipios de {uf}: {e}")
        
        return []
    
    def validar_municipio(self, municipio: str, uf: str) -> bool:
        """Valida se um município existe em um UF"""
        municipios = self.obter_municipios_por_uf(uf)
        return municipio.upper() in municipios
    
    def normalizar_municipio(self, municipio: str, uf: str) -> Optional[str]:
        """Retorna nome normalizado do município"""
        municipios = self.obter_municipios_por_uf(uf)
        municipio_upper = municipio.upper()
        
        if municipio_upper in municipios:
            return municipio_upper
        
        for mun in municipios:
            if municipio_upper in mun or mun in municipio_upper:
                return mun
        
        return None

class ConsultorCNPJ:
    """Consultor de CNPJ com suporte a múltiplas APIs"""
    
    def __init__(self, timeout: int = 5, delay: float = 0.5):
        self.timeout = timeout
        self.delay = delay
        self.cache = {}
        self.headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        self.api_localidades = APILocalidades()
    
    def consultar_brasilapi(self, cnpj: str) -> Optional[Dict]:
        """Consulta CNPJ usando Brasil API"""
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
                    'logradouro': data.get('logradouro', 'N/A'),
                    'numero': data.get('numero', 'N/A'),
                    'complemento': data.get('complemento', 'N/A'),
                    'bairro': data.get('bairro', 'N/A'),
                    'cep': data.get('cep', 'N/A'),
                    'cnae': data.get('cnae_fiscal_descricao', 'N/A'),
                    'cnae_codigo': data.get('cnae_fiscal', 'N/A'),
                    'natureza_juridica': data.get('natureza_juridica_descricao', 'N/A'),
                    'status': 'ATIVO' if data.get('status') == 'ATIVA' else 'INATIVO',
                    'data_situacao': data.get('data_situacao_cadastral', 'N/A'),
                    'data_consulta': datetime.now().isoformat()
                }
                self.cache[cnpj_limpo] = resultado
                return resultado
        except requests.exceptions.RequestException as e:
            logger.warning(f"Erro ao consultar {cnpj}: {e}")
        
        return None
    
    def consultar_cnpj(self, cnpj: str) -> Dict:
        """Consulta CNPJ com fallback"""
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
                'complemento': 'N/A',
                'bairro': 'N/A',
                'cep': 'N/A',
                'cnae': 'N/A',
                'cnae_codigo': 'N/A',
                'natureza_juridica': 'N/A',
                'status': 'ERRO_CONSULTA',
                'data_situacao': 'N/A',
                'data_consulta': datetime.now().isoformat()
            }
        
        return resultado
    
    def validar_localizacao(self, municipio: str, uf: str) -> Tuple[bool, str]:
        """Valida e normaliza municipio/UF"""
        if uf not in ['AC', 'AL', 'AP', 'AM', 'BA', 'CE', 'DF', 'ES', 'GO', 'MA', 
                      'MT', 'MS', 'MG', 'PA', 'PB', 'PR', 'PE', 'PI', 'RJ', 'RN', 
                      'RS', 'RO', 'RR', 'SC', 'SP', 'SE', 'TO']:
            return False, "UF_INVALIDO"
        
        municipio_normalizado = self.api_localidades.normalizar_municipio(municipio, uf)
        
        if municipio_normalizado:
            return True, municipio_normalizado
        
        return False, municipio

class AnalisadorDadosEmpresa:
    """Analisa e processa dados de empresas com cruzamento geográfico"""
    
    def __init__(self):
        self.consultor = ConsultorCNPJ(timeout=5, delay=0.3)
        self.regioes_metropo = self._mapear_regioes_metropolitanas()
    
    def _mapear_regioes_metropolitanas(self) -> Dict[str, List[str]]:
        """Mapa de regiões metropolitanas brasileiras"""
        return {
            'RM_SAOPAULO': {
                'uf': 'SP',
                'municipios': ['SAO PAULO', 'GUARULHOS', 'CAMPINAS', 'SANTO ANDRE', 
                              'SÃO BERNARDO DO CAMPO', 'DIADEMA', 'MAUA', 'OSASCO']
            },
            'RM_RIO': {
                'uf': 'RJ',
                'municipios': ['RIO DE JANEIRO', 'NITEROI', 'SAO GONCALO', 'DUQUE DE CAXIAS', 
                              'NOVA IGUACU', 'SÃO JOÃO DE MERITI', 'NILÓPOLIS']
            },
            'RM_BELO_HORIZONTE': {
                'uf': 'MG',
                'municipios': ['BELO HORIZONTE', 'CONTAGEM', 'BETIM', 'SABARA', 
                              'NOVA LIMA', 'BRUMADINHO', 'RIBEIRÃO DAS NEVES']
            },
            'RM_BRASILIA': {
                'uf': 'DF',
                'municipios': ['BRASILIA', 'TAGUATINGA', 'CEILANDIA', 'GUARA']
            },
            'RM_CURITIBA': {
                'uf': 'PR',
                'municipios': ['CURITIBA', 'ARAUCARIA', 'CAMPO LARGO', 'COLOMBO', 'PINHAIS']
            },
            'RM_PORTO_ALEGRE': {
                'uf': 'RS',
                'municipios': ['PORTO ALEGRE', 'VIAMAO', 'CANOAS', 'GRAVATAÍ', 'ALVORADA']
            },
            'RM_SALVADOR': {
                'uf': 'BA',
                'municipios': ['SALVADOR', 'LAURO DE FREITAS', 'CAMAÇARI', 'SIMÕES FILHO']
            },
            'RM_RECIFE': {
                'uf': 'PE',
                'municipios': ['RECIFE', 'JABOATAO DOS GUARARAPES', 'OLINDA', 'PAULISTA']
            },
            'RM_FORTALEZA': {
                'uf': 'CE',
                'municipios': ['FORTALEZA', 'MARACANAÚ', 'CAUCAIA', 'AQUIRAZ']
            },
            'RM_MANAUS': {
                'uf': 'AM',
                'municipios': ['MANAUS', 'ITACOATIARA', 'IRANDUBA']
            }
        }
    
    def identificar_regiao_metro(self, municipio: str, uf: str) -> Optional[str]:
        """Identifica se município está em região metropolitana"""
        municipio_upper = municipio.upper()
        
        for regiao, dados in self.regioes_metropo.items():
            if dados['uf'] == uf:
                for mun in dados['municipios']:
                    if municipio_upper in mun or mun in municipio_upper:
                        return regiao
        
        return None
    
    @staticmethod
    def ler_arquivo_excel(caminho: str, coluna_cnpj: str = 'CNPJ') -> pd.DataFrame:
        """Lê arquivo Excel"""
        try:
            df = pd.read_excel(caminho)
            logger.info(f"Arquivo lido: {len(df)} registros")
            
            df = df.dropna(subset=[coluna_cnpj])
            df_unique = df.drop_duplicates(subset=[coluna_cnpj]).reset_index(drop=True)
            logger.info(f"CNPJs unicos: {len(df_unique)}")
            
            return df_unique
        except Exception as e:
            logger.error(f"Erro ao ler arquivo: {e}")
            raise
    
    def processar_lote(self, df: pd.DataFrame, coluna_cnpj: str = 'CNPJ', 
                       coluna_uf: str = 'UF do preco', coluna_municipio: str = None) -> pd.DataFrame:
        """Processa lote com cruzamento de dados"""
        resultados = []
        total = len(df)
        
        for idx, row in df.iterrows():
            cnpj = str(row[coluna_cnpj]).strip()
            uf_base = str(row.get(coluna_uf, 'N/A')).strip()
            municipio_base = str(row.get(coluna_municipio, 'N/A')).strip() if coluna_municipio else 'N/A'
            
            logger.info(f"Processando {idx+1}/{total}: {cnpj}")
            
            dados_api = self.consultor.consultar_cnpj(cnpj)
            
            validacao_uf, uf_normalizado = self.consultor.validar_localizacao(
                dados_api['municipio'], dados_api['uf']
            )
            
            municipio_api = dados_api['municipio']
            uf_api = dados_api['uf']
            
            validacao_municipio = False
            if validacao_uf and municipio_api != 'N/A':
                validacao_municipio, municipio_normalizado = self.consultor.validar_localizacao(
                    municipio_api, uf_api
                )
                municipio_api = municipio_normalizado if municipio_normalizado else municipio_api
            
            regiao_metro = self.identificar_regiao_metro(municipio_api, uf_api) if validacao_municipio else None
            
            match_uf = 'SIM' if uf_base == uf_api else 'NAO'
            match_municipio = 'SIM' if municipio_base.upper() in municipio_api.upper() else 'NAO'
            
            resultado = {
                'CNPJ': cnpj,
                'Empresa_Original': row.get('Empresa', 'N/A'),
                'UF_Origem': uf_base,
                'Municipio_Origem': municipio_base,
                'Razao_Social': dados_api['razao_social'],
                'Nome_Fantasia': dados_api['nome_fantasia'],
                'Municipio_API': municipio_api,
                'UF_API': uf_api,
                'Validacao_Municipio': 'SIM' if validacao_municipio else 'NAO',
                'Regiao_Metropolitana': regiao_metro if regiao_metro else 'N/A',
                'Match_UF': match_uf,
                'Match_Municipio': match_municipio,
                'Logradouro': dados_api['logradouro'],
                'Numero': dados_api['numero'],
                'Bairro': dados_api['bairro'],
                'CEP': dados_api['cep'],
                'CNAE': dados_api['cnae'],
                'CNAE_Codigo': dados_api['cnae_codigo'],
                'Natureza_Juridica': dados_api['natureza_juridica'],
                'Status': dados_api['status'],
                'Data_Situacao': dados_api['data_situacao'],
                'Data_Consulta': dados_api['data_consulta']
            }
            
            resultados.append(resultado)
            time.sleep(self.consultor.delay)
        
        return pd.DataFrame(resultados)
    
    @staticmethod
    def gerar_relatorio(df: pd.DataFrame, arquivo_saida: str = 'relatorio_cnpj_completo.csv'):
        """Gera relatório com estatísticas"""
        
        df.to_csv(arquivo_saida, index=False, encoding='utf-8', sep=';')
        logger.info(f"Relatorio salvo: {arquivo_saida}")
        
        print("\n" + "="*120)
        print("RELATORIO FINAL - ANALISE DE CNPJS COM VALIDACAO GEOGRAFICA")
        print("="*120 + "\n")
        
        print("ESTATISTICAS GERAIS")
        print("-"*120)
        print(f"Total de CNPJs processados: {len(df):,}")
        print(f"CNPJs com dados completos: {len(df[df['Status'] != 'ERRO_CONSULTA']):,}")
        print(f"CNPJs com erro: {len(df[df['Status'] == 'ERRO_CONSULTA']):,}")
        print()
        
        print("VALIDACAO GEOGRAFICA")
        print("-"*120)
        validos = len(df[df['Validacao_Municipio'] == 'SIM'])
        invalidos = len(df[df['Validacao_Municipio'] == 'NAO'])
        print(f"Municipios validados com sucesso: {validos} ({(validos/len(df)*100):.1f}%)")
        print(f"Municipios nao encontrados: {invalidos} ({(invalidos/len(df)*100):.1f}%)")
        print()
        
        print("COINCIDENCIA DE DADOS")
        print("-"*120)
        match_uf = len(df[df['Match_UF'] == 'SIM'])
        diff_uf = len(df[df['Match_UF'] == 'NAO'])
        print(f"UF coincidentes: {match_uf} ({(match_uf/len(df)*100):.1f}%)")
        print(f"UF diferentes: {diff_uf} ({(diff_uf/len(df)*100):.1f}%)")
        
        if diff_uf > 0:
            print("\nPrimeiras discrepancias de UF encontradas:")
            disc_uf = df[df['Match_UF'] == 'NAO'].head(5)
            for idx, row in disc_uf.iterrows():
                print(f"  {row['CNPJ']}: {row['UF_Origem']} (origem) -> {row['UF_API']} (api)")
        print()
        
        print("REGIOES METROPOLITANAS")
        print("-"*120)
        metros = df[df['Regiao_Metropolitana'] != 'N/A']
        print(f"CNPJs em regioes metropolitanas: {len(metros)} ({(len(metros)/len(df)*100):.1f}%)")
        
        if len(metros) > 0:
            regiao_count = metros['Regiao_Metropolitana'].value_counts()
            for regiao, count in regiao_count.items():
                print(f"  {regiao}: {count}")
        print()
        
        print("PRINCIPAIS ATIVIDADES (CNAE)")
        print("-"*120)
        atividades = df[df['CNAE'] != 'N/A']['CNAE'].value_counts().head(10)
        for atividade, count in atividades.items():
            print(f"  {atividade}: {count}")
        print()
        
        print("="*120)
        print(f"Relatorio completo salvo em: {arquivo_saida}")
        print("="*120)

def main():
    """Função principal"""
    
    print("\n" + "="*120)
    print("SCRIPT DE CONSULTA DE CNPJ EM MASSA COM VALIDACAO GEOGRAFICA")
    print("="*120 + "\n")
    
    arquivo_entrada = '20251222-Empresas-mapeadas.xlsx'
    arquivo_saida = 'relatorio_cnpj_completo.csv'
    coluna_cnpj = 'CNPJ'
    coluna_uf = 'UF do preco'
    coluna_municipio = 'Municipio'
    
    try:
        analisador = AnalisadorDadosEmpresa()
        
        logger.info(f"Lendo arquivo: {arquivo_entrada}")
        df = analisador.ler_arquivo_excel(arquivo_entrada, coluna_cnpj)
        
        logger.info("Iniciando consultas e validacoes...")
        df_resultado = analisador.processar_lote(df, coluna_cnpj, coluna_uf, coluna_municipio)
        
        analisador.gerar_relatorio(df_resultado, arquivo_saida)
        
    except Exception as e:
        logger.error(f"Erro fatal: {e}")
        raise

if __name__ == '__main__':
    main()
