# Propostas SICONV sem Plano de Trabalho

![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python)
![pandas](https://img.shields.io/badge/pandas-ETL-lightgrey?logo=pandas)
![Azure AD](https://img.shields.io/badge/Azure%20AD-MSAL-0078D4?logo=microsoftazure)
![Status](https://img.shields.io/badge/status-em%20desenvolvimento-yellow)

Pipeline de dados para monitoramento automatizado de propostas de convênios federais (SICONV) que ainda não possuem Plano de Trabalho (PQ) aprovado, com foco em entidades do estado de Minas Gerais.

> Desenvolvido no contexto da **DCGCE — Diretoria de Captação e Gestão de Convênios Estaduais**, com o objetivo de substituir um processo manual repetitivo por uma automação confiável e rastreável.

---

## Problema

A equipe precisava identificar, dentre centenas de propostas abertas no SICONV, quais das entidades estaduais de MG ainda não haviam avançado para a etapa de Plano de Trabalho — processo feito manualmente, sujeito a erros e consumindo horas de trabalho a cada ciclo.

## Solução

Pipeline ETL em Python que:
1. **Extrai** o dump público do SICONV (CSV com milhares de registros)
2. **Transforma** aplicando regras de negócio da DCGCE (UF, ano, natureza jurídica, situação, exclusões manuais)
3. **Cruza** com o Controle SEI interno (OneDrive/Excel) para identificar propostas ainda sem processo aberto
4. **Entrega** uma lista priorizada para atuação da equipe

---

## Arquitetura do Pipeline

```
siconv_proposta.csv          Controle_SEI.xlsx (OneDrive)
       │                              │
       ▼                              ▼
carregar_propostas_siconv()    baixar_controle_sei()        ← Extract
       │                              │
       ▼                              │
filtrar_propostas()                   │                     ← Transform
  ├── Filtra UF = MG                  │
  ├── Filtra Ano atual                │
  ├── Filtra Natureza Jurídica        │
  ├── Remove exclusões manuais        │
  ├── Filtra Situações ativas         │
  └── Remove valores inválidos        │
       │                              │
       └──────────┬───────────────────┘
                  ▼
          cruzar_com_sei()                                  ← Transform
                  │
                  ▼
          exportar_resultado()                              ← Load
                  │
                  ▼
         propostas_sem_pq.xlsx
```

---

## Tecnologias

| Tecnologia | Uso |
|---|---|
| **Python 3.10+** | Linguagem principal |
| **pandas** | Manipulação e filtragem do CSV do SICONV |
| **openpyxl** | Leitura/escrita de planilhas Excel |
| **MSAL** | Autenticação no Azure Active Directory |
| **requests** | Chamadas à Microsoft Graph API (OneDrive) |
| **python-dotenv** | Gerenciamento seguro de credenciais |

---

## Estrutura do Projeto

```
propostas_sem_pq_python/
├── propostas_sem_pq.py   # Pipeline principal (Extract → Transform → Load)
├── config.py             # Constantes e parâmetros de negócio
├── requirements.txt      # Dependências do projeto
├── .env.example          # Template de variáveis de ambiente
├── .gitignore
├── data/                 # Arquivos de dados (não versionados)
│   ├── siconv_proposta.csv
│   └── Controle_SEI.xlsx
└── README.md
```

---

## Como Executar

### Pré-requisitos

- Python 3.10+
- Credenciais de aplicativo no Azure Active Directory (para acesso ao OneDrive)

### Instalação

```bash
# Clone o repositório
git clone https://github.com/seu-usuario/propostas-sem-pq.git
cd propostas-sem-pq

# Crie e ative o ambiente virtual
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
.venv\Scripts\activate     # Windows

# Instale as dependências
pip install -r requirements.txt
```

### Configuração

```bash
# Copie o template de variáveis de ambiente
cp .env.example .env

# Edite o .env com suas credenciais Azure
AZURE_CLIENT_ID=...
AZURE_CLIENT_SECRET=...
AZURE_TENANT_ID=...
```

### Execução

```bash
# Coloque o arquivo siconv_proposta.csv em data/
# e execute o pipeline
python propostas_sem_pq.py
```

---

## Filtros de Negócio Aplicados

| Dimensão | Critério |
|---|---|
| UF | Minas Gerais (`MG`) |
| Ano | Ano corrente (dinâmico) |
| Natureza Jurídica | Administração Pública Estadual, Empresa Pública/Soc. Economia Mista, EMMAG |
| Situação | 13 situações ativas mapeadas (sem PQ concluído) |
| Exclusões | Lista de propostas já tratadas pela equipe (configurável em `config.py`) |
| Valor Global | > R$ 2,00 (remove registros inválidos) |

---

## Roadmap

- [x] ETL com filtros de negócio (CSV do SICONV)
- [x] Configuração centralizada via `config.py`
- [x] Autenticação Azure AD (estrutura pronta)
- [ ] Integração com OneDrive via Microsoft Graph API
- [ ] Cruzamento com Controle SEI
- [ ] Exportação automática do resultado
- [ ] Agendamento via cron/Task Scheduler

---

## Fonte dos Dados

Os dados do SICONV são públicos e disponíveis em:
[Transferegov — Dados Abertos](https://www.gov.br/transferegov/pt-br/acesso-a-informacao/dados-abertos)

---

## Licença

Distribuído sob a licença MIT. Veja `LICENSE` para mais informações.
