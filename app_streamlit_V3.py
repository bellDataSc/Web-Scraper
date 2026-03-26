import streamlit as st
import pandas as pd
import requests
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import time

st.set_page_config(
    page_title="Consultor CNPJ com Localidades",
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

    def _limpar_cnpj(self, cnpj: str) -> str:
        return cnpj.replace('.', '').replace('/', '').replace('-', '').strip()

    def _formatar_cnpj(self, cnpj: str) -> str:
        c = self._limpar_cnpj(cnpj)
        if len(c) == 14:
            return f"{c[:2]}.{c[2:5]}.{c[5:8]}/{c[8:12]}-{c[12:]}"
        return cnpj

    def consultar_brasilapi(self, cnpj: str) -> Optional[Dict]:
        try:
            cnpj_limpo = self._limpar_cnpj(cnpj)
            if cnpj_limpo in self.cache:
                return self.cache[cnpj_limpo]

            url = f"https://brasilapi.com.br/api/cnpj/v1/{cnpj_limpo}"
            response = requests.get(url, headers=self.headers, timeout=10)

            if response.status_code == 200:
                data = response.json()
                resultado = {
                    'cnpj': cnpj,
                    'cnpj_limpo': cnpj_limpo,
                    'cnpj_raiz': cnpj_limpo[:8],
                    'razao_social': data.get('razao_social', 'N/A'),
                    'nome_fantasia': data.get('nome_fantasia', 'N/A'),
                    'municipio': data.get('municipio', 'N/A'),
                    'uf': data.get('uf', 'N/A'),
                    'logradouro': data.get('logradouro', 'N/A'),
                    'numero': data.get('numero', 'N/A'),
                    'bairro': data.get('bairro', 'N/A'),
                    'complemento': data.get('complemento', ''),
                    'cep': data.get('cep', 'N/A'),
                    'cnae': data.get('cnae_fiscal_descricao', 'N/A'),
                    'cnae_codigo': data.get('cnae_fiscal', 'N/A'),
                    'cnaes_secundarios': data.get('cnaes_secundarios', []),
                    'natureza_juridica': data.get('natureza_juridica', 'N/A'),
                    'status': 'ATIVO' if data.get('descricao_situacao_cadastral') == 'ATIVA' else 'INATIVO',
                    'matriz_filial': (
                        'MATRIZ' if data.get('identificador_matriz_filial') == 1 else 'FILIAL'
                    ),
                    'data_consulta': datetime.now().isoformat(),
                    'email': data.get('email') or 'N/A',
                    'telefone': data.get('ddd_telefone_1', 'N/A'),
                    'data_inicio_atividade': data.get('data_inicio_atividade', 'N/A'),
                    'capital_social': data.get('capital_social', 'N/A'),
                    'porte': data.get('descricao_porte') or data.get('porte') or 'N/A',
                }
                self.cache[cnpj_limpo] = resultado
                return resultado
        except Exception as e:
            logger.warning(f"Erro ao consultar BrasilAPI: {e}")
        return None

    def consultar_cnpj(self, cnpj: str) -> Dict:
        resultado = self.consultar_brasilapi(cnpj)
        if resultado is None:
            cnpj_limpo = self._limpar_cnpj(cnpj)
            resultado = {
                'cnpj': cnpj,
                'cnpj_limpo': cnpj_limpo,
                'cnpj_raiz': cnpj_limpo[:8] if len(cnpj_limpo) >= 8 else 'N/A',
                'razao_social': 'N/A',
                'nome_fantasia': 'N/A',
                'municipio': 'N/A',
                'uf': 'N/A',
                'logradouro': 'N/A',
                'numero': 'N/A',
                'bairro': 'N/A',
                'complemento': '',
                'cep': 'N/A',
                'cnae': 'N/A',
                'cnae_codigo': 'N/A',
                'cnaes_secundarios': [],
                'natureza_juridica': 'N/A',
                'status': 'ERRO',
                'matriz_filial': 'N/A',
                'data_consulta': datetime.now().isoformat(),
                'email': 'N/A',
                'telefone': 'N/A',
                'data_inicio_atividade': 'N/A',
                'capital_social': 'N/A',
                'porte': 'N/A',
            }
        return resultado

    def consultar_filiais_cnpja(self, cnpj: str) -> Dict:
        cnpj_limpo = self._limpar_cnpj(cnpj)
        cache_key = f"filiais_{cnpj_limpo}"

        if cache_key in self.cache:
            return self.cache[cache_key]

        resultado = {'filiais': [], 'erro': None, 'total': 0}

        try:
            url = f"https://open.cnpja.com/office/{cnpj_limpo}"
            response = requests.get(url, headers=self.headers, timeout=15)

            if response.status_code == 429:
                resultado['erro'] = "Limite de requisicoes atingido na CNPJa. Aguarde 1 minuto."
                return resultado

            if response.status_code == 404:
                resultado['erro'] = "CNPJ nao encontrado na CNPJa."
                return resultado

            if response.status_code != 200:
                resultado['erro'] = f"CNPJa retornou status {response.status_code}."
                return resultado

            data = response.json()
            company = data.get('company', {})
            branches = company.get('branches', [])

            filiais = []
            for est in branches:
                cnpj_est = str(est.get('taxId', ''))
                if not cnpj_est:
                    continue

                tipo = 'MATRIZ' if est.get('head', False) else 'FILIAL'
                situacao = est.get('status', {}).get('text', 'N/A')

                address = est.get('address', {})
                municipio = address.get('city', 'N/A')
                uf = address.get('state', 'N/A')
                logradouro = address.get('street', 'N/A')
                numero = address.get('number', 'N/A')
                bairro = address.get('district', 'N/A')
                complemento = address.get('details', '') or ''
                cep = address.get('zip', 'N/A')

                comp_str = f" {complemento}" if complemento else ''
                endereco_completo = (
                    f"{logradouro}, {numero}{comp_str} - "
                    f"{bairro} - {municipio}/{uf} - CEP: {cep}"
                )

                filiais.append({
                    'cnpj': self._formatar_cnpj(cnpj_est),
                    'tipo': tipo,
                    'razao_social': company.get('name', 'N/A'),
                    'nome_fantasia': est.get('alias', 'N/A'),
                    'situacao': situacao,
                    'logradouro': logradouro,
                    'numero': numero,
                    'complemento': complemento,
                    'bairro': bairro,
                    'municipio': municipio,
                    'uf': uf,
                    'cep': cep,
                    'endereco_completo': endereco_completo,
                })

            filiais = [f for f in filiais if self._limpar_cnpj(f['cnpj']) != cnpj_limpo]

            resultado['filiais'] = filiais
            resultado['total'] = len(filiais)
            self.cache[cache_key] = resultado
            return resultado

        except Exception as e:
            logger.warning(f"Erro ao consultar filiais CNPJa: {e}")
            resultado['erro'] = f"Erro inesperado: {str(e)}"
            return resultado

    def validar_municipio(self, municipio: str, uf: str) -> Tuple[bool, Optional[str]]:
        if uf not in [
            'AC', 'AL', 'AP', 'AM', 'BA', 'CE', 'DF', 'ES', 'GO', 'MA',
            'MT', 'MS', 'MG', 'PA', 'PB', 'PR', 'PE', 'PI', 'RJ', 'RN',
            'RS', 'RO', 'RR', 'SC', 'SP', 'SE', 'TO'
        ]:
            return False, None
        municipio_normalizado = self.api_localidades.normalizar_municipio(municipio, uf)
        if municipio_normalizado:
            return True, municipio_normalizado
        return False, None



def exibir_status(status: str):
    if status == 'ATIVO':
        st.success(f"**Status:** {status}")
    elif status == 'INATIVO':
        st.error(f"**Status:** {status}")
    else:
        st.warning(f"**Status:** {status}")


def montar_endereco(r: Dict) -> str:
    comp = f" {r.get('complemento', '')}" if r.get('complemento') else ''
    return (
        f"{r.get('logradouro', 'N/A')}, {r.get('numero', 'N/A')}{comp} - "
        f"{r.get('bairro', 'N/A')} - "
        f"{r.get('municipio', 'N/A')}/{r.get('uf', 'N/A')} - "
        f"CEP: {r.get('cep', 'N/A')}"
    )



def main():
    st.title("Consultor CNPJ com Validacao de Localidades")
    st.markdown("Busque dados completos de CNPJs e valide localizacao geografica")

    consultor = ConsultorCNPJ()

    tab1, tab2, tab3, tab4 = st.tabs([
        "Consulta Individual",
        "Filiais",
        "Upload em Massa",
        "Analise",
    ])

 
    with tab1:
        st.header("Consulta Individual de CNPJ")

        col1, col2 = st.columns(2)
        with col1:
            cnpj_input = st.text_input(
                "Digite o CNPJ", placeholder="00.000.000/0000-00", key="cnpj_tab1"
            )
        with col2:
            consultar = st.button("Consultar", key="btn_consultar")

        if consultar:
            if cnpj_input:
                with st.spinner("Consultando API..."):
                    resultado = consultor.consultar_cnpj(cnpj_input)

                st.subheader("Filiais do Grupo")
                with st.spinner("Buscando filiais via CNPJa..."):
                    res_filiais = consultor.consultar_filiais_cnpja(cnpj_input)

                if res_filiais['erro']:
                    st.warning(f"Filiais: {res_filiais['erro']}")
                elif res_filiais['total'] == 0:
                    st.info("Nenhuma filial encontrada para este CNPJ.")
                else:
                    filiais = res_filiais['filiais']
                    col_m1, col_m2, col_m3 = st.columns(3)
                    with col_m1:
                        st.metric("Total de Filiais", res_filiais['total'])
                    with col_m2:
                        ativas = sum(1 for f in filiais if 'ATIVA' in f['situacao'].upper())
                        st.metric("Filiais Ativas", ativas)
                    with col_m3:
                        ufs = set(f['uf'] for f in filiais if f['uf'] != 'N/A')
                        st.metric("Estados", len(ufs))

                    df_filiais = pd.DataFrame(filiais)
                    df_display = df_filiais[
                        ['cnpj', 'tipo', 'nome_fantasia', 'situacao', 'municipio', 'uf', 'endereco_completo']
                    ].copy()
                    df_display.columns = [
                        'CNPJ', 'Tipo', 'Nome Fantasia', 'Situacao', 'Municipio', 'UF', 'Endereco'
                    ]
                    st.dataframe(df_display, use_container_width=True, hide_index=True)

                st.divider()

                col1, col2 = st.columns(2)
                with col1:
                    st.subheader("Dados Basicos")
                    st.write(f"**CNPJ:** {resultado['cnpj']}")
                    st.write(f"**CNPJ Raiz:** {resultado['cnpj_raiz']}")
                    st.write(f"**Razao Social:** {resultado['razao_social']}")
                    st.write(f"**Nome Fantasia:** {resultado['nome_fantasia']}")
                    st.write(f"**Tipo:** {resultado['matriz_filial']}")
                    st.write(f"**Porte:** {resultado['porte']}")
                    st.write(f"**Capital Social:** {resultado['capital_social']}")
                    st.write(f"**Inicio Atividade:** {resultado['data_inicio_atividade']}")
                    exibir_status(resultado['status'])

                with col2:
                    st.subheader("Localizacao")
                    st.write(f"**Municipio:** {resultado['municipio']}")
                    st.write(f"**UF:** {resultado['uf']}")
                    st.write(f"**CEP:** {resultado['cep']}")
                    st.write(f"**Telefone:** {resultado['telefone']}")
                    st.write(f"**Email:** {resultado['email']}")

                    if resultado['uf'] != 'N/A' and resultado['municipio'] != 'N/A':
                        valido, mun_norm = consultor.validar_municipio(
                            resultado['municipio'], resultado['uf']
                        )
                        if valido:
                            st.success(f"Municipio validado: {mun_norm}")
                        else:
                            st.warning("Municipio nao encontrado no IBGE")

                st.subheader("Endereco Completo")
                st.text(montar_endereco(resultado))

                col1, col2 = st.columns(2)
                with col1:
                    st.subheader("Atividade Primaria")
                    st.write(f"**Codigo CNAE:** {resultado['cnae_codigo']}")
                    st.write(f"**Descricao:** {resultado['cnae']}")
                with col2:
                    st.subheader("Informacoes Adicionais")
                    st.write(f"**Natureza Juridica:** {resultado['natureza_juridica']}")
                    st.write(f"**Data Consulta:** {resultado['data_consulta']}")

                cnaes_sec = resultado.get('cnaes_secundarios', [])
                if cnaes_sec:
                    st.subheader(f"Atividades Secundarias ({len(cnaes_sec)})")
                    df_cnaes = pd.DataFrame(cnaes_sec)
                    df_cnaes.columns = ['Codigo', 'Descricao']
                    df_cnaes['Codigo'] = df_cnaes['Codigo'].astype(str)
                    st.dataframe(df_cnaes, use_container_width=True, hide_index=True)
                else:
                    st.subheader("Atividades Secundarias")
                    st.info("Nenhuma atividade secundaria cadastrada.")

            else:
                st.error("Digite um CNPJ valido")

   
    with tab2:
        st.header("Consulta de Filiais / Grupo Empresarial")
        st.markdown(
            "Busca todos os estabelecimentos do grupo via CNPJa (open.cnpja.com). "
            "Informe qualquer CNPJ do grupo (matriz ou filial)."
        )

        col1, col2 = st.columns(2)
        with col1:
            cnpj_filiais = st.text_input(
                "Digite o CNPJ", placeholder="00.000.000/0000-00", key="cnpj_tab2"
            )
        with col2:
            buscar_filiais = st.button("Buscar Filiais", key="btn_filiais")

        if buscar_filiais:
            if cnpj_filiais:
                with st.spinner("Consultando grupo empresarial..."):
                    res = consultor.consultar_filiais_cnpja(cnpj_filiais)

                if res['erro']:
                    st.error(f"Erro: {res['erro']}")
                elif res['total'] == 0:
                    st.info("Nenhuma filial encontrada para este CNPJ.")
                else:
                    filiais = res['filiais']

                    col_m1, col_m2, col_m3 = st.columns(3)
                    with col_m1:
                        st.metric("Total no Grupo", res['total'])
                    with col_m2:
                        qtd_filiais = sum(1 for f in filiais if f['tipo'] == 'FILIAL')
                        st.metric("Filiais", qtd_filiais)
                    with col_m3:
                        ufs = set(f['uf'] for f in filiais if f['uf'] != 'N/A')
                        st.metric("Estados", len(ufs))

                    col_f1, col_f2, col_f3 = st.columns(3)
                    with col_f1:
                        ufs_disp = sorted(ufs)
                        uf_filtro = st.multiselect("Filtrar por UF", ufs_disp, key="uf_tab2")
                    with col_f2:
                        tipo_filtro = st.multiselect(
                            "Filtrar por Tipo", ['MATRIZ', 'FILIAL'],
                            default=['FILIAL'], key="tipo_tab2"
                        )
                    with col_f3:
                        situacoes = sorted(set(f['situacao'] for f in filiais))
                        sit_filtro = st.multiselect(
                            "Filtrar por Situacao", situacoes, key="sit_tab2"
                        )

                    filtrados = filiais
                    if uf_filtro:
                        filtrados = [f for f in filtrados if f['uf'] in uf_filtro]
                    if tipo_filtro:
                        filtrados = [f for f in filtrados if f['tipo'] in tipo_filtro]
                    if sit_filtro:
                        filtrados = [f for f in filtrados if f['situacao'] in sit_filtro]

                    st.markdown(f"**Exibindo {len(filtrados)} registro(s)**")

                    df_filiais = pd.DataFrame(filtrados)
                    colunas = [
                        'cnpj', 'tipo', 'nome_fantasia', 'situacao',
                        'municipio', 'uf', 'endereco_completo'
                    ]
                    colunas = [c for c in colunas if c in df_filiais.columns]
                    df_display = df_filiais[colunas].copy()
                    df_display.columns = [
                        'CNPJ', 'Tipo', 'Nome Fantasia', 'Situacao',
                        'Municipio', 'UF', 'Endereco'
                    ]
                    st.dataframe(df_display, use_container_width=True, hide_index=True)

                    st.divider()
                    st.subheader("Detalhes por Estabelecimento")
                    for f in filtrados:
                        label = f"{f['tipo']} | {f['cnpj']} | {f['municipio']}/{f['uf']}"
                        with st.expander(label):
                            c1, c2 = st.columns(2)
                            with c1:
                                st.write(f"**CNPJ:** {f['cnpj']}")
                                st.write(f"**Nome Fantasia:** {f['nome_fantasia']}")
                                st.write(f"**Tipo:** {f['tipo']}")
                                st.write(f"**Situacao:** {f['situacao']}")
                            with c2:
                                st.write(f"**Logradouro:** {f['logradouro']}, {f['numero']}")
                                if f.get('complemento'):
                                    st.write(f"**Complemento:** {f['complemento']}")
                                st.write(f"**Bairro:** {f['bairro']}")
                                st.write(f"**Municipio/UF:** {f['municipio']}/{f['uf']}")
                                st.write(f"**CEP:** {f['cep']}")

                    csv_filiais = df_filiais.to_csv(index=False, sep=';', encoding='utf-8')
                    st.download_button(
                        label="Download CSV - Filiais",
                        data=csv_filiais,
                        file_name=f"filiais_{consultor._limpar_cnpj(cnpj_filiais)}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        mime="text/csv"
                    )
            else:
                st.error("Digite um CNPJ valido")


    with tab3:
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
                coluna_municipio = st.selectbox(
                    "Coluna com Municipio (opcional)",
                    ["Nenhuma"] + list(df.columns)
                )

            if st.button("Processar em Massa", key="btn_processar"):
                resultados = []
                progress_bar = st.progress(0)
                status_text = st.empty()

                for idx, row in df.iterrows():
                    cnpj = str(row[coluna_cnpj]).strip()
                    uf_base = str(row[coluna_uf]).strip()

                    resultado = consultor.consultar_cnpj(cnpj)

                    valido, mun_norm = consultor.validar_municipio(
                        resultado['municipio'], resultado['uf']
                    )

                    resultado['Validacao_Municipio'] = 'SIM' if valido else 'NAO'
                    resultado['UF_Base'] = uf_base
                    resultado['Match_UF'] = 'SIM' if uf_base == resultado['uf'] else 'NAO'

                    cnaes_sec = resultado.get('cnaes_secundarios', [])
                    resultado['cnaes_secundarios_txt'] = ' | '.join(
                        [f"{c.get('codigo')} - {c.get('descricao')}" for c in cnaes_sec]
                    ) if cnaes_sec else 'N/A'

                    resultado.pop('cnaes_secundarios', None)

                    resultados.append(resultado)

                    progress_bar.progress((idx + 1) / len(df))
                    status_text.text(f"Processados {idx + 1}/{len(df)}")
                    time.sleep(0.2)

                df_resultado = pd.DataFrame(resultados)
                st.success("Processamento concluido!")

                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total Processados", len(df_resultado))
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

   
    with tab4:
        st.header("Analise de Dados")
        st.info("Carregue um arquivo em massa na aba anterior para ver analises")


if __name__ == "__main__":
    main()

