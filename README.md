# Consultor CNPJ em Massa com Validacao de Localidades

Script Python + Streamlit para consultar dados completos de CNPJs em massa, com validacao geografica usando API IBGE e cruzamento com dados de localizacao.

## Recursos Principais

- **Consulta Individual**: Busque dados completos de um CNPJ (razao social, endereco, atividade, etc)
- **Processamento em Massa**: Upload de Excel com multiplos CNPJs para consulta automatizada
- **API de Localidades (IBGE)**: Validacao e normalizacao de municipios por UF
- **Cruzamento de Dados**: Compara dados da origem com informacoes da API de receita
- **Regioes Metropolitanas**: Identifica automaticamente CNPJs em regioes metropolitanas
- **Relatorios Detalhados**: Gera CSV com todas as informacoes e validacoes

## Instalacao

```bash
pip install -r requirements.txt
```

## Uso

### Script em Linha de Comando

```bash
python consulta_cnpj_massa.py
```

O script espera um arquivo `20251222-Empresas-mapeadas.xlsx` com as colunas:
- `CNPJ`: CNPJ da empresa
- `UF do preco`: Estado de origem
- `Municipio`: Cidade de origem (opcional)

Gera output: `relatorio_cnpj_completo.csv`

### Streamlit (Interface Web)

```bash
streamlit run app_streamlit.py
```

Acesse http://localhost:8501 no navegador

## APIs Utilizadas

### Brasil API
Endpoint: `https://brasilapi.com.br/api/cnpj/v1/{cnpj}`

Retorna:
- Razao social e nome fantasia
- Endereco completo (logradouro, numero, bairro, CEP)
- Atividade principal (CNAE com codigo e descricao)
- Natureza juridica
- Status da empresa
- Data de situacao cadastral

### IBGE - API de Localidades
Endpoint: `https://servicodados.ibge.gov.br/api/v1/localidades`

Retorna:
- Lista de municipios por UF
- Normalizacao de nomes de cidades
- Validacao de localizacoes geograficas

## Estrutura de Output

### CSV Gerado com as Seguintes Colunas

| Coluna | Descricao |
|--------|----------|
| CNPJ | CNPJ consultado |
| Empresa_Original | Nome da empresa no arquivo de entrada |
| UF_Origem | Estado informado no arquivo |
| Municipio_Origem | Municipio informado no arquivo |
| Razao_Social | Razao social conforme receita |
| Nome_Fantasia | Nome fantasia conforme receita |
| Municipio_API | Municipio conforme API (normalizado) |
| UF_API | Estado conforme API |
| Validacao_Municipio | SIM/NAO se municipio existe no IBGE |
| Regiao_Metropolitana | Identificacao de RM (RM_SAOPAULO, RM_RIO, etc) |
| Match_UF | SIM/NAO se UF coincide |
| Match_Municipio | SIM/NAO se municipio coincide |
| Logradouro | Rua/avenida |
| Numero | Numero do endereco |
| Bairro | Bairro |
| CEP | CEP |
| CNAE | Descricao da atividade |
| CNAE_Codigo | Codigo CNAE |
| Natureza_Juridica | Tipo de pessoa juridica |
| Status | ATIVO/INATIVO/ERRO_CONSULTA |
| Data_Situacao | Data da ultima atualizacao cadastral |
| Data_Consulta | Quando foi feita a consulta |

## Regioes Metropolitanas Mapeadas

- RM_SAOPAULO: Sao Paulo, Guarulhos, Campinas, Santo Andre, etc
- RM_RIO: Rio de Janeiro, Niteroi, Sao Goncalo, Duque de Caxias, etc
- RM_BELO_HORIZONTE: Belo Horizonte, Contagem, Betim, etc
- RM_BRASILIA: Brasilia, Taguatinga, Ceilandia, etc
- RM_CURITIBA: Curitiba, Araucaria, Campo Largo, etc
- RM_PORTO_ALEGRE: Porto Alegre, Viamao, Canoas, etc
- RM_SALVADOR: Salvador, Lauro de Freitas, Camacari, etc
- RM_RECIFE: Recife, Jaboatao dos Guararapes, Olinda, etc
- RM_FORTALEZA: Fortaleza, Maracanaú, Caucaia, etc
- RM_MANAUS: Manaus, Itacoatiara, Iranduba

## Relatorio de Saida

O script gera:

1. **CSV com dados completos** - Importavel em Excel, Power BI, etc
2. **Relatorio em console** com:
   - Estatisticas gerais de processamento
   - Taxa de validacao de municipios
   - Coincidencias entre dados de origem e API
   - Distribuicao por regioes metropolitanas
   - Principais atividades (CNAE)

Exemplo de saida:

```
RELATORIO FINAL - ANALISE DE CNPJS COM VALIDACAO GEOGRAFICA
================================================================
ESTATISTICAS GERAIS
Total de CNPJs processados: 3.145
CNPJs com dados completos: 3.087
CNPJs com erro: 58

VALIDACAO GEOGRAFICA
Municipios validados com sucesso: 2.945 (93.6%)
Municipios nao encontrados: 200 (6.4%)

COINCIDENCIA DE DADOS
UF coincidentes: 2.890 (92.0%)
UF diferentes: 255 (8.0%)
```

## Configuracao

Ajuste no codigo:
- `arquivo_entrada`: Nome do arquivo Excel
- `coluna_cnpj`: Nome da coluna com CNPJs
- `coluna_uf`: Nome da coluna com UF
- `coluna_municipio`: Nome da coluna com municipios (opcional)

## Performance

- Rate limit: 0.3s por consulta (ajustavel)
- Cache em memoria de municipios IBGE
- Cache de respostas de CNPJ para evitar repeticoes
- Processamento sequencial (pode ser paralelizado se necessario)

## Limitacoes

- Brasil API pode ter rate limit em producao
- IBGE API pode estar indisponivel ocasionalmente
- Alguns CNPJs podem estar inativos ou com dados inconsistentes
- Nomes de municipios variados podem nao normalizar perfeitamente

## Proximos Passos

- Adicionar suporte a batch processing paralelo
- Integrar com banco de dados (SQLite/PostgreSQL)
- Dashboard com Streamlit + Plotly
- Exportacao para Power BI

## Licenca

MIT License
