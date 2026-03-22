import logging
import re
import time
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd
import requests

from cnpj_scraper_v2 import CNPJScraperV2


logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class APILocalidadesV2:
    def __init__(self, timeout: int = 10):
        self.timeout = timeout
        self.base_url = "https://servicodados.ibge.gov.br/api/v1/localidades"
        self.cache_ufs: Dict[str, List[str]] = {}

    def _normalize_text_v2(self, value: str) -> str:
        value = str(value or "").strip()
        normalized = unicodedata.normalize("NFKD", value)
        return "".join(ch for ch in normalized if not unicodedata.combining(ch)).upper()

    def obter_municipios_por_uf_v2(self, uf: str) -> List[str]:
        uf = str(uf or "").strip().upper()
        if uf in self.cache_ufs:
            return self.cache_ufs[uf]
        url = f"{self.base_url}/estados/{uf}/municipios"
        try:
            response = requests.get(url, timeout=self.timeout)
            if response.status_code == 200:
                municipios = [self._normalize_text_v2(item.get("nome", "")) for item in response.json()]
                self.cache_ufs[uf] = municipios
                return municipios
        except requests.RequestException as exc:
            logger.warning(f"Erro IBGE V2 {uf}: {str(exc)[:160]}")
        self.cache_ufs[uf] = []
        return []

    def normalizar_municipio_v2(self, municipio: str, uf: str) -> Optional[str]:
        municipio_norm = self._normalize_text_v2(municipio)
        municipios = self.obter_municipios_por_uf_v2(uf)
        if not municipio_norm or not municipios:
            return None
        if municipio_norm in municipios:
            return municipio_norm
        for item in municipios:
            if municipio_norm in item or item in municipio_norm:
                return item
        return None


class ConsultorCNPJMassaV2:
    def __init__(self, delay: float = 0.4):
        self.delay = delay
        self.scraper_v2 = CNPJScraperV2(timeout=15, delay=delay)
        self.api_localidades_v2 = APILocalidadesV2(timeout=10)
        self.regioes_metropolitanas_v2 = self._mapear_regioes_metropolitanas_v2()

    def _normalize_text_v2(self, value: str) -> str:
        value = str(value or "").strip()
        normalized = unicodedata.normalize("NFKD", value)
        return "".join(ch for ch in normalized if not unicodedata.combining(ch)).upper()

    def _clean_cnpj_v2(self, value: str) -> str:
        return re.sub(r"\D", "", str(value or ""))

    def _mapear_regioes_metropolitanas_v2(self) -> Dict[str, Dict[str, List[str]]]:
        return {
            "RM_SAO_PAULO_V2": {"uf": "SP", "municipios": ["SAO PAULO", "GUARULHOS", "OSASCO", "SANTO ANDRE", "SAO BERNARDO DO CAMPO", "DIADEMA", "MAUA"]},
            "RM_RIO_V2": {"uf": "RJ", "municipios": ["RIO DE JANEIRO", "NITEROI", "SAO GONCALO", "DUQUE DE CAXIAS", "NOVA IGUACU"]},
            "RM_BELO_HORIZONTE_V2": {"uf": "MG", "municipios": ["BELO HORIZONTE", "CONTAGEM", "BETIM", "NOVA LIMA", "RIBEIRAO DAS NEVES"]},
            "RM_CURITIBA_V2": {"uf": "PR", "municipios": ["CURITIBA", "COLOMBO", "PINHAIS", "ARAUCARIA", "CAMPO LARGO"]},
            "RM_PORTO_ALEGRE_V2": {"uf": "RS", "municipios": ["PORTO ALEGRE", "CANOAS", "ALVORADA", "VIAMAO", "GRAVATAI"]},
            "RM_RECIFE_V2": {"uf": "PE", "municipios": ["RECIFE", "OLINDA", "PAULISTA", "JABOATAO DOS GUARARAPES"]},
            "RM_FORTALEZA_V2": {"uf": "CE", "municipios": ["FORTALEZA", "CAUCAIA", "MARACANAU", "AQUIRAZ"]},
            "RM_SALVADOR_V2": {"uf": "BA", "municipios": ["SALVADOR", "LAURO DE FREITAS", "CAMACARI", "SIMOES FILHO"]},
            "RM_BRASILIA_V2": {"uf": "DF", "municipios": ["BRASILIA", "TAGUATINGA", "CEILANDIA", "GUARA"]}
        }

    def identificar_regiao_metropolitana_v2(self, municipio: str, uf: str) -> str:
        municipio_norm = self._normalize_text_v2(municipio)
        uf = str(uf or "").strip().upper()
        for regiao, dados in self.regioes_metropolitanas_v2.items():
            if dados["uf"] != uf:
                continue
            if municipio_norm in dados["municipios"]:
                return regiao
            for item in dados["municipios"]:
                if municipio_norm in item or item in municipio_norm:
                    return regiao
        return "N/A"

    def detectar_coluna_v2(self, df: pd.DataFrame, candidatos: List[str]) -> str:
        normalized_columns = {self._normalize_text_v2(col): col for col in df.columns}
        for item in candidatos:
            if self._normalize_text_v2(item) in normalized_columns:
                return normalized_columns[self._normalize_text_v2(item)]
        raise ValueError(f"Coluna nao encontrada entre {candidatos}")

    def ler_excel_v2(self, arquivo_entrada_v2: str) -> pd.DataFrame:
        path = Path(arquivo_entrada_v2)
        if not path.exists():
            raise FileNotFoundError(f"Arquivo nao encontrado: {arquivo_entrada_v2}")
        df = pd.read_excel(path)
        coluna_cnpj_v2 = self.detectar_coluna_v2(df, ["CNPJ"])
        df = df.dropna(subset=[coluna_cnpj_v2]).copy()
        df["CNPJ_V2"] = df[coluna_cnpj_v2].astype(str).map(self._clean_cnpj_v2)
        df = df[df["CNPJ_V2"].str.len() == 14].drop_duplicates(subset=["CNPJ_V2"]).reset_index(drop=True)
        return df

    def processar_lote_v2(self, df: pd.DataFrame) -> pd.DataFrame:
        coluna_cnpj_origem_v2 = self.detectar_coluna_v2(df, ["CNPJ"])
        coluna_empresa_v2 = self.detectar_coluna_v2(df, ["Empresa", "RAZAO SOCIAL", "Razao Social"])
        coluna_uf_origem_v2 = self.detectar_coluna_v2(df, ["UF do preco", "UF do preço", "UF", "UF origem"])
        coluna_municipio_origem_v2 = self.detectar_coluna_v2(df, ["Municipio", "Município", "Cidade"])

        resultados = []
        total = len(df)

        for idx, row in df.iterrows():
            cnpj = row["CNPJ_V2"]
            consulta = self.scraper_v2.consultar_cnpj_v2(cnpj)

            municipio_api = consulta["municipio_v2"]
            uf_api = str(consulta["uf_v2"] or "").upper().strip()

            municipio_api_normalizado = self.api_localidades_v2.normalizar_municipio_v2(municipio_api, uf_api) if uf_api else None
            validacao_municipio_v2 = "SIM" if municipio_api_normalizado else "NAO"

            uf_origem = str(row[coluna_uf_origem_v2]).strip().upper()
            municipio_origem = self._normalize_text_v2(row[coluna_municipio_origem_v2])

            municipio_final_v2 = municipio_api_normalizado if municipio_api_normalizado else municipio_api
            match_uf_v2 = "SIM" if uf_origem == uf_api else "NAO"
            match_municipio_v2 = "SIM" if municipio_origem and municipio_origem == self._normalize_text_v2(municipio_final_v2) else "NAO"
            regiao_metropolitana_v2 = self.identificar_regiao_metropolitana_v2(municipio_final_v2, uf_api)

            resultados.append({
                "CNPJ_V2": consulta["cnpj"],
                "Empresa_Original_V2": row[coluna_empresa_v2],
                "UF_Origem_V2": uf_origem,
                "Municipio_Origem_V2": row[coluna_municipio_origem_v2],
                "Razao_Social_V2": consulta["razao_social_v2"],
                "Nome_Fantasia_V2": consulta["nome_fantasia_v2"],
                "Municipio_API_V2": municipio_final_v2,
                "UF_API_V2": uf_api,
                "Validacao_Municipio_V2": validacao_municipio_v2,
                "Regiao_Metropolitana_V2": regiao_metropolitana_v2,
                "Match_UF_V2": match_uf_v2,
                "Match_Municipio_V2": match_municipio_v2,
                "Logradouro_V2": consulta["logradouro_v2"],
                "Numero_V2": consulta["numero_v2"],
                "Complemento_V2": consulta["complemento_v2"],
                "Bairro_V2": consulta["bairro_v2"],
                "CEP_V2": consulta["cep_v2"],
                "CNAE_Principal_V2": consulta["cnae_principal_v2"],
                "CNAE_Principal_Codigo_V2": consulta["cnae_principal_codigo_v2"],
                "Natureza_Juridica_V2": consulta["natureza_juridica_v2"],
                "Situacao_Cadastral_V2": consulta["situacao_cadastral_v2"],
                "Data_Inicio_Atividade_V2": consulta["data_inicio_atividade_v2"],
                "Porte_V2": consulta["porte_v2"],
                "Capital_Social_V2": consulta["capital_social_v2"],
                "Email_V2": consulta["email_v2"],
                "Telefone_V2": consulta["telefone_v2"],
                "Status_Busca_V2": consulta["status_busca_v2"],
                "Fonte_V2": consulta["fonte_v2"],
                "Data_Consulta_V2": datetime.now().isoformat()
            })

            logger.info(f"Processado V2 {idx + 1}/{total}: {consulta['cnpj']}")
            time.sleep(self.delay)

        return pd.DataFrame(resultados)

    def exportar_resultados_v2(self, df_resultado_v2: pd.DataFrame, prefixo_saida_v2: str = "relatorio_cnpj_v2") -> Tuple[str, str]:
        csv_path = f"{prefixo_saida_v2}.csv"
        xlsx_path = f"{prefixo_saida_v2}.xlsx"
        df_resultado_v2.to_csv(csv_path, index=False, encoding="utf-8-sig", sep=";")
        df_resultado_v2.to_excel(xlsx_path, index=False)
        return csv_path, xlsx_path


def main():
    arquivo_entrada_v2 = "20251222 - Empresas mapeadas.xlsx"
    processador_v2 = ConsultorCNPJMassaV2(delay=0.4)
    df_entrada_v2 = processador_v2.ler_excel_v2(arquivo_entrada_v2)
    df_resultado_v2 = processador_v2.processar_lote_v2(df_entrada_v2)
    processador_v2.exportar_resultados_v2(df_resultado_v2, "relatorio_cnpj_completo_v2")


if __name__ == "__main__":
    main()
