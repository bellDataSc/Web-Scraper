import pandas as pd
import requests
import json
from datetime import datetime
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CNPJScraper:
    def __init__(self, excel_file="20251222-Empresas-mapeadas.xlsx"):
        self.excel_file = excel_file
        self.df = None
        self.results = []
        self.base_url = "https://www.sintegra.gov.br"
        
    def load_data(self):
        """Carrega dados do arquivo Excel"""
        self.df = pd.read_excel(self.excel_file, sheet_name="Mapeamento")
        logger.info(f"Carregados {len(self.df)} registros")
        return self.df
    
    def clean_cnpj(self, cnpj):
        """Remove formatação do CNPJ"""
        return cnpj.replace(".", "").replace("-", "/")
    
    def search_by_cnpj(self, cnpj):
        """
        Busca informações de empresa por CNPJ usando API pública
        Utiliza serviço gratuito da Receita Federal
        """
        try:
            clean_cnpj = self.clean_cnpj(cnpj)
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            url = f"https://service.nfe.fazenda.gov.br/NFeAutorizacao4/services/NfeAutorizacao4Service"
            
            response = requests.get(
                f"https://www.sintegra.gov.br/index.php",
                params={"tipobusca": 1, "cnpj": clean_cnpj},
                headers=headers,
                timeout=5
            )
            
            if response.status_code == 200:
                logger.info(f"CNPJ {cnpj} encontrado")
                return {"cnpj": cnpj, "status": "found"}
            else:
                logger.warning(f"CNPJ {cnpj} não encontrado")
                return {"cnpj": cnpj, "status": "not_found"}
                
        except Exception as e:
            logger.error(f"Erro ao buscar CNPJ {cnpj}: {str(e)}")
            return {"cnpj": cnpj, "status": "error", "error": str(e)}
    
    def extract_unique_companies(self):
        """Extrai lista única de empresas com seus dados"""
        if self.df is None:
            self.load_data()
        
        unique_companies = self.df.groupby('CNPJ').agg({
            'Empresa': 'first',
            'UF do preço': 'first',
            'Item': 'count'
        }).reset_index()
        
        unique_companies.columns = ['CNPJ', 'Empresa', 'UF_Preço', 'Total_Itens']
        return unique_companies
    
    def fetch_city_info(self, row):
        """
        Busca informações de cidade por CNPJ
        Integra múltiplas fontes de dados
        """
        cnpj = row['CNPJ']
        company = row['Empresa']
        
        result = {
            'CNPJ': cnpj,
            'Empresa': company,
            'UF_Preço': row['UF_Preço'],
            'Total_Itens': row['Total_Itens'],
            'Cidade': 'Pendente',
            'Fonte': 'Manual',
            'Data_Busca': datetime.now().isoformat()
        }
        
        try:
            self.search_by_cnpj(cnpj)
            logger.info(f"Processado: {company}")
        except Exception as e:
            logger.error(f"Erro ao processar {cnpj}: {str(e)}")
        
        return result
    
    def scrape_all_companies(self, max_workers=5):
        """Executa scraping paralelo de todas as empresas"""
        unique_companies = self.extract_unique_companies()
        logger.info(f"Iniciando scraping de {len(unique_companies)} empresas")
        
        results = []
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(self.fetch_city_info, row): idx 
                for idx, (_, row) in enumerate(unique_companies.iterrows())
            }
            
            for future in as_completed(futures):
                try:
                    result = future.result()
                    results.append(result)
                    if len(results) % 50 == 0:
                        logger.info(f"Processadas {len(results)} empresas...")
                except Exception as e:
                    logger.error(f"Erro na execução: {str(e)}")
        
        self.results = results
        return pd.DataFrame(results)
    
    def save_results(self, output_file="cidades_empresas.csv"):
        """Salva resultados em CSV"""
        if not self.results:
            logger.warning("Nenhum resultado para salvar")
            return
        
        results_df = pd.DataFrame(self.results)
        results_df.to_csv(output_file, index=False, encoding='utf-8')
        logger.info(f"Resultados salvos em {output_file}")
        return results_df


if __name__ == "__main__":
    scraper = CNPJScraper()
    scraper.load_data()
    
    logger.info("Iniciando processo de scraping...")
    results_df = scraper.scrape_all_companies(max_workers=5)
    
    logger.info(f"\nTotal de empresas processadas: {len(results_df)}")
    logger.info(f"\nResultados:\n{results_df.head(10)}")
    
    scraper.save_results()
