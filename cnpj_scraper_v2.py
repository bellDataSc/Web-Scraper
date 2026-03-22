import re
import time
import unicodedata
import logging
from typing import Dict, List, Optional

import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class CNPJScraperV2:
    def __init__(self, timeout: int = 15, delay: float = 0.6):
        self.timeout = timeout
        self.delay = delay
        self.cache: Dict[str, Dict] = {}
        self.session = requests.Session()
        retry = Retry(
            total=3,
            read=3,
            connect=3,
            backoff_factor=0.8,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"]
        )
        adapter = HTTPAdapter(max_retries=retry)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept": "application/json,text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8"
        })

    def _clean_cnpj_v2(self, cnpj: str) -> str:
        return re.sub(r"\D", "", str(cnpj or ""))

    def _format_cnpj_v2(self, cnpj: str) -> str:
        clean = self._clean_cnpj_v2(cnpj)
        if len(clean) != 14:
            return str(cnpj)
        return f"{clean[:2]}.{clean[2:5]}.{clean[5:8]}/{clean[8:12]}-{clean[12:]}"

    def _normalize_text_v2(self, value: str) -> str:
        value = str(value or "").strip()
        normalized = unicodedata.normalize("NFKD", value)
        return "".join(ch for ch in normalized if not unicodedata.combining(ch)).upper()

    def _default_result_v2(self, cnpj: str, status: str = "nao_encontrado", fonte: str = "nenhuma") -> Dict:
        return {
            "cnpj": self._format_cnpj_v2(cnpj),
            "razao_social_v2": "N/A",
            "nome_fantasia_v2": "N/A",
            "municipio_v2": "N/A",
            "uf_v2": "N/A",
            "logradouro_v2": "N/A",
            "numero_v2": "N/A",
            "complemento_v2": "N/A",
            "bairro_v2": "N/A",
            "cep_v2": "N/A",
            "cnae_principal_v2": "N/A",
            "cnae_principal_codigo_v2": "N/A",
            "natureza_juridica_v2": "N/A",
            "situacao_cadastral_v2": "N/A",
            "data_inicio_atividade_v2": "N/A",
            "porte_v2": "N/A",
            "capital_social_v2": "N/A",
            "email_v2": "N/A",
            "telefone_v2": "N/A",
            "status_busca_v2": status,
            "fonte_v2": fonte
        }

    def _parse_brasilapi_v2(self, cnpj: str, data: Dict) -> Dict:
        return {
            "cnpj": self._format_cnpj_v2(cnpj),
            "razao_social_v2": data.get("razao_social", "N/A"),
            "nome_fantasia_v2": data.get("nome_fantasia", "N/A"),
            "municipio_v2": data.get("municipio", "N/A"),
            "uf_v2": data.get("uf", "N/A"),
            "logradouro_v2": data.get("logradouro", "N/A"),
            "numero_v2": data.get("numero", "N/A"),
            "complemento_v2": data.get("complemento", "N/A"),
            "bairro_v2": data.get("bairro", "N/A"),
            "cep_v2": data.get("cep", "N/A"),
            "cnae_principal_v2": data.get("cnae_fiscal_descricao", "N/A"),
            "cnae_principal_codigo_v2": data.get("cnae_fiscal", "N/A"),
            "natureza_juridica_v2": data.get("natureza_juridica_descricao", "N/A"),
            "situacao_cadastral_v2": data.get("descricao_situacao_cadastral", data.get("status", "N/A")),
            "data_inicio_atividade_v2": data.get("data_inicio_atividade", "N/A"),
            "porte_v2": data.get("porte", "N/A"),
            "capital_social_v2": data.get("capital_social", "N/A"),
            "email_v2": data.get("email", "N/A"),
            "telefone_v2": data.get("ddd_telefone_1", "N/A"),
            "status_busca_v2": "encontrado",
            "fonte_v2": "brasilapi_v2"
        }

    def consultar_brasilapi_v2(self, cnpj: str) -> Optional[Dict]:
        clean = self._clean_cnpj_v2(cnpj)
        if len(clean) != 14:
            return self._default_result_v2(cnpj, status="cnpj_invalido", fonte="validacao_v2")
        url = f"https://brasilapi.com.br/api/cnpj/v1/{clean}"
        try:
            response = self.session.get(url, timeout=self.timeout)
            if response.status_code == 200:
                return self._parse_brasilapi_v2(cnpj, response.json())
            if response.status_code == 404:
                return None
            logger.warning(f"BrasilAPI V2 retornou {response.status_code} para {cnpj}")
            return None
        except requests.RequestException as exc:
            logger.warning(f"Erro BrasilAPI V2 {cnpj}: {str(exc)[:160]}")
            return None

    def consultar_publica_v2(self, cnpj: str) -> Optional[Dict]:
        clean = self._clean_cnpj_v2(cnpj)
        if len(clean) != 14:
            return None
        url = f"https://open.cnpja.com/office/{clean}"
        try:
            response = self.session.get(url, timeout=self.timeout)
            if response.status_code != 200:
                return None
            data = response.json()
            address = data.get("address", {}) or {}
            company = data.get("company", {}) or {}
            main_activity = {}
            if isinstance(data.get("mainActivity"), dict):
                main_activity = data.get("mainActivity", {})
            return {
                "cnpj": self._format_cnpj_v2(cnpj),
                "razao_social_v2": company.get("name", data.get("alias", "N/A")),
                "nome_fantasia_v2": data.get("alias", "N/A"),
                "municipio_v2": address.get("city", "N/A"),
                "uf_v2": address.get("state", "N/A"),
                "logradouro_v2": address.get("street", "N/A"),
                "numero_v2": address.get("number", "N/A"),
                "complemento_v2": address.get("details", "N/A"),
                "bairro_v2": address.get("district", "N/A"),
                "cep_v2": address.get("zip", "N/A"),
                "cnae_principal_v2": main_activity.get("text", "N/A"),
                "cnae_principal_codigo_v2": main_activity.get("id", "N/A"),
                "natureza_juridica_v2": company.get("nature", {}).get("text", "N/A") if isinstance(company.get("nature"), dict) else "N/A",
                "situacao_cadastral_v2": data.get("status", {}).get("text", "N/A") if isinstance(data.get("status"), dict) else "N/A",
                "data_inicio_atividade_v2": data.get("founded", "N/A"),
                "porte_v2": company.get("size", {}).get("text", "N/A") if isinstance(company.get("size"), dict) else "N/A",
                "capital_social_v2": company.get("equity", "N/A"),
                "email_v2": "N/A",
                "telefone_v2": "N/A",
                "status_busca_v2": "encontrado",
                "fonte_v2": "consulta_publica_v2"
            }
        except requests.RequestException as exc:
            logger.warning(f"Erro consulta publica V2 {cnpj}: {str(exc)[:160]}")
            return None

    def consultar_cnpj_v2(self, cnpj: str) -> Dict:
        clean = self._clean_cnpj_v2(cnpj)
        if clean in self.cache:
            return self.cache[clean]
        if len(clean) != 14:
            result = self._default_result_v2(cnpj, status="cnpj_invalido", fonte="validacao_v2")
            self.cache[clean] = result
            return result
        result = self.consultar_brasilapi_v2(cnpj)
        if not result:
            time.sleep(self.delay)
            result = self.consultar_publica_v2(cnpj)
        if not result:
            result = self._default_result_v2(cnpj)
        self.cache[clean] = result
        return result

    def consultar_lote_v2(self, cnpjs: List[str], progress_callback=None) -> pd.DataFrame:
        results = []
        total = len(cnpjs)
        for idx, cnpj in enumerate(cnpjs, start=1):
            result = self.consultar_cnpj_v2(cnpj)
            results.append(result)
            if progress_callback:
                progress_callback(idx, total)
            time.sleep(self.delay)
        return pd.DataFrame(results)
