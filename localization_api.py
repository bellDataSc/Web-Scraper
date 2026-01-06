import requests
import pandas as pd
from typing import Dict, List, Optional, Tuple
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class LocalizationAPI:
    """API para consulta de localidades brasileiras e validacao geografica"""
    
    def __init__(self):
        self.ibge_base_url = "https://servicodados.ibge.gov.br/api/v1/localidades"
        self.metropolitan_regions = self._init_metropolitan_regions()
        self.uf_cache = {}
        self.cities_cache = {}
    
    def _init_metropolitan_regions(self) -> Dict[str, List[str]]:
        """
        Define regioes metropolitanas brasileiras
        Estrutura: UF -> Lista de cidades na regiao metropolitana
        """
        return {
            'SP': {
                'name': 'RMSP - Regiao Metropolitana de Sao Paulo',
                'cities': [
                    'Sao Paulo', 'Guarulhos', 'Campinas', 'Santos', 'Sorocaba',
                    'Osasco', 'Santo Andre', 'Sao Bernardo do Campo', 'Sao Caetano do Sul',
                    'Diadema', 'Mogi das Cruzes', 'Suzano', 'Ribeirao Pires',
                    'Rio Grande da Serra', 'Embu-Guacu', 'Embu', 'Itapecerica da Serra',
                    'Juquitiba', 'Vargem Grande Paulista', 'Cotia', 'Itapevi',
                    'Jandira', 'Pirapora do Bom Jesus', 'Santana de Parnaiba',
                    'Cajamar', 'Cabreuva', 'Itu', 'Salto', 'Mairinque',
                    'Aracariguama', 'Piedade', 'Tapiratiba', 'Ipeuna'
                ]
            },
            'RJ': {
                'name': 'RMRJ - Regiao Metropolitana do Rio de Janeiro',
                'cities': [
                    'Rio de Janeiro', 'Niteroi', 'Sao Goncalo', 'Duque de Caxias',
                    'Nova Iguacu', 'Sao Joao de Meriti', 'Nillopolis', 'Mesquita',
                    'Magé', 'Mangaratiba', 'Itaguai', 'Seropedica',
                    'Japeri', 'Marica', 'Cachoeiras de Macacu', 'Guapimirim',
                    'Tanguá', 'Sao Goncalo'
                ]
            },
            'MG': {
                'name': 'RMBH - Regiao Metropolitana de Belo Horizonte',
                'cities': [
                    'Belo Horizonte', 'Contagem', 'Betim', 'Ribeirão das Neves',
                    'Santa Luzia', 'Vespasiano', 'Sarzedo', 'Sete Lagoas',
                    'Divinopolis', 'Conselheiro Lafaiete', 'Itabira'
                ]
            },
            'BA': {
                'name': 'RMSB - Regiao Metropolitana de Salvador',
                'cities': [
                    'Salvador', 'Camaçari', 'Lauro de Freitas', 'Simoes Filho',
                    'Dias d\'Avila', 'Mata de Sao Joao', 'Pojuca'
                ]
            },
            'PE': {
                'name': 'RMR - Regiao Metropolitana do Recife',
                'cities': [
                    'Recife', 'Jaboatao dos Guararapes', 'Camaragibe', 'Olinda',
                    'Paulista', 'Itapissuma', 'Igarassu', 'Araçoiaba',
                    'Moreno', 'Cabo de Santo Agostinho'
                ]
            },
            'SC': {
                'name': 'RMGV - Regiao Metropolitana do Vale do Itajai',
                'cities': [
                    'Blumenau', 'Brusque', 'Gaspar', 'Botuverá', 'Guabiruba',
                    'Indaial', 'Pomerode', 'Rodeio', 'Timbó'
                ]
            },
            'RS': {
                'name': 'RMPA - Regiao Metropolitana de Porto Alegre',
                'cities': [
                    'Porto Alegre', 'Viamao', 'Alvorada', 'Gravataí', 'Cachoeirinha',
                    'Canoas', 'Esteio', 'Sapucaia do Sul', 'São Leopoldo',
                    'Novo Hamburgo', 'Paracambi'
                ]
            },
            'PR': {
                'name': 'RMC - Regiao Metropolitana de Curitiba',
                'cities': [
                    'Curitiba', 'Sao Jose dos Pinhais', 'Almirante Tamandaré',
                    'Araçatuba', 'Araucária', 'Bocaiuva do Sul', 'Campina Grande do Sul',
                    'Colombo', 'Contenda', 'Fazenda Rio Grande', 'Itaperuçu',
                    'Mandirituba', 'Piraquara', 'Quatro Barras', 'Rio Branco do Sul',
                    'Tunas do Paraná'
                ]
            }
        }
    
    def get_cities_by_uf(self, uf: str) -> List[str]:
        """
        Busca lista de cidades por UF via IBGE API
        """
        if uf in self.cities_cache:
            return self.cities_cache[uf]
        
        try:
            url = f"{self.ibge_base_url}/estados/{uf}/municipios"
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            
            data = response.json()
            cities = [city['nome'] for city in data]
            self.cities_cache[uf] = cities
            logger.info(f"Carregadas {len(cities)} cidades de {uf}")
            return cities
        
        except Exception as e:
            logger.error(f"Erro ao buscar cidades de {uf}: {str(e)}")
            return []
    
    def get_all_ufs(self) -> List[Dict[str, str]]:
        """
        Retorna lista de todos os estados brasileiros
        """
        try:
            url = f"{self.ibge_base_url}/estados"
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            
            data = response.json()
            return [{"nome": state['nome'], "sigla": state['sigla']} for state in data]
        
        except Exception as e:
            logger.error(f"Erro ao buscar UFs: {str(e)}")
            return []
    
    def is_metropolitan_area(self, uf: str, city: str) -> Tuple[bool, Optional[str]]:
        """
        Verifica se cidade pertence a uma regiao metropolitana
        Retorna: (é metropolitana, nome da regiao)
        """
        if uf not in self.metropolitan_regions:
            return False, None
        
        region_data = self.metropolitan_regions[uf]
        cities_normalized = [c.upper().strip() for c in region_data['cities']]
        city_normalized = city.upper().strip()
        
        if city_normalized in cities_normalized:
            return True, region_data['name']
        
        return False, None
    
    def validate_location(self, uf: str, city: str) -> Dict[str, any]:
        """
        Valida se localidade existe em banco de dados IBGE
        Retorna dict com validacao, regiao metropolitana, etc.
        """
        cities = self.get_cities_by_uf(uf)
        city_normalized = city.upper().strip()
        cities_normalized = [c.upper().strip() for c in cities]
        
        is_valid = city_normalized in cities_normalized
        is_metro, metro_name = self.is_metropolitan_area(uf, city)
        
        return {
            'uf': uf,
            'city': city,
            'valid': is_valid,
            'metropolitan': is_metro,
            'metropolitan_name': metro_name
        }
    
    def enrich_dataframe(self, df: pd.DataFrame, city_column: str = 'Cidade',
                         uf_column: str = 'UF do preço') -> pd.DataFrame:
        """
        Enriquece DataFrame com validacoes e dados de regiao metropolitana
        """
        validations = []
        
        for idx, row in df.iterrows():
            uf = row[uf_column]
            city = row.get(city_column, '')
            
            if city and pd.notna(city):
                validation = self.validate_location(uf, city)
            else:
                validation = {
                    'uf': uf,
                    'city': city if city else 'Nao informada',
                    'valid': False,
                    'metropolitan': False,
                    'metropolitan_name': None
                }
            
            validations.append(validation)
        
        validation_df = pd.DataFrame(validations)
        
        enriched = pd.concat([df.reset_index(drop=True), 
                             validation_df[['valid', 'metropolitan', 'metropolitan_name']]], 
                            axis=1)
        
        return enriched


def get_regional_stats(df: pd.DataFrame) -> Dict[str, any]:
    """
    Calcula estatisticas por regiao metropolitana
    """
    stats = {
        'total_companies': len(df),
        'metropolitan_companies': len(df[df['metropolitan'] == True]),
        'non_metropolitan': len(df[df['metropolitan'] == False]),
        'validated_cities': len(df[df['valid'] == True]),
        'unvalidated_cities': len(df[df['valid'] == False])
    }
    
    if 'metropolitan_name' in df.columns:
        metro_dist = df[df['metropolitan'] == True]['metropolitan_name'].value_counts()
        stats['distribution_by_metropolitan'] = metro_dist.to_dict()
    
    return stats
