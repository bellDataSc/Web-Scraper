import requests
import pandas as pd
from typing import Dict, Optional, List
import logging
from time import sleep

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CNPJDataFetcher:
    """Coleta dados de CNPJ de multiplas APIs brasileiras"""
    
    def __init__(self):
        self.cnpjs_dev_url = "https://cnpjs.dev/api/cnpj"
        self.moccasin_url = "https://moccasin.com.br/api/cnpj"
        self.cache = {}
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json'
        }
    
    def _clean_cnpj(self, cnpj: str) -> str:
        """Remove formatacao do CNPJ"""
        return cnpj.replace('.', '').replace('-', '').replace('/', '')
    
    def _format_cnpj(self, cnpj: str) -> str:
        """Formata CNPJ no padrao XX.XXX.XXX/XXXX-XX"""
        clean = self._clean_cnpj(cnpj)
        if len(clean) == 14:
            return f"{clean[:2]}.{clean[2:5]}.{clean[5:8]}/{clean[8:12]}-{clean[12:14]}"
        return cnpj
    
    def fetch_from_cnpjs_dev(self, cnpj: str) -> Optional[Dict]:
        """
        Busca dados em cnpjs.dev
        API mais rapida para dados brasileiros
        """
        try:
            clean_cnpj = self._clean_cnpj(cnpj)
            url = f"{self.cnpjs_dev_url}/{clean_cnpj}"
            response = requests.get(url, headers=self.headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                return {
                    'cnpj': self._format_cnpj(cnpj),
                    'razao_social': data.get('nome', 'N/A'),
                    'nome_fantasia': data.get('nome_fantasia', 'N/A'),
                    'cidade': data.get('municipio', 'Nao informada'),
                    'uf': data.get('uf', 'Nao informada'),
                    'logradouro': data.get('logradouro', 'N/A'),
                    'numero': data.get('numero', 'N/A'),
                    'cep': data.get('cep', 'N/A'),
                    'status': 'encontrado',
                    'fonte': 'cnpjs.dev'
                }
            return None
        
        except requests.exceptions.Timeout:
            logger.warning(f"Timeout cnpjs.dev: {cnpj}")
            return None
        except Exception as e:
            logger.warning(f"Erro cnpjs.dev {cnpj}: {str(e)}")
            return None
    
    def fetch_from_moccasin(self, cnpj: str) -> Optional[Dict]:
        """
        Busca dados em moccasin.com.br (API alternativa)
        """
        try:
            clean_cnpj = self._clean_cnpj(cnpj)
            url = f"{self.moccasin_url}/{clean_cnpj}"
            response = requests.get(url, headers=self.headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                return {
                    'cnpj': self._format_cnpj(cnpj),
                    'razao_social': data.get('company', {}).get('name', 'N/A'),
                    'nome_fantasia': data.get('company', {}).get('alias', 'N/A'),
                    'cidade': data.get('address', {}).get('city', 'Nao informada'),
                    'uf': data.get('address', {}).get('state', 'Nao informada'),
                    'logradouro': data.get('address', {}).get('street', 'N/A'),
                    'numero': data.get('address', {}).get('number', 'N/A'),
                    'cep': data.get('address', {}).get('zip_code', 'N/A'),
                    'status': 'encontrado',
                    'fonte': 'moccasin'
                }
            return None
        
        except requests.exceptions.Timeout:
            logger.warning(f"Timeout moccasin: {cnpj}")
            return None
        except Exception as e:
            logger.warning(f"Erro moccasin {cnpj}: {str(e)}")
            return None
    
    def fetch_cnpj_data(self, cnpj: str) -> Dict:
        """
        Busca dados do CNPJ em multiplas APIs com fallback
        """
        clean_cnpj = self._clean_cnpj(cnpj)
        
        if clean_cnpj in self.cache:
            return self.cache[clean_cnpj]
        
        result = None
        
        try:
            result = self.fetch_from_cnpjs_dev(cnpj)
            
            if not result:
                logger.info(f"Fallback moccasin: {cnpj}")
                sleep(0.5)
                result = self.fetch_from_moccasin(cnpj)
            
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
            logger.error(f"Erro geral {cnpj}: {str(e)}")
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
    
    def fetch_batch(self, cnpj_list: List[str], progress_callback=None) -> pd.DataFrame:
        """
        Busca dados para multiplos CNPJs
        """
        results = []
        total = len(cnpj_list)
        
        for idx, cnpj in enumerate(cnpj_list):
            try:
                data = self.fetch_cnpj_data(cnpj)
                results.append(data)
                
                if progress_callback:
                    progress_callback(idx + 1, total)
                
                sleep(0.2)
            
            except Exception as e:
                logger.error(f"Erro ao processar {cnpj}: {str(e)}")
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
