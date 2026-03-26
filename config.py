"""
config.py
---------
Centraliza todas as constantes, parâmetros de filtro e configurações
do pipeline de processamento de propostas SICONV.
"""

from datetime import datetime
import os
from pathlib import Path

# ── Diretório raiz do projeto ──────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent

# ── Ano de referência (dinâmico) ───────────────────────────────────────────
ANO_ATUAL = datetime.now().year

# ── Caminhos dos arquivos ──────────────────────────────────────────────────
# raw/ → dados brutos de entrada (SICONV e Controle SEI baixado do OneDrive)
# data/ → arquivos gerados pelo pipeline (resultado, cache de token)
CAMINHO_CSV = BASE_DIR / "raw" / "siconv_proposta.csv"
CAMINHO_CONTROLE_SEI = BASE_DIR / "raw" / "Controle_SEI.xlsx"
CAMINHO_TOKEN_CACHE = BASE_DIR / "data" / ".token_cache.bin"

# ── Gmail API (OAuth2) ─────────────────────────────────────────────────────
# json.json fica na pasta pai do projeto (mesmo local usado no script R)
CAMINHO_GMAIL_CREDENTIALS = BASE_DIR / "json.json"
# Token gerado após o primeiro login — fica em data/ (ignorado pelo git)
CAMINHO_GMAIL_TOKEN = BASE_DIR / "data" / ".gmail_token.json"

# ── Autenticação Microsoft (PublicClientApplication) ──────────────────────
# App ID público do Azure CLI — funciona em qualquer tenant sem registro próprio
AZURE_CLIENT_ID = "d3590ed6-52b3-4102-aeff-aad2292ab01c"

# Link de compartilhamento do Controle_SEI.xlsx no OneDrive
CONTROLE_SEI_SHAREPOINT_URL = "https://cecad365-my.sharepoint.com/:x:/g/personal/m16900633_ca_mg_gov_br/IQDavaoigLEtS4nQs_JCschkAQiUl1Fh8hZN7KJTul3aQOI?e=DeIO1a"

# ── UF de interesse ────────────────────────────────────────────────────────
UF_ALVO = "MG"

# ── Naturezas jurídicas monitoradas ───────────────────────────────────────
NATUREZAS_JURIDICAS = [
    "Administração Pública Estadual ou do Distrito Federal",
    "Empresa pública/Sociedade de economia mista",
    "EMMAG EMPRESA MUNICIPAL DE MECANIZACAO AGRICOLA",
]

# ── Situações de proposta consideradas "ativas" (sem Plano de Trabalho) ───
SITUACOES_ATIVAS = [
    "Proposta/Plano de Trabalho Cadastrados",
    "Proposta/Plano de Trabalho em Análise",
    "Proposta/Plano de Trabalho Aprovados",
    "Proposta Aprovada e Plano de Trabalho em Complementação",
    "Proposta/Plano de Trabalho em Complementação",
    "Proposta Aprovada e Plano de Trabalho em Análise",
    "Proposta/Plano de Trabalho Complementado em Análise",
    "Proposta/Plano de Trabalho Complementado Enviado para Análise",
    "Proposta Aprovada e Plano de Trabalho Complementado Enviado para Análise",
    "Proposta Aprovada e Plano de Trabalho Complementado em Análise",
    "Proposta/Plano de Trabalho Enviado para Análise",
    "Enviada para Análise Preliminar",
    "Proposta Aprovada/Aguardando Plano de Trabalho",
]

# ── Índices das colunas relevantes no CSV do SICONV ───────────────────────
# [UF_PROPONENTE, NR_PROPOSTA, ANO_PROP, NATUREZA_JURIDICA,
#  NM_PROPONENTE, SIT_PROPOSTA, VL_GLOBAL_PROP]
# Atenção: R usa índice base 1, Python usa base 0 — por isso cada valor é o do R menos 1
INDICES_COLUNAS = [1, 6, 7, 10, 16, 23, 31]

# ── Propostas a excluir manualmente por natureza jurídica ─────────────────
# Propostas já tratadas ou fora do escopo de atuação da DCGCE
PROPOSTAS_EXCLUIR = {
    "Administração Pública Estadual ou do Distrito Federal": [
        "254/2024", "5211/2024", "8125/2024", "8126/2024",
        "3991/2024", "14019/2024", "14020/2024", "14021/2024",
        "14022/2024", "227/2025", "63401/2025", "68428/2025",
    ],
    "Empresa pública/Sociedade de economia mista": [
        "6163/2024", "76332/2025",
    ],
    "EMMAG EMPRESA MUNICIPAL DE MECANIZACAO AGRICOLA": [],
}

# ── Valor global mínimo (filtra registros inválidos/zerados) ──────────────
VL_GLOBAL_MIN = 2
