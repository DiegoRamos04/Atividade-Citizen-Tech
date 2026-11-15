import time

import avaliacao
import base_dados
import busca_grafo
import prompts


def obter_intervalo_ids(base):
    """
    Retorna o menor e o maior ID presentes na base carregada,
    permitindo que novos registros no JSON sejam reconhecidos dinamicamente.
    """
    ids = [int(reg["id"]) for reg in base]
    return min(ids), max(ids)


def exibir_e_navegar_orientacao(
    base,
    registro,
    modelo_atual,
    pontuacao=None,
    termos_encontrados=None,
    tempo_ms=None,
):
    """
    Exibe a orientação formatada conforme o modelo de prompt ativo, mostra os
    indicadores da busca (pontuação, termos e tempo) e permite navegar
    continuamente pelos assuntos relacionados no grafo de conhecimento.
    """
    registro_atual = registro
    pontuacao_atual = pontuacao
    termos_atuais = termos_encontrados
    tempo_atual = tempo_ms

    while True:
        relacionados = busca_grafo.obter_relacionados(base, registro_atual["id"], limite=3)
        resposta_formatada = prompts.gerar_resposta_estruturada(
            registro=registro_atual,
            modelo=modelo_atual,
            relacionados=relacionados,
            pontuacao=pontuacao_atual,
        )
        print("\n" + resposta_formatada)

        if termos_atuais:
            print(f"[Busca] Termos correspondidos: {', '.join(termos_atuais)}")
        if tempo_atual is not None:
            print(f"[Métrica] Tempo de processamento da consulta: {tempo_atual:.3f} ms")

        if not relacionados:
            break

        print("\nContinuidade da consulta (Grafo de Assuntos Relacionados):")
        for idx, item in enumerate(relacionados, start=1):
            reg_rel = item["registro"]
            print(f"  {idx}. [ID #{reg_rel['id']}] {reg_rel['pergunta']} ({item['motivo']})")
        print("  0. Voltar ao menu principal")

        escolha = input("\nEscolha um assunto relacionado para explorar (ou 0 para voltar): ").strip()
        if escolha in ("", "0"):
            break

        if escolha.isdigit() and 1 <= int(escolha) <= len(relacionados):
            inicio_nav = time.perf_counter()
            registro_atual = relacionados[int(escolha) - 1]["registro"]
            pontuacao_atual = None
            termos_atuais = None
            tempo_atual = (time.perf_counter() - inicio_nav) * 1000
        else:
            print("[AVISO] Opção inválida. Digite um número da lista ou 0 para voltar ao menu.")


def fluxo_consulta_pergunta(base, temas, modelo_atual):
    """
    Recebe uma pergunta ou palavras-chave em texto livre, valida a entrada,
    mede o tempo de consulta e trata correspondência única, ambiguidade ou
    ausência de resposta confiável na base.
    """
    print("\n--- CONSULTA POR PERGUNTA OU PALAVRAS-CHAVE ---")
    print("Exemplos: 'Como solicitar o Bilhete Único Especial?' ou 'elevador quebrado'")
    pergunta = input("Digite sua dúvida: ")

    inicio = time.perf_counter()
    eh_valida, mensagem_erro = prompts.validar_entrada_consulta(pergunta)

    if not eh_valida:
        tempo_ms = (time.perf_counter() - inicio) * 1000
        print(f"\n{mensagem_erro}")
        print(f"[Métrica] Tempo de validação: {tempo_ms:.3f} ms")
        return

    resultados = busca_grafo.buscar_orientacoes(base, pergunta)
    classificacao = busca_grafo.classificar_resultado_busca(resultados)
    tempo_ms = (time.perf_counter() - inicio) * 1000

    if classificacao == "unico":
        melhor = resultados[0]
        exibir_e_navegar_orientacao(
            base=base,
            registro=melhor["registro"],
            modelo_atual=modelo_atual,
            pontuacao=melhor["pontuacao"],
            termos_encontrados=melhor["termos_encontrados"],
            tempo_ms=tempo_ms,
        )

    elif classificacao == "ambiguo":
        candidatos = resultados[:3]
        print("\n" + prompts.gerar_resposta_ambigua(pergunta, candidatos, limite=3))
        print(f"[Métrica] Tempo de busca: {tempo_ms:.3f} ms")

        escolha = input("Digite o número da opção desejada (ou 0 para cancelar): ").strip()
        if escolha.isdigit() and 1 <= int(escolha) <= len(candidatos):
            selecionado = candidatos[int(escolha) - 1]
            exibir_e_navegar_orientacao(
                base=base,
                registro=selecionado["registro"],
                modelo_atual=modelo_atual,
                pontuacao=selecionado["pontuacao"],
                termos_encontrados=selecionado["termos_encontrados"],
                tempo_ms=tempo_ms,
            )
        elif escolha not in ("", "0"):
            print("[AVISO] Opção inválida. Retornando ao menu principal.")

    else:
        print(
            "\n"
            + prompts.gerar_resposta_sem_correspondencia(
                pergunta,
                temas,
                sugestoes_iniciais=base[:3],
            )
        )
        print(f"[Métrica] Tempo de busca: {tempo_ms:.3f} ms")


def fluxo_navegar_por_tema(base, temas, resumo_temas, modelo_atual):
    """
    Permite escolher um tema principal no menu e selecionar uma orientação
    específica dentro da hierarquia organizada por tema.
    """
    print("\n--- NAVEGAÇÃO HIERÁRQUICA POR TEMAS ---")
    for idx, tema in enumerate(temas, start=1):
        print(f"  {idx}. {tema} ({resumo_temas[tema]} orientações)")
    print("  0. Voltar ao menu principal")

    escolha_tema = input("\nEscolha o número do tema: ").strip()
    if escolha_tema in ("", "0"):
        return

    if not escolha_tema.isdigit() or not (1 <= int(escolha_tema) <= len(temas)):
        print("[ERRO] Opção de tema inexistente. Escolha um número válido do menu.")
        return

    tema_selecionado = temas[int(escolha_tema) - 1]
    orientacoes_tema = busca_grafo.filtrar_por_tema(base, tema_selecionado)

    print(f"\nOrientações disponíveis em '{tema_selecionado}':")
    for idx, reg in enumerate(orientacoes_tema, start=1):
        print(f"  {idx}. [ID #{reg['id']}] {reg['pergunta']}")
    print("  0. Voltar")

    escolha_item = input("\nEscolha o número da orientação: ").strip()
    if escolha_item in ("", "0"):
        return

    if not escolha_item.isdigit() or not (1 <= int(escolha_item) <= len(orientacoes_tema)):
        print("[ERRO] Opção inválida. Retornando ao menu principal.")
        return

    inicio = time.perf_counter()
    registro_escolhido = orientacoes_tema[int(escolha_item) - 1]
    tempo_ms = (time.perf_counter() - inicio) * 1000

    exibir_e_navegar_orientacao(
        base=base,
        registro=registro_escolhido,
        modelo_atual=modelo_atual,
        tempo_ms=tempo_ms,
    )


def fluxo_consultar_por_id(base, modelo_atual):
    """
    Recupera diretamente uma orientação pelo seu identificador numérico (ID),
    atendendo ao requisito de busca por identificador, tema ou palavras-chave.
    """
    id_min, id_max = obter_intervalo_ids(base)
    print(f"\n--- CONSULTA DIRETA POR IDENTIFICADOR (ID #{id_min} a #{id_max}) ---")
    entrada = input("Digite o ID da orientação (ou Enter para voltar): ").strip()

    if entrada == "":
        return

    if not entrada.isdigit():
        print("[ERRO] Identificador inválido. Informe apenas números inteiros.")
        return

    inicio = time.perf_counter()
    registro = base_dados.buscar_por_id(base, int(entrada))
    tempo_ms = (time.perf_counter() - inicio) * 1000

    if not registro:
        print(f"[ERRO] Nenhuma orientação encontrada com ID #{entrada}.")
        return

    exibir_e_navegar_orientacao(
        base=base,
        registro=registro,
        modelo_atual=modelo_atual,
        tempo_ms=tempo_ms,
    )


def fluxo_alternar_prompt(modelo_atual):
    """
    Apresenta a documentação dos dois modelos de instrução/prompt (papel,
    regras e formato) e permite alternar o modelo ativo no assistente.
    """
    print("\n--- ESTRATÉGIAS DE PROMPT / FORMATAÇÃO DE RESPOSTA ---")
    for idx, (chave, dados) in enumerate(prompts.MODELOS_PROMPT.items(), start=1):
        ativo = " (ATIVO)" if chave == modelo_atual else ""
        print(f"\n[{idx}] {dados['nome']}{ativo}")
        print(f"    Papel   : {dados['papel_assistente']}")
        print(f"    Formato : {dados['formato_saida']}")
        print("    Regras  :")
        for regra in dados["regras_instrucao"]:
            print(f"      - {regra}")

    escolha = input(
        "\nDigite 1 para Modelo Direto, 2 para Modelo Didático (ou Enter para manter): "
    ).strip()

    if escolha == "1":
        print("[SUCESSO] Formato alterado para: Resposta Direta e Objetiva.")
        return "direto"
    if escolha == "2":
        print("[SUCESSO] Formato alterado para: Guia Estruturado e Acessível.")
        return "didatico"
    if escolha != "":
        print("[AVISO] Opção inválida. Mantendo o formato atual.")
    return modelo_atual


def fluxo_comparar_prompts(base):
    """
    Compara os dois modelos de prompt lado a lado em um registro da base,
    evidenciando diferenças de clareza, estrutura e continuidade de consulta.
    """
    id_min, id_max = obter_intervalo_ids(base)
    print("\n--- COMPARAÇÃO ENTRE OS 2 MODELOS DE PROMPT ---")
    print(f"Informe um ID ({id_min} a {id_max}) ou pressione Enter para usar o ID #1 (Bilhete Único):")
    entrada = input("ID do registro: ").strip()

    if entrada == "":
        id_escolhido = 1
    elif entrada.isdigit():
        id_escolhido = int(entrada)
    else:
        print("[ERRO] ID inválido. Informe apenas números.")
        return

    registro = base_dados.buscar_por_id(base, id_escolhido)
    if not registro:
        print(f"[ERRO] Nenhum registro encontrado com ID #{id_escolhido}.")
        return

    relacionados = busca_grafo.obter_relacionados(base, registro["id"], limite=3)
    print(prompts.comparar_modelos_prompt(registro, relacionados=relacionados))


def fluxo_caminho_grafo(base):
    """
    Utiliza o algoritmo de Dijkstra sobre o grafo ponderado de conhecimento
    para encontrar a menor trilha semântica entre duas orientações da base.
    """
    id_min, id_max = obter_intervalo_ids(base)
    print("\n--- EXPLORADOR DE CAMINHOS NO GRAFO DE CONHECIMENTO (DIJKSTRA) ---")
    print(f"Descubra a menor conexão entre dois registros (IDs #{id_min} a #{id_max}).")
    origem_txt = input("ID de origem (ex.: 1): ").strip()
    destino_txt = input("ID de destino (ex.: 20): ").strip()

    if not origem_txt.isdigit() or not destino_txt.isdigit():
        print("[ERRO] Informe IDs numéricos válidos.")
        return

    caminho = busca_grafo.encontrar_caminho_assuntos(base, int(origem_txt), int(destino_txt))
    if not caminho:
        print("[AVISO] Não foi possível encontrar um caminho entre os IDs informados.")
        return

    print(f"\nMenor trilha encontrada ({len(caminho) - 1} salto(s) no grafo):")
    for idx, reg in enumerate(caminho):
        prefixo = (
            "Início ->"
            if idx == 0
            else ("Fim    ->" if idx == len(caminho) - 1 else "Passo  ->")
        )
        print(f"  {prefixo} [ID #{reg['id']} | {reg['tema']}] {reg['pergunta']}")


def main():
    print("=" * 72)
    print("IncluiSP | Citizen Assist AI — Assistente de Orientação Cidadã")
    print("Aviso: Protótipo informativo não oficial. Não insira dados pessoais.")
    print("=" * 72)

    base = base_dados.carregar_base_conhecimento()
    if not base:
        print("\n[FALHA] Encerrando o sistema pois nenhuma orientação válida foi carregada.")
        return

    temas = base_dados.listar_temas(base)
    resumo_temas = base_dados.contar_por_tema(base)
    modelo_atual = "didatico"

    print(
        f"\n[SUCESSO] {len(base)} orientações verificadas carregadas "
        f"em {len(temas)} temas:"
    )
    for indice, tema in enumerate(temas, start=1):
        print(f"  • {indice}. {tema} ({resumo_temas[tema]} orientações)")

    while True:
        rotulo_formato = "Guia Didático" if modelo_atual == "didatico" else "Resposta Direta"
        print("\n" + "=" * 72)
        print("MENU PRINCIPAL")
        print("=" * 72)
        print("  1. Fazer uma pergunta ou buscar por palavras-chave")
        print("  2. Navegar por temas disponíveis")
        print("  3. Consultar orientação diretamente por ID")
        print(f"  4. Alternar formato das respostas (Atual: {rotulo_formato})")
        print("  5. Comparar os 2 modelos de prompt em uma orientação")
        print("  6. Explorar conexão entre assuntos no grafo (Dijkstra)")
        print("  7. Executar bateria de testes e gerar indicadores (15 testes)")
        print("  0. Sair")
        print("-" * 72)

        try:
            opcao = input("Escolha uma opção: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nEncerrando o IncluiSP | Citizen Assist AI. Até logo!")
            break

        if opcao == "1":
            fluxo_consulta_pergunta(base, temas, modelo_atual)
        elif opcao == "2":
            fluxo_navegar_por_tema(base, temas, resumo_temas, modelo_atual)
        elif opcao == "3":
            fluxo_consultar_por_id(base, modelo_atual)
        elif opcao == "4":
            modelo_atual = fluxo_alternar_prompt(modelo_atual)
        elif opcao == "5":
            fluxo_comparar_prompts(base)
        elif opcao == "6":
            fluxo_caminho_grafo(base)
        elif opcao == "7":
            relatorio = avaliacao.executar_bateria_testes(base)
            print("\n" + avaliacao.formatar_relatorio_avaliacao(relatorio))
        elif opcao == "0":
            print("\nEncerrando o IncluiSP | Citizen Assist AI. Obrigado por utilizar!")
            break
        else:
            print("[ERRO] Opção inexistente. Digite um número de 0 a 7.")


if __name__ == "__main__":
    main()
