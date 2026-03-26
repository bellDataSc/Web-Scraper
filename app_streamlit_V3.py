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
                cnaes_sec = data.get('cnaes_secundarios', [])
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
                    'cnaes_secundarios': cnaes_sec,
                    'natureza_juridica': data.get('natureza_juridica', 'N/A'),
                    'status': 'ATIVO' if data.get('descricao_situacao_cadastral') == 'ATIVA' else 'INATIVO',
                    'matriz_filial': (
                        'MATRIZ' if data.get('identificador_matriz_filial') == 1
                        else 'FILIAL'
                    ),
                    'data_consulta': datetime.now().isoformat(),
                    'qsa': data.get('qsa', []),
                    'regime_tributario': data.get('regime_tributario', []),
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
                'cnpj': cnpj, 'cnpj_limpo': cnpj_limpo,
                'cnpj_raiz': cnpj_limpo[:8] if len(cnpj_limpo) >= 8 else 'N/A',
                'razao_social': 'N/A', 'nome_fantasia': 'N/A',
                'municipio': 'N/A', 'uf': 'N/A', 'logradouro': 'N/A',
                'numero': 'N/A', 'bairro': 'N/A', 'complemento': '',
                'cep': 'N/A', 'cnae': 'N/A', 'cnae_codigo': 'N/A',
                'cnaes_secundarios': [], 'natureza_juridica': 'N/A',
                'status': 'ERRO', 'matriz_filial': 'N/A',
                'data_consulta': datetime.now().isoformat(),
                'qsa': [], 'regime_tributario': [], 'email': 'N/A',
                'telefone': 'N/A', 'data_inicio_atividade': 'N/A',
                'capital_social': 'N/A', 'porte': 'N/A',
            }
        return resultado

    def consultar_multiplos_cnpjs(self, lista_cnpjs: List[str]) -> List[Dict]:
        """
        Consulta uma lista de CNPJs na BrasilAPI e retorna dados de cada um.
        Usado na aba Filiais para montar o grupo manualmente.
        """
        resultados = []
        for cnpj in lista_cnpjs:
            cnpj = cnpj.strip()
            if not cnpj:
                continue
            dado = self.consultar_cnpj(cnpj)
            resultados.append(dado)
            time.sleep(0.3)
        return resultados

    def validar_municipio(self, municipio: str, uf: str) -> Tuple[bool, Optional[str]]:
        if uf not in ['AC', 'AL', 'AP', 'AM', 'BA', 'CE', 'DF', 'ES', 'GO', 'MA',
                      'MT', 'MS', 'MG', 'PA', 'PB', 'PR', 'PE', 'PI', 'RJ', 'RN',
                      'RS', 'RO', 'RR', 'SC', 'SP', 'SE', 'TO']:
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
        f"{r.get('logradouro','N/A')}, {r.get('numero','N/A')}{comp} - "
        f"{r.get('bairro','N/A')} - "
        f"{r.get('municipio','N/A')}/{r.get('uf','N/A')} - "
        f"CEP: {r.get('cep','N/A')}"
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

                qsa = resultado.get('qsa', [])
                if qsa:
                    st.subheader(f"Quadro Societario ({len(qsa)} socio(s))")
                    df_qsa = pd.DataFrame([{
                        'Nome': s.get('nome_socio', 'N/A'),
                        'Qualificacao': s.get('qualificacao_socio', 'N/A'),
                        'Faixa Etaria': s.get('faixa_etaria', 'N/A'),
                        'Data Entrada': s.get('data_entrada_sociedade', 'N/A'),
                    } for s in qsa])
                    st.dataframe(df_qsa, use_container_width=True, hide_index=True)

                regime = resultado.get('regime_tributario', [])
                if regime:
                    st.subheader("Regime Tributario")
                    df_regime = pd.DataFrame([{
                        'Ano': r.get('ano', 'N/A'),
                        'Tributacao': r.get('forma_de_tributacao', 'N/A'),
                    } for r in regime])
                    st.dataframe(df_regime, use_container_width=True, hide_index=True)

            else:
                st.error("Digite um CNPJ valido")

 
    with tab2:
        st.header("Consulta de Filiais / Grupo Empresarial")
        st.markdown(
            "Informe o CNPJ principal e, em seguida, adicione os CNPJs das filiais "
            "para consultar e comparar enderecos e situacao cadastral via BrasilAPI."
        )
        st.info(
            "A BrasilAPI consulta um CNPJ por vez. Informe cada CNPJ do grupo "
            "separado por virgula ou um por linha para montar o painel completo."
        )

        cnpj_grupo_input = st.text_area(
            "CNPJs do grupo (um por linha ou separados por virgula)",
            placeholder="00.000.000/0001-00\n00.000.000/0002-00\n00.000.000/0003-00",
            height=120,
            key="cnpj_grupo"
        )

        buscar_grupo = st.button("Consultar Grupo", key="btn_grupo")

        if buscar_grupo:
            if cnpj_grupo_input:
                raw = cnpj_grupo_input.replace('\n', ',')
                lista_cnpjs = [c.strip() for c in raw.split(',') if c.strip()]

                if not lista_cnpjs:
                    st.error("Nenhum CNPJ valido informado.")
                else:
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    resultados_grupo = []

                    for i, cnpj in enumerate(lista_cnpjs):
                        with st.spinner(f"Consultando {cnpj}..."):
                            dado = consultor.consultar_cnpj(cnpj)
                            resultados_grupo.append(dado)
                        progress_bar.progress((i + 1) / len(lista_cnpjs))
                        status_text.text(f"Consultados {i + 1}/{len(lista_cnpjs)}")
                        time.sleep(0.3)

                    status_text.empty()
                    progress_bar.empty()

                    # Metricas
                    col_m1, col_m2, col_m3, col_m4 = st.columns(4)
                    with col_m1:
                        st.metric("Total Consultados", len(resultados_grupo))
                    with col_m2:
                        ativos = sum(1 for r in resultados_grupo if r['status'] == 'ATIVO')
                        st.metric("Ativos", ativos)
                    with col_m3:
                        filiais = sum(1 for r in resultados_grupo if r['matriz_filial'] == 'FILIAL')
                        st.metric("Filiais", filiais)
                    with col_m4:
                        ufs = set(r['uf'] for r in resultados_grupo if r['uf'] != 'N/A')
                        st.metric("Estados", len(ufs))

                    # Filtros
                    col_f1, col_f2 = st.columns(2)
                    with col_f1:
                        ufs_disp = sorted(ufs)
                        uf_filtro = st.multiselect("Filtrar por UF", ufs_disp, key="uf_filtro_filiais")
                    with col_f2:
                        tipo_filtro = st.multiselect(
                            "Filtrar por Tipo",
                            ['MATRIZ', 'FILIAL'],
                            key="tipo_filtro_filiais"
                        )

                    filtrados = resultados_grupo
                    if uf_filtro:
                        filtrados = [r for r in filtrados if r['uf'] in uf_filtro]
                    if tipo_filtro:
                        filtrados = [r for r in filtrados if r['matriz_filial'] in tipo_filtro]

                    st.markdown(f"**Exibindo {len(filtrados)} registro(s)**")

                    # Tabela resumo
                    df_grupo = pd.DataFrame([{
                        'CNPJ': r['cnpj'],
                        'Razao Social': r['razao_social'],
                        'Nome Fantasia': r['nome_fantasia'],
                        'Tipo': r['matriz_filial'],
                        'Status': r['status'],
                        'UF': r['uf'],
                        'Municipio': r['municipio'],
                        'Endereco Completo': montar_endereco(r),
                    } for r in filtrados])

                    st.dataframe(df_grupo, use_container_width=True, hide_index=True)

                    # Cards detalhados
                    st.divider()
                    st.subheader("Detalhes por Estabelecimento")
                    for r in filtrados:
                        label = f"{r['matriz_filial']} | {r['cnpj']} | {r['razao_social']}"
                        with st.expander(label):
                            c1, c2 = st.columns(2)
                            with c1:
                                st.write(f"**CNPJ:** {r['cnpj']}")
                                st.write(f"**CNPJ Raiz:** {r['cnpj_raiz']}")
                                st.write(f"**Razao Social:** {r['razao_social']}")
                                st.write(f"**Nome Fantasia:** {r['nome_fantasia']}")
                                st.write(f"**Tipo:** {r['matriz_filial']}")
                                st.write(f"**Porte:** {r['porte']}")
                                exibir_status(r['status'])
                            with c2:
                                st.write(f"**Logradouro:** {r['logradouro']}, {r['numero']}")
                                if r.get('complemento'):
                                    st.write(f"**Complemento:** {r['complemento']}")
                                st.write(f"**Bairro:** {r['bairro']}")
                                st.write(f"**Municipio/UF:** {r['municipio']}/{r['uf']}")
                                st.write(f"**CEP:** {r['cep']}")
                                st.write(f"**Telefone:** {r['telefone']}")
                                st.write(f"**Email:** {r['email']}")
                                st.write(f"**Inicio Atividade:** {r['data_inicio_atividade']}")

                    # Download
                    csv_grupo = df_grupo.to_csv(index=False, sep=';', encoding='utf-8')
                    st.download_button(
                        label="Download CSV - Grupo",
                        data=csv_grupo,
                        file_name=f"grupo_cnpj_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        mime="text/csv"
                    )
            else:
                st.error("Informe ao menos um CNPJ.")

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
                    resultado.pop('qsa', None)
                    resultado.pop('regime_tributario', None)

                    resultados.append(resultado)

                    progress = (idx + 1) / len(df)
                    progress_bar.progress(progress)
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
