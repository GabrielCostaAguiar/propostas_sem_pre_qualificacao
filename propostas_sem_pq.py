"""
propostas_sem_pq.py
-------------------
Pipeline principal: carrega o dump do SICONV, aplica filtros de negócio
e retorna as propostas de MG que ainda não possuem Plano de Trabalho (PQ)
aprovado, cruzando com o Controle SEI da DCGCE.
"""

import base64
import os
import pandas as pd
from dotenv import load_dotenv
from msal import PublicClientApplication, SerializableTokenCache
import requests

from config import (
    ANO_ATUAL,
    UF_ALVO,
    CAMINHO_CONTROLE_SEI,
    CAMINHO_TOKEN_CACHE,
    AZURE_CLIENT_ID,
    CONTROLE_SEI_SHAREPOINT_URL,
    CAMINHO_GMAIL_CREDENTIALS,
    CAMINHO_GMAIL_TOKEN,
    NATUREZAS_JURIDICAS,
    SITUACOES_ATIVAS,
    INDICES_COLUNAS,
    PROPOSTAS_EXCLUIR,
    VL_GLOBAL_MIN,
)

load_dotenv()


# ─── Autenticação ─────────────────────────────────────────────────────────────

_SCOPES = ["https://graph.microsoft.com/Files.Read.All"]

def obter_token_microsoft() -> str:
    """
    Obtém token via PublicClientApplication com device code flow.
    Na primeira execução abre um link para login no navegador.
    Nas execuções seguintes reutiliza o token cacheado em disco.
    """
    cache = SerializableTokenCache()
    if CAMINHO_TOKEN_CACHE.exists():
        cache.deserialize(CAMINHO_TOKEN_CACHE.read_text())

    tenant = os.getenv("AZURE_TENANT_ID", "organizations")
    app = PublicClientApplication(
        client_id=AZURE_CLIENT_ID,
        authority=f"https://login.microsoftonline.com/{tenant}",
        token_cache=cache,
    )

    # Tenta usar token cacheado silenciosamente
    contas = app.get_accounts()
    if contas:
        resultado = app.acquire_token_silent(_SCOPES, account=contas[0])
        if resultado and "access_token" in resultado:
            if cache.has_state_changed:
                CAMINHO_TOKEN_CACHE.write_text(cache.serialize())
            return resultado["access_token"]

    # Sem cache válido: inicia device code flow
    flow = app.initiate_device_flow(scopes=_SCOPES)
    print("\n" + flow["message"] + "\n")  # Ex: "Abra https://microsoft.com/devicelogin e insira o código XXXXXXXX"
    resultado = app.acquire_token_by_device_flow(flow)

    if "access_token" not in resultado:
        raise ValueError(f"Falha na autenticação: {resultado.get('error_description', 'Sem detalhes')}")

    if cache.has_state_changed:
        CAMINHO_TOKEN_CACHE.write_text(cache.serialize())

    return resultado["access_token"]

# ─── Extração (Extract) ───────────────────────────────────────────────────────

def carregar_propostas_siconv(caminho_csv: str) -> pd.DataFrame:
    """Lê o CSV do SICONV com fallback de encoding (Latin-1 → UTF-8)."""
    for encoding in ("Latin-1", "UTF-8"):
        try:
            return pd.read_csv(caminho_csv, sep=";", encoding=encoding)
        except UnicodeDecodeError:
            print(f"Encoding {encoding} falhou, tentando próximo...")
    raise ValueError(f"Não foi possível ler o arquivo: {caminho_csv}")

# ─── Transformação (Transform) ────────────────────────────────────────────────

def filtrar_propostas(df: pd.DataFrame) -> pd.DataFrame:
    """
    Aplica o pipeline completo de filtros:
      1. Seleciona colunas relevantes
      2. Filtra por UF e ano
      3. Filtra por natureza jurídica monitorada
      4. Remove propostas da lista de exclusão manual
      5. Filtra situações ativas (sem PQ concluído)
      6. Remove registros com valor global inválido
    """
    # 1. Colunas de interesse
    df = df.iloc[:, INDICES_COLUNAS].copy()

    # 2. UF e ano
    df = df[(df["UF_PROPONENTE"] == UF_ALVO) & (df["ANO_PROP"] == ANO_ATUAL)]

    # 3. Natureza jurídica
    df = df[df["NATUREZA_JURIDICA"].isin(NATUREZAS_JURIDICAS)]

    # 4. Exclusões manuais (por natureza jurídica)
    df["NR_PROPOSTA"] = df["NR_PROPOSTA"].astype(str).str.strip()
    mascaras = []
    for natureza, excluir in PROPOSTAS_EXCLUIR.items():
        if excluir:
            mask = (df["NATUREZA_JURIDICA"] == natureza) & (df["NR_PROPOSTA"].isin(excluir))
            mascaras.append(mask)
    if mascaras:
        mascara_excluir = mascaras[0]
        for m in mascaras[1:]:
            mascara_excluir = mascara_excluir | m
        df = df[~mascara_excluir]

    # 5. Situações ativas
    df = df[df["SIT_PROPOSTA"].isin(SITUACOES_ATIVAS)]

    # 6. Valor global mínimo
    df = df[df["VL_GLOBAL_PROP"] > VL_GLOBAL_MIN]

    return df.reset_index(drop=True)


def baixar_controle_sei() -> pd.DataFrame:
    """
    Baixa o Controle_SEI.xlsx via sharing link do SharePoint (Graph API)
    e salva localmente sobrescrevendo o arquivo anterior.
    """
    token = obter_token_microsoft()

    # Codifica o link de compartilhamento no formato exigido pela Graph API
    encoded = base64.b64encode(CONTROLE_SEI_SHAREPOINT_URL.encode("utf-8")).decode("utf-8")
    encoded = encoded.rstrip("=").replace("/", "_").replace("+", "-")
    share_id = f"u!{encoded}"

    response = requests.get(
        f"https://graph.microsoft.com/v1.0/shares/{share_id}/driveItem/content",
        headers={"Authorization": f"Bearer {token}"},
        allow_redirects=True,
    )

    if response.status_code != 200:
        raise ValueError(f"Erro ao baixar Controle SEI: {response.status_code} — {response.text}")

    CAMINHO_CONTROLE_SEI.parent.mkdir(parents=True, exist_ok=True)
    CAMINHO_CONTROLE_SEI.write_bytes(response.content)
    print(f"      Controle SEI baixado: {CAMINHO_CONTROLE_SEI}")
    return pd.read_excel(CAMINHO_CONTROLE_SEI)


def processar_controle_sei(df_sei: pd.DataFrame) -> pd.DataFrame:
    """
    Extrai e limpa a coluna de NR_PROPOSTA do Controle SEI.
    Equivalente ao trecho do R:
        oportunidades = oportunidades[, c(3)]
        setnames(oportunidades, "NR_PROPOSTA")
        oportunidades <- na.omit(oportunidades)
    """
    df = df_sei.iloc[:, 2].to_frame(name="NR_PROPOSTA")  # coluna 3 da planilha (índice 2)
    df["NR_PROPOSTA"] = df["NR_PROPOSTA"].astype(str).str.strip()
    df = df[df["NR_PROPOSTA"] != "nan"].reset_index(drop=True)
    return df


def cruzar_bases(df_propostas: pd.DataFrame, df_sei: pd.DataFrame) -> pd.DataFrame:
    """
    Retorna as propostas do SICONV que NÃO estão no Controle SEI.
    Equivalente ao anti_join do R:
        propostas_sem_PQ = propostas_siconv %>% anti_join(oportunidades, by="NR_PROPOSTA")
    """
    df_propostas = df_propostas.copy()
    df_propostas["NR_PROPOSTA"] = df_propostas["NR_PROPOSTA"].astype(str).str.strip()

    # merge com indicador para saber quais vieram só do lado esquerdo (SICONV)
    df_merged = df_propostas.merge(df_sei[["NR_PROPOSTA"]], on="NR_PROPOSTA", how="left", indicator=True)
    df_sem_sei = df_merged[df_merged["_merge"] == "left_only"].drop(columns=["_merge"])
    return df_sem_sei.reset_index(drop=True)


# ─── Carga (Load) ─────────────────────────────────────────────────────────────

def preparar_saida(df: pd.DataFrame) -> pd.DataFrame:
    """
    Renomeia e seleciona as colunas para o resultado final.
    Equivalente ao trecho do R:
        propostas_sem_PQ = rename(propostas_sem_PQ, Nº_Proposta=NR_PROPOSTA,
                                  Proponente=NM_PROPONENTE, ...)
        propostas_sem_PQ = propostas_sem_PQ[, c(5, 3, 6, 7)]
    """
    df = df.rename(columns={
        "NM_PROPONENTE": "Proponente",
        "VL_GLOBAL_PROP": "Valor_global",
        "SIT_PROPOSTA": "Situacao_proposta",
    })
    return df[["Proponente", "ANO_PROP", "Situacao_proposta", "Valor_global"]]


def exportar_resultado(df: pd.DataFrame, caminho_saida: str) -> None:
    """Exporta o resultado final para um arquivo Excel."""
    df.to_excel(caminho_saida, index=False)
    print(f"      Resultado exportado: {caminho_saida}")


def montar_tabela_html(df: pd.DataFrame) -> str:
    """
    Gera uma tabela HTML estilizada com as propostas sem PQ.
    Substitui o tableHTML() do R com visual mais limpo e profissional.
    Colunas: Proponente, ANO_PROP, Situacao_proposta, Valor_global
    """
    estilo_tabela = (
        "border-collapse: collapse; width: 100%; font-family: Arial, sans-serif;"
        "font-size: 13px;"
    )
    estilo_cabecalho = (
        "background-color: #1F4E79; color: white; font-weight: bold;"
        "padding: 10px 12px; text-align: left; border: 1px solid #ccc;"
    )
    estilo_celula = "padding: 8px 12px; border: 1px solid #ccc; text-align: left;"
    estilo_linha_par = "background-color: #EBF3FB;"  # azul claro
    estilo_linha_impar = "background-color: #FFFFFF;"

    cabecalhos = {
        "Proponente": "Proponente",
        "ANO_PROP": "Ano",
        "Situacao_proposta": "Situação da Proposta",
        "Valor_global": "Valor Global (R$)",
    }

    # Monta o cabeçalho
    ths = "".join(f'<th style="{estilo_cabecalho}">{nome}</th>' for nome in cabecalhos.values())
    thead = f"<thead><tr>{ths}</tr></thead>"

    # Monta as linhas
    linhas = []
    for i, row in df.iterrows():
        estilo_linha = estilo_linha_par if i % 2 == 0 else estilo_linha_impar
        # Formata Valor_global como moeda brasileira
        try:
            valor = f"R$ {float(row['Valor_global']):_.2f}".replace(".", ",").replace("_", ".")
        except (ValueError, TypeError):
            valor = row["Valor_global"]

        tds = (
            f'<td style="{estilo_celula}">{row["Proponente"]}</td>'
            f'<td style="{estilo_celula}">{row["ANO_PROP"]}</td>'
            f'<td style="{estilo_celula}">{row["Situacao_proposta"]}</td>'
            f'<td style="{estilo_celula}">{valor}</td>'
        )
        linhas.append(f'<tr style="{estilo_linha}">{tds}</tr>')

    tbody = f"<tbody>{''.join(linhas)}</tbody>"
    return f'<table style="{estilo_tabela}">{thead}{tbody}</table>'


def enviar_email(df_propostas: pd.DataFrame, tem_propostas: bool) -> None:
    """
    Envia e-mail via Gmail API (OAuth2 / HTTPS).
    Equivalente ao bloco gmailr do script R:
        gm_auth_configure(path = "json.json")
        gm_auth(email = '...')
        gm_send_message(...)
    Na primeira execução abre o navegador para autorizar. O token fica
    salvo em data/.gmail_token.json e é reutilizado nas próximas execuções.
    """
    import base64
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build

    GMAIL_SCOPES = ["https://www.googleapis.com/auth/gmail.send"]

    remetente = os.getenv("GMAIL_EMAIL")
    destinatario = os.getenv("EMAIL_DESTINO")

    if not all([remetente, destinatario]):
        print("      GMAIL_EMAIL ou EMAIL_DESTINO não configurados no .env — e-mail não enviado.")
        return

    # Carrega token salvo ou faz login (equivalente ao gm_auth_configure + gm_auth do R)
    creds = None
    if CAMINHO_GMAIL_TOKEN.exists():
        creds = Credentials.from_authorized_user_file(str(CAMINHO_GMAIL_TOKEN), GMAIL_SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                str(CAMINHO_GMAIL_CREDENTIALS), GMAIL_SCOPES
            )
            creds = flow.run_local_server(port=0)
        CAMINHO_GMAIL_TOKEN.parent.mkdir(parents=True, exist_ok=True)
        CAMINHO_GMAIL_TOKEN.write_text(creds.to_json())

    service = build("gmail", "v1", credentials=creds)

    # Monta o e-mail
    msg = MIMEMultipart("alternative")
    msg["From"] = remetente
    msg["To"] = destinatario

    assinatura = """
        <br><br>
        <span style="font-family: Arial, sans-serif; font-size: 12px; color: #555;">
        Esta é uma comunicação automática, gentileza não responder este e-mail.
        Quaisquer dúvidas, entrem em contato pelo e-mail dcgce@casacivil.mg.gov.br<br><br>
        <strong>Diretoria Central de Gestão de Convênios de Entrada - DCGCE</strong><br>
        Superintendência Central de Gestão e Captação de Recursos - SCGCR<br>
        Subsecretaria de Relações Institucionais<br>
        Secretaria de Estado de Casa Civil - SCC<br>
        Governo do Estado de Minas Gerais
        </span>
    """

    estilo_p = "font-family: Arial, sans-serif; font-size: 13px;"

    if tem_propostas:
        msg["Subject"] = "ENVIE PROPOSTA TRANSFEREGOV P/ PRE QUALIFICACAO"
        tabela_html = montar_tabela_html(df_propostas)
        corpo = f"""
            <p style="{estilo_p}">Prezados (as),</p>
            <p style="{estilo_p}">Identificamos a inclusão de nova proposta de seu(s) órgão(s)/entidade(s) na
            TransfereGov, mas ainda não recebemos a solicitação de pré-qualificação.
            Lembramos que essa solicitação deve ser feita antes do envio da proposta ao
            concedente, uma vez que a DCGCE/SCC realiza uma análise minuciosa da proposta e,
            se pertinente, envia recomendações de alterações nos projetos para uma maior chance
            de captação do recurso e para mitigar possíveis futuros problemas na execução do
            instrumento e evitar perda de recursos. Dessa forma, solicitamos que nos seja(m)
            enviado(s) o(s) pedido(s) de pré-qualificação da(s) proposta(s) abaixo:</p>
            <br>
            {tabela_html}
            <br>
            <p style="{estilo_p}">MESMO QUE A(S) PROPOSTA(S) ACIMA TENHA(M) SIDO ANALISADA(S) OU ESTEJA(M) EM
            ANÁLISE PELO CONCEDENTE, vocês devem nos enviar a pré-qualificação em até 5 dias,
            conforme o simples passo a passo constante no arquivo anexo.</p>
            <p style="{estilo_p}">Ressaltamos que, caso não sejam enviadas as propostas para a pré-qualificação no
            prazo disposto pelo Decreto de Programação Orçamentária do Estado de Minas Gerais
            (Decreto nº 48.574, de 17 de fevereiro de 2023), a aprovação de cotas orçamentárias
            por parte da Casa Civil, para todas as fontes de recurso que transitam no Tesouro
            Estadual, ficará suspensa para o seu órgão/entidade até que seja regularizada a
            situação da pré-qualificação. Aproveitamos a oportunidade para solicitar que as
            próximas propostas sejam pré-qualificadas ANTES do envio ao concedente.</p>
            {assinatura}
        """
    else:
        msg["Subject"] = "PROPOSTAS TRANSFEREGOV P/ PRE QUALIFICACAO"
        corpo = f"""
            <p style="{estilo_p}">Prezados (as),</p>
            <p style="{estilo_p}">No momento, não há proposta para ser pré-qualificada.</p>
            {assinatura}
        """

    msg.attach(MIMEText(corpo, "html"))

    # Envia via Gmail API (usa HTTPS porta 443 — não é bloqueado por firewall corporativo)
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    service.users().messages().send(userId="me", body={"raw": raw}).execute()
    print("      E-mail enviado com sucesso.")


