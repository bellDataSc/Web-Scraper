import requests
import pandas as pd
from typing import Dict, Optional, List
import logging
from time import sleep
from bs4 import BeautifulSoup
import re

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CNPJScraper:
    """Web scraper para dados de CNPJ de multiplas fontes"""
    
    def __init__(self):
        self.cache = {}
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'pt-BR,pt;q=0.9,en;q=0.8',
            'Referer': 'https://www.google.com/',
            'DNT': '1'
        })
    
    def _clean_cnpj(self, cnpj: str) -> str:
        """Remove formatacao do CNPJ"""
        return cnpj.replace('.', '').replace('-', '').replace('/', '')
    
    def _format_cnpj(self, cnpj: str) -> str:
        """Formata CNPJ no padrao XX.XXX.XXX/XXXX-XX"""
        clean = self._clean_cnpj(cnpj)
        if len(clean) == 14:
            return f"{clean[:2]}.{clean[2:5]}.{clean[5:8]}/{clean[8:12]}-{clean[12:14]}"
        return cnpj
    
    def scrape_receita_federal(self, cnpj: str) -> Optional[Dict]:
        """
        Realiza web scraping no site da Receita Federal
        Esta e a fonte mais confiavel de dados de CNPJ
        """
        try:
            clean_cnpj = self._clean_cnpj(cnpj)
            
            url = "https://www.cnpj.gov.br/"
            
            data = {
                'cnpj': clean_cnpj
            }
            
            response = self.session.post(url, data=data, timeout=15, allow_redirects=True)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                razao_social = 'Nao encontrada'
                cidade = 'Nao encontrada'
                uf = 'Nao encontrada'
                logradouro = 'N/A'
                numero = 'N/A'
                cep = 'N/A'
                
                text_content = soup.get_text()
                
                if 'CNPJ nao foi encontrado' in text_content or 'NAO LOCALIZADO' in text_content:
                    return None
                
                patterns = {
                    'razao_social': r'Razao Social[:\s]+([^\n<]+)',
                    'cidade': r'Municipio[:\s]+([^\n<]+)',
                    'uf': r'UF[:\s]+([A-Z]{2})',
                    'logradouro': r'Logradouro[:\s]+([^\n<]+)',
                    'numero': r'Numero[:\s]+([^\n<]+)',
                    'cep': r'CEP[:\s]+([0-9-]+)'
                }
                
                for key, pattern in patterns.items():
                    match = re.search(pattern, text_content, re.IGNORECASE)
                    if match:
                        locals()[key] = match.group(1).strip()
                
                if razao_social == 'Nao encontrada':
                    return None
                
                return {
                    'cnpj': self._format_cnpj(cnpj),
                    'razao_social': razao_social,
                    'nome_fantasia': 'N/A',
                    'cidade': cidade.upper().strip(),
                    'uf': uf,
                    'logradouro': logradouro,
                    'numero': numero,
                    'cep': cep,
                    'status': 'encontrado',
                    'fonte': 'receita_federal'
                }
            
            return None
        
        except requests.exceptions.Timeout:
            logger.warning(f"Timeout Receita Federal: {cnpj}")
            return None
        except Exception as e:
            logger.warning(f"Erro Receita Federal {cnpj}: {str(e)[:100]}")
            return None
    
    def scrape_sintegra(self, cnpj: str) -> Optional[Dict]:
        """
        Realiza web scraping no Sintegra
        Sistema de Integrados Estaduais
        """
        try:
            clean_cnpj = self._clean_cnpj(cnpj)
            
            url = "https://www1.sintegra.gov.br/Cgi-Bin/MGER800.EXE"
            
            data = {
                'CNPJ': clean_cnpj,
                'TIPO': '1',
                'TABELA': '1'
            }
            
            response = self.session.get(url, params=data, timeout=15)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                text_content = soup.get_text()
                
                if 'CNPJ NAO LOCALIZADO' in text_content or 'nao localizado' in text_content.lower():
                    return None
                
                lines = text_content.split('\n')
                
                razao_social = 'Nao encontrada'
                cidade = 'Nao encontrada'
                uf = 'Nao encontrada'
                logradouro = 'N/A'
                numero = 'N/A'
                cep = 'N/A'
                
                for line in lines:
                    if 'RAZAO SOCIAL' in line.upper():
                        razao_social = line.split(':')[-1].strip() if ':' in line else 'N/A'
                    elif 'MUNICIPIO' in line.upper():
                        cidade = line.split(':')[-1].strip() if ':' in line else 'N/A'
                    elif 'UF' in line.upper():
                        match = re.search(r'([A-Z]{2})', line)
                        if match:
                            uf = match.group(1)
                
                if razao_social != 'Nao encontrada' and razao_social != 'N/A':
                    return {
                        'cnpj': self._format_cnpj(cnpj),
                        'razao_social': razao_social,
                        'nome_fantasia': 'N/A',
                        'cidade': cidade.upper().strip(),
                        'uf': uf,
                        'logradouro': logradouro,
                        'numero': numero,
                        'cep': cep,
                        'status': 'encontrado',
                        'fonte': 'sintegra'
                    }
            
            return None
        
        except requests.exceptions.Timeout:
            logger.warning(f"Timeout Sintegra: {cnpj}")
            return None
        except Exception as e:
            logger.warning(f"Erro Sintegra {cnpj}: {str(e)[:100]}")
            return None
    
    def scrape_cnpj(self, cnpj: str) -> Dict:
        """
        Busca dados do CNPJ em multiplas fontes com fallback
        Tenta Receita Federal primeiro, depois Sintegra
        """
        clean_cnpj = self._clean_cnpj(cnpj)
        
        if clean_cnpj in self.cache:
            return self.cache[clean_cnpj]
        
        result = None
        
        try:
            result = self.scrape_receita_federal(cnpj)
            
            if not result:
                logger.info(f"Tentando Sintegra para {cnpj}")
                sleep(1)
                result = self.scrape_sintegra(cnpj)
            
            if not result:
                result = {
                    'cnpj': self._format_cnpj(cnpj),
                    'razao_social': 'Nao encontrada',
                    'nome_fantasia': 'N/A',
                    'cidade': 'Nao encontrada',
                    'uf': 'Nao encontrada',
                    'logradouro': 'N/A',
                    'numero': 'N/A',
                    'cep': 'N/A',
                    'status': 'nao_encontrado',
                    'fonte': 'nenhuma'
                }
        
        except Exception as e:
            logger.error(f"Erro geral {cnpj}: {str(e)[:100]}")
            result = {
                'cnpj': self._format_cnpj(cnpj),
                'razao_social': 'Erro',
                'nome_fantasia': 'Erro',
                'cidade': 'Erro',
                'uf': 'Erro',
                'logradouro': 'Erro',
                'numero': 'Erro',
                'cep': 'Erro',
                'status': 'erro',
                'fonte': 'erro'
            }
        
        self.cache[clean_cnpj] = result
        return result
    
    def scrape_batch(self, cnpj_list: List[str], progress_callback=None) -> pd.DataFrame:
        """
        Realiza web scraping para multiplos CNPJs
        """
        results = []
        total = len(cnpj_list)
        
        for idx, cnpj in enumerate(cnpj_list):
            try:
                data = self.scrape_cnpj(cnpj)
                results.append(data)
                
                if progress_callback:
                    progress_callback(idx + 1, total)
                
                sleep(2)
            
            except Exception as e:
                logger.error(f"Erro ao processar {cnpj}: {str(e)[:100]}")
                results.append({
                    'cnpj': cnpj,
                    'razao_social': 'Erro',
                    'nome_fantasia': 'Erro',
                    'cidade': 'Erro',
                    'uf': 'Erro',
                    'logradouro': 'Erro',
                    'numero': 'Erro',
                    'cep': 'Erro',
                    'status': 'erro',
                    'fonte': 'erro'
                })
        
        return pd.DataFrame(results)
