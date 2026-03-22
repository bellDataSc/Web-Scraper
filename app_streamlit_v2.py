import pandas as pd
import streamlit as st

from consulta_cnpj_massa_v2 import ConsultorCNPJMassaV2


st.set_page_config(page_title="Web Scraper V2", page_icon="📊", layout="wide")

st.title("Web Scraper V2")
st.caption("Consulta em massa de CNPJ com validacao geografica e exportacao V2")

uploaded_file_v2 = st.file_uploader("Envie a planilha Excel", type=["xlsx", "xls"])

if "resultado_v2" not in st.session_state:
    st.session_state["resultado_v2"] = None

if uploaded_file_v2 is not None:
    df_preview_v2 = pd.read_excel(uploaded_file_v2)
    st.subheader("Preview")
    st.dataframe(df_preview_v2.head(20), use_container_width=True)

    if st.button("Processar V2", type="primary"):
        temp_path_v2 = "input_streamlit_v2.xlsx"
        df_preview_v2.to_excel(temp_path_v2, index=False)

        processor_v2 = ConsultorCNPJMassaV2(delay=0.2)
        df_entrada_v2 = processor_v2.ler_excel_v2(temp_path_v2)

        progress_bar_v2 = st.progress(0)
        status_box_v2 = st.empty()

        resultados_parciais_v2 = []
        total_v2 = len(df_entrada_v2)

        for idx in range(total_v2):
            row_df_v2 = df_entrada_v2.iloc[[idx]].copy()
            parcial_v2 = processor_v2.processar_lote_v2(row_df_v2)
            resultados_parciais_v2.append(parcial_v2)
            progresso_v2 = int(((idx + 1) / total_v2) * 100)
            progress_bar_v2.progress(progresso_v2)
            status_box_v2.write(f"Processando V2 {idx + 1}/{total_v2}")

        resultado_v2 = pd.concat(resultados_parciais_v2, ignore_index=True)
        st.session_state["resultado_v2"] = resultado_v2

if st.session_state["resultado_v2"] is not None:
    st.subheader("Resultado V2")
    st.dataframe(st.session_state["resultado_v2"], use_container_width=True)

    csv_bytes_v2 = st.session_state["resultado_v2"].to_csv(index=False, encoding="utf-8-sig", sep=";").encode("utf-8-sig")
    xlsx_buffer_path_v2 = "resultado_streamlit_v2.xlsx"
    st.session_state["resultado_v2"].to_excel(xlsx_buffer_path_v2, index=False)

    col1_v2, col2_v2 = st.columns(2)

    with col1_v2:
        st.download_button(
            "Baixar CSV V2",
            data=csv_bytes_v2,
            file_name="resultado_web_scraper_v2.csv",
            mime="text/csv"
        )

    with col2_v2:
        with open(xlsx_buffer_path_v2, "rb") as file_v2:
            st.download_button(
                "Baixar XLSX V2",
                data=file_v2.read(),
                file_name="resultado_web_scraper_v2.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
