from base_dados import (
    carregar_base_conhecimento,
    contar_por_tema,
    listar_temas,
)


def main():
    print("=" * 60)
    print("IncluiSP | Citizen Assist AI - Inicializando Sistema")
    print("=" * 60)

    base_dados = carregar_base_conhecimento()

    if not base_dados:
        print("\n[FALHA] Encerrando o sistema pois nenhuma orientação válida foi carregada.")
        return

    temas = listar_temas(base_dados)
    resumo_temas = contar_por_tema(base_dados)

    print(f"\n[SUCESSO] {len(base_dados)} orientações válidas carregadas!")
    print("\nTemas disponíveis na base:")
    for indice, tema in enumerate(temas, start=1):
        print(f"  {indice}. {tema} ({resumo_temas[tema]} orientações)")
    print("-" * 60)


if __name__ == "__main__": main()
