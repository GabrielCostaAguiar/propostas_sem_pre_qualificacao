"""
main.py
-------
Ponto de entrada do pipeline. Execute este arquivo para rodar o programa completo.

Fluxo:
  1. Baixa o Controle SEI do OneDrive (SharePoint)
  2. Carrega e filtra as propostas do SICONV
  3. Cruza as duas bases para encontrar propostas sem PQ
  4. Exporta o resultado em Excel e envia e-mail
"""

from config import CAMINHO_CSV, ANO_ATUAL, UF_ALVO, BASE_DIR
from propostas_sem_pq import (
    baixar_controle_sei,
    processar_controle_sei,
    carregar_propostas_siconv,
    filtrar_propostas,
    cruzar_bases,
    preparar_saida,
    exportar_resultado,
    enviar_email,
)


def main():
    print("=== Iniciando pipeline: Propostas sem Plano de Trabalho ===\n")

    # ── Passo 1: Baixar Controle SEI do OneDrive ───────────────────────────────
    # Na primeira execução vai pedir para abrir um link e fazer login.
    # Nas próximas execuções o login é feito automaticamente.
    print("[1/4] Baixando Controle SEI do OneDrive...")
    df_sei_raw = baixar_controle_sei()
    df_sei = processar_controle_sei(df_sei_raw)
    print(f"      {len(df_sei)} registros no Controle SEI.\n")

    # ── Passo 2: Carregar propostas SICONV ─────────────────────────────────────
    print(f"[2/4] Carregando CSV do SICONV: {CAMINHO_CSV}")
    df_raw = carregar_propostas_siconv(CAMINHO_CSV)
    print(f"      {len(df_raw):,} registros carregados.\n")

    # ── Passo 3: Filtrar propostas ─────────────────────────────────────────────
    print(f"[3/4] Filtrando propostas (UF={UF_ALVO}, Ano={ANO_ATUAL})...")
    df_filtrado = filtrar_propostas(df_raw)
    print(f"      {len(df_filtrado)} propostas ativas após filtro.\n")

    # ── Passo 4: Cruzar com Controle SEI ──────────────────────────────────────
    print("[4/4] Cruzando com Controle SEI (buscando propostas sem PQ)...")
    df_sem_pq = cruzar_bases(df_filtrado, df_sei)
    print(f"      {len(df_sem_pq)} propostas sem PQ identificadas.\n")

    # ── Resultado ──────────────────────────────────────────────────────────────
    if len(df_sem_pq) > 0:
        df_saida = preparar_saida(df_sem_pq)

        caminho_saida = BASE_DIR / "data" / "propostas_sem_PQ.xlsx"
        exportar_resultado(df_saida, caminho_saida)

        print("\n--- Propostas sem PQ ---")
        print(df_saida.to_string(index=False))

        print("\nEnviando e-mail de alerta...")
        enviar_email(df_saida, tem_propostas=True)

    else:
        print("Nenhuma proposta sem PQ encontrada.")

        print("\nEnviando e-mail informativo...")
        enviar_email(None, tem_propostas=False)

    print("\n=== Pipeline concluído com sucesso ===")


if __name__ == "__main__":
    main()
