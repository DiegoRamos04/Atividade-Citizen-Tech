import os
import textwrap
import time

import avaliacao
import base_dados
import busca_grafo
import prompts

LARGURA_TELA = 72


def limpar_tela():
    """
    Limpa o conteúdo anterior do terminal para manter o foco apenas na
    tela, consulta ou orientação atual.
    """
    os.system("cls" if os.name == "nt" else "clear")


def pausar_retorno():
    """
    Aguarda confirmação do usuário antes de limpar a tela e voltar ao menu.
    """
    input("\nPressione Enter para voltar ao menu principal...")


def formatar_item_lista(texto, recuo_inicial="  ", recuo_seguinte="     "):
    """
    Evita que itens longos de menu ou perguntas ultrapassem a largura do terminal.
    """
    return textwrap.fill(
        str(texto).strip(),
        width=LARGURA_TELA,
        initial_indent=recuo_inicial,
        subsequent_indent=recuo_seguinte,
        break_long_words=False,
        break_on_hyphens=False,
    )


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
    aviso_navegacao = ""

    while True:
        limpar_tela()
        relacionados = busca_grafo.obter_relacionados(base, registro_atual["id"], limite=3)
        resposta_formatada = prompts.gerar_resposta_estruturada(
            registro=registro_atual,
            modelo=modelo_atual,
            relacionados=relacionados,
            pontuacao=pontuacao_atual,
        )
        print(resposta_formatada)

        if termos_atuais:
            print(f"[Busca] Termos correspondidos: {', '.join(termos_atuais)}")
        if tempo_atual is not None:
            print(f"[Métrica] Tempo de processamento da consulta: {tempo_atual:.3f} ms")

        if not relacionados:
            pausar_retorno()
            break

        print("\nContinuidade da consulta (Grafo de Assuntos Relacionados):")
        for idx, item in enumerate(relacionados, start=1):
            reg_rel = item["registro"]
            print(
                formatar_item_lista(
                    f"{idx}. [ID #{reg_rel['id']}] {reg_rel['pergunta']} ({item['motivo']})"
                )
            )
        print("  0. Voltar ao menu principal")

        if aviso_navegacao:
            print(f"\n{aviso_navegacao}")
            aviso_navegacao = ""

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
            aviso_navegacao = "[AVISO] Opção inválida. Digite um número da lista ou 0 para voltar ao menu."


def fluxo_consulta_pergunta(base, temas, modelo_atual):
    """
    Recebe uma pergunta ou palavras-chave em texto livre, valida a entrada,
    mede o tempo de consulta e trata correspondência única, ambiguidade ou
    ausência de resposta confiável na base.
    """
    limpar_tela()
    print("=" * LARGURA_TELA)
    print("CONSULTA POR PERGUNTA OU PALAVRAS-CHAVE")
    print("=" * LARGURA_TELA)
    print("Exemplos: 'Como solicitar o Bilhete Único Especial?' ou 'elevador quebrado'")
    pergunta = input("\nDigite sua dúvida: ")

    inicio = time.perf_counter()
    eh_valida, mensagem_erro = prompts.validar_entrada_consulta(pergunta)

    if not eh_valida:
        tempo_ms = (time.perf_counter() - inicio) * 1000
        limpar_tela()
        print(formatar_item_lista(mensagem_erro, recuo_inicial="", recuo_seguinte=""))
        print(f"[Métrica] Tempo de validação: {tempo_ms:.3f} ms")
        pausar_retorno()
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
        limpar_tela()
        candidatos = resultados[:3]
        print(prompts.gerar_resposta_ambigua(pergunta, candidatos, limite=3))
        print(f"[Métrica] Tempo de busca: {tempo_ms:.3f} ms")

        escolha = input("\nDigite o número da opção desejada (ou 0 para cancelar): ").strip()
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
            print("\n[AVISO] Opção inválida. Retornando ao menu principal.")
            pausar_retorno()

    else:
        limpar_tela()
        print(
            prompts.gerar_resposta_sem_correspondencia(
                pergunta,
                temas,
                sugestoes_iniciais=base[:3],
            )
        )
        print(f"[Métrica] Tempo de busca: {tempo_ms:.3f} ms")
        pausar_retorno()


def fluxo_navegar_por_tema(base, temas, resumo_temas, modelo_atual):
    """
    Navegação hierárquica em 3 níveis exigida pelo edital:
      Nível 1 (Tema) -> Nível 2 (Subtema) -> Nível 3 (Orientação).
    """
    limpar_tela()
    print("=" * LARGURA_TELA)
    print("NAVEGAÇÃO HIERÁRQUICA POR TEMAS E SUBTEMAS")
    print("=" * LARGURA_TELA)
    for idx, tema in enumerate(temas, start=1):
        print(f"  {idx}. {tema} ({resumo_temas[tema]} orientações)")
    print("  0. Voltar ao menu principal")

    escolha_tema = input("\nEscolha o número do tema: ").strip()
    if escolha_tema in ("", "0"):
        return

    if not escolha_tema.isdigit() or not (1 <= int(escolha_tema) <= len(temas)):
        print("\n[ERRO] Opção de tema inexistente. Escolha um número válido do menu.")
        pausar_retorno()
        return

    tema_selecionado = temas[int(escolha_tema) - 1]
    hierarquia = busca_grafo.construir_hierarquia_temas(base)
    subtemas_dict = hierarquia.get(tema_selecionado, {})
    lista_subtemas = sorted(subtemas_dict.keys())

    # Nível 2: Seleção de Subtema
    limpar_tela()
    print("=" * LARGURA_TELA)
    print(f"TEMA: {tema_selecionado.upper()} — SUBTEMAS")
    print("=" * LARGURA_TELA)
    for idx, sub in enumerate(lista_subtemas, start=1):
        print(f"  {idx}. {sub} ({len(subtemas_dict[sub])} orientações)")
    print(f"  {len(lista_subtemas) + 1}. Ver todas as orientações deste tema")
    print("  0. Voltar ao menu principal")

    escolha_sub = input("\nEscolha o número do subtema: ").strip()
    if escolha_sub in ("", "0"):
        return

    if not escolha_sub.isdigit() or not (1 <= int(escolha_sub) <= len(lista_subtemas) + 1):
        print("\n[ERRO] Opção de subtema inexistente. Retornando ao menu principal.")
        pausar_retorno()
        return

    indice_sub = int(escolha_sub)
    if indice_sub <= len(lista_subtemas):
        subtema_selecionado = lista_subtemas[indice_sub - 1]
        orientacoes_filtradas = busca_grafo.filtrar_por_tema(
            base, tema_selecionado, subtema_selecionado
        )
        titulo_nivel = f"{tema_selecionado.upper()} > {subtema_selecionado.upper()}"
    else:
        orientacoes_filtradas = busca_grafo.filtrar_por_tema(base, tema_selecionado)
        titulo_nivel = f"{tema_selecionado.upper()} > TODOS OS SUBTEMAS"

    # Nível 3: Seleção da Orientação
    limpar_tela()
    print("=" * LARGURA_TELA)
    print(f"HIERARQUIA: {titulo_nivel}")
    print("=" * LARGURA_TELA)
    for idx, reg in enumerate(orientacoes_filtradas, start=1):
        print(formatar_item_lista(f"{idx}. [ID #{reg['id']}] {reg['pergunta']}"))
    print("  0. Voltar ao menu principal")

    escolha_item = input("\nEscolha o número da orientação: ").strip()
    if escolha_item in ("", "0"):
        return

    if not escolha_item.isdigit() or not (1 <= int(escolha_item) <= len(orientacoes_filtradas)):
        print("\n[ERRO] Opção inválida. Retornando ao menu principal.")
        pausar_retorno()
        return

    inicio = time.perf_counter()
    registro_escolhido = orientacoes_filtradas[int(escolha_item) - 1]
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
    limpar_tela()
    id_min, id_max = obter_intervalo_ids(base)
    print("=" * LARGURA_TELA)
    print(f"CONSULTA DIRETA POR IDENTIFICADOR (ID #{id_min} a #{id_max})")
    print("=" * LARGURA_TELA)
    entrada = input("Digite o ID da orientação (ou Enter para voltar): ").strip()

    if entrada == "":
        return

    if not entrada.isdigit():
        print("\n[ERRO] Identificador inválido. Informe apenas números inteiros.")
        pausar_retorno()
        return

    inicio = time.perf_counter()
    registro = base_dados.buscar_por_id(base, int(entrada))
    tempo_ms = (time.perf_counter() - inicio) * 1000

    if not registro:
        print(f"\n[ERRO] Nenhuma orientação encontrada com ID #{entrada}.")
        pausar_retorno()
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
    limpar_tela()
    print("=" * LARGURA_TELA)
    print("ESTRATÉGIAS DE PROMPT / FORMATAÇÃO DE RESPOSTA")
    print("=" * LARGURA_TELA)
    for idx, (chave, dados) in enumerate(prompts.MODELOS_PROMPT.items(), start=1):
        ativo = " (ATIVO)" if chave == modelo_atual else ""
        print(f"\n[{idx}] {dados['nome']}{ativo}")
        print(
            formatar_item_lista(
                f"Papel   : {dados['papel_assistente']}",
                recuo_inicial="    ",
                recuo_seguinte="              ",
            )
        )
        print(
            formatar_item_lista(
                f"Formato : {dados['formato_saida']}",
                recuo_inicial="    ",
                recuo_seguinte="              ",
            )
        )
        print("    Regras  :")
        for regra in dados["regras_instrucao"]:
            print(
                formatar_item_lista(
                    regra,
                    recuo_inicial="      - ",
                    recuo_seguinte="        ",
                )
            )

    escolha = input(
        "\nDigite 1 para Modelo Direto, 2 para Modelo Didático (ou Enter para manter): "
    ).strip()

    if escolha == "1":
        print("\n[SUCESSO] Formato alterado para: Resposta Direta e Objetiva.")
        pausar_retorno()
        return "direto"
    if escolha == "2":
        print("\n[SUCESSO] Formato alterado para: Guia Estruturado e Acessível.")
        pausar_retorno()
        return "didatico"
    if escolha != "":
        print("\n[AVISO] Opção inválida. Mantendo o formato atual.")
        pausar_retorno()
    return modelo_atual


def fluxo_comparar_prompts(base):
    """
    Compara os dois modelos de prompt lado a lado em um registro da base,
    evidenciando diferenças de clareza, estrutura e continuidade de consulta.
    """
    limpar_tela()
    id_min, id_max = obter_intervalo_ids(base)
    print("=" * LARGURA_TELA)
    print("COMPARAÇÃO ENTRE OS 2 MODELOS DE PROMPT")
    print("=" * LARGURA_TELA)
    print(f"Informe um ID ({id_min} a {id_max}) ou pressione Enter para usar o ID #1:")
    entrada = input("ID do registro: ").strip()

    if entrada == "":
        id_escolhido = 1
    elif entrada.isdigit():
        id_escolhido = int(entrada)
    else:
        print("\n[ERRO] ID inválido. Informe apenas números.")
        pausar_retorno()
        return

    registro = base_dados.buscar_por_id(base, id_escolhido)
    if not registro:
        print(f"\n[ERRO] Nenhum registro encontrado com ID #{id_escolhido}.")
        pausar_retorno()
        return

    limpar_tela()
    relacionados = busca_grafo.obter_relacionados(base, registro["id"], limite=3)
    print(prompts.comparar_modelos_prompt(registro, relacionados=relacionados))
    relatorio_testes = avaliacao.executar_bateria_testes(base)
    if relatorio_testes.get("comparacao_prompts"):
        print("\n" + prompts.formatar_comparacao_testes(relatorio_testes["comparacao_prompts"]))
    pausar_retorno()


def fluxo_caminho_grafo(base):
    """
    Utiliza o algoritmo de Dijkstra sobre o grafo ponderado de conhecimento
    para encontrar a menor trilha semântica entre duas orientações da base.
    """
    limpar_tela()
    id_min, id_max = obter_intervalo_ids(base)
    print("=" * LARGURA_TELA)
    print("EXPLORADOR DE CAMINHOS NO GRAFO DE CONHECIMENTO (DIJKSTRA)")
    print("=" * LARGURA_TELA)
    print(f"Descubra a menor conexão entre dois registros (IDs #{id_min} a #{id_max}).")
    origem_txt = input("\nID de origem (ex.: 1): ").strip()
    destino_txt = input("ID de destino (ex.: 20): ").strip()

    if not origem_txt.isdigit() or not destino_txt.isdigit():
        print("\n[ERRO] Informe IDs numéricos válidos.")
        pausar_retorno()
        return

    caminho = busca_grafo.encontrar_caminho_assuntos(base, int(origem_txt), int(destino_txt))
    if not caminho:
        print("\n[AVISO] Não foi possível encontrar um caminho entre os IDs informados.")
        pausar_retorno()
        return

    print(f"\nMenor trilha encontrada ({len(caminho) - 1} salto(s) no grafo):")
    for idx, reg in enumerate(caminho):
        prefixo = (
            "Início ->"
            if idx == 0
            else ("Fim    ->" if idx == len(caminho) - 1 else "Passo  ->")
        )
        print(
            formatar_item_lista(
                f"{prefixo} [ID #{reg['id']} | {reg['tema']}] {reg['pergunta']}",
                recuo_inicial="  ",
                recuo_seguinte="            ",
            )
        )
    pausar_retorno()

def _ler_relacionados_input(base):
    """
    Auxiliar opcional para cadastrar conexões explícitas do grafo (campo 'relacionados')
    ao adicionar ou editar um registro pelo terminal.
    """
    entrada_ids = input(
        "IDs relacionados no grafo separados por vírgula (ex.: 1, 6 ou Enter para automático): "
    ).strip()
    if not entrada_ids:
        return None

    relacionados = []
    for pedaco in entrada_ids.split(","):
        pedaco = pedaco.strip()
        if pedaco.isdigit():
            id_rel = int(pedaco)
            reg_destino = base_dados.buscar_por_id(base, id_rel)
            if reg_destino:
                motivo = input(
                    f"  Motivo da conexão com ID #{id_rel} ({reg_destino['tema']}): "
                ).strip()
                relacionados.append({
                    "id": id_rel,
                    "motivo": motivo or f"Assunto relacionado ({reg_destino['tema']})",
                })
    return relacionados


def fluxo_gerenciar_base(base, temas):
    """
    Permite acrescentar ou corrigir registros diretamente pela aplicação,
    persistindo no data/base.json sem alterar o código-fonte.
    """
    limpar_tela()
    print("=" * LARGURA_TELA)
    print("MANUTENÇÃO DA BASE DE CONHECIMENTO (ADICIONAR / CORRIGIR)")
    print("=" * LARGURA_TELA)
    print("  1. Adicionar nova orientação")
    print("  2. Corrigir orientação existente (por ID)")
    print("  0. Voltar ao menu principal")
    print("-" * LARGURA_TELA)

    opcao = input("Escolha uma opção: ").strip()
    if opcao in ("", "0"):
        return

    if opcao == "1":
        limpar_tela()
        proximo_id = base_dados.obter_proximo_id(base)
        print("=" * LARGURA_TELA)
        print(f"CADASTRAR NOVA ORIENTAÇÃO (ID #{proximo_id})")
        print("=" * LARGURA_TELA)
        print("Temas atuais:", ", ".join(temas))

        tema = input("\nTema (escolha um existente ou digite um novo): ").strip()
        pergunta = input("Pergunta de referência: ").strip()
        kw_txt = input("Palavras-chave (separadas por vírgula): ").strip()
        orientacao = input("Orientação resumida: ").strip()
        fonte = input("Fonte / referência verificável: ").strip()
        data_verif = input("Data de verificação (AAAA-MM-DD) [Enter = 2026-11-16]: ").strip() or "2026-11-16"

        palavras_chave = [k.strip() for k in kw_txt.split(",") if k.strip()]
        novo_reg = {
            "id": proximo_id,
            "tema": tema,
            "pergunta": pergunta,
            "palavras_chave": palavras_chave,
            "orientacao": orientacao,
            "fonte": fonte,
            "data_verificacao": data_verif,
        }

        relacionados = _ler_relacionados_input(base)
        if relacionados:
            novo_reg["relacionados"] = relacionados

        sucesso, mensagem = base_dados.adicionar_registro(base, novo_reg)
        print(f"\n[{'SUCESSO' if sucesso else 'ERRO'}] {mensagem}")
        pausar_retorno()

    elif opcao == "2":
        limpar_tela()
        id_min, id_max = obter_intervalo_ids(base)
        print("=" * LARGURA_TELA)
        print(f"CORRIGIR ORIENTAÇÃO EXISTENTE (ID #{id_min} a #{id_max})")
        print("=" * LARGURA_TELA)
        id_txt = input("Informe o ID do registro a corrigir: ").strip()

        if not id_txt.isdigit():
            print("\n[ERRO] ID inválido.")
            pausar_retorno()
            return

        reg = base_dados.buscar_por_id(base, int(id_txt))
        if not reg:
            print(f"\n[ERRO] Registro ID #{id_txt} não encontrado.")
            pausar_retorno()
            return

        print(f"\nEditando [ID #{reg['id']}] {reg['pergunta']}")
        print("(Pressione Enter em qualquer campo para manter o valor atual)\n")

        novo_tema = input(f"Tema [{reg['tema']}]: ").strip() or None
        nova_pergunta = input("Nova pergunta (ou Enter para manter): ").strip() or None
        novas_kws_txt = input("Novas palavras-chave por vírgula (ou Enter para manter): ").strip()
        nova_orientacao = input("Nova orientação (ou Enter para manter): ").strip() or None
        nova_fonte = input(f"Nova fonte [{reg['fonte']}]: ").strip() or None
        nova_data = input(f"Data verificação [{reg['data_verificacao']}]: ").strip() or None

        atualizacoes = {
            "tema": novo_tema,
            "pergunta": nova_pergunta,
            "orientacao": nova_orientacao,
            "fonte": nova_fonte,
            "data_verificacao": nova_data,
        }
        if novas_kws_txt:
            atualizacoes["palavras_chave"] = [k.strip() for k in novas_kws_txt.split(",") if k.strip()]

        relacionados = _ler_relacionados_input(base)
        if relacionados is not None:
            atualizacoes["relacionados"] = relacionados

        sucesso, mensagem = base_dados.atualizar_registro(base, reg["id"], atualizacoes)
        print(f"\n[{'SUCESSO' if sucesso else 'ERRO'}] {mensagem}")
        pausar_retorno()

    else:
        print("\n[ERRO] Opção inválida.")
        pausar_retorno()

def main():
    limpar_tela()
    base = base_dados.carregar_base_conhecimento()
    if not base:
        print("[FALHA] Encerrando o sistema pois nenhuma orientação válida foi carregada.")
        return

    temas = base_dados.listar_temas(base)
    resumo_temas = base_dados.contar_por_tema(base)
    modelo_atual = "didatico"
    primeira_exibicao = True

    while True:
        if not primeira_exibicao:
            limpar_tela()

        rotulo_formato = "Guia Didático" if modelo_atual == "didatico" else "Resposta Direta"
        print("=" * LARGURA_TELA)
        print("IncluiSP | Citizen Assist AI — Assistente de Orientação Cidadã")
        print("Aviso: Protótipo informativo não oficial. Não insira dados pessoais.")
        print("=" * LARGURA_TELA)

        if primeira_exibicao:
            print(
                f"\n[SUCESSO] {len(base)} orientações verificadas carregadas "
                f"em {len(temas)} temas:"
            )
            for indice, tema in enumerate(temas, start=1):
                print(f"  • {indice}. {tema} ({resumo_temas[tema]} orientações)")
            primeira_exibicao = False

        print("\n" + "=" * LARGURA_TELA)
        print("MENU PRINCIPAL")
        print("=" * LARGURA_TELA)
        print("  1. Fazer uma pergunta ou buscar por palavras-chave")
        print("  2. Navegar por temas disponíveis")
        print("  3. Consultar orientação diretamente por ID")
        print(f"  4. Alternar formato das respostas (Atual: {rotulo_formato})")
        print("  5. Comparar os 2 modelos de prompt em uma orientação")
        print("  6. Explorar conexão entre assuntos no grafo (Dijkstra)")
        print("  7. Executar bateria de testes e gerar indicadores (15 testes)")
        print("  8. Gerenciar base de conhecimento (Adicionar ou corrigir)")
        print("  0. Sair")
        print("-" * LARGURA_TELA)

        try:
            opcao = input("Escolha uma opção: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nEncerrando o IncluiSP | Citizen Assist AI. Até logo!")
            break

        try:
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
                limpar_tela()
                relatorio = avaliacao.executar_bateria_testes(base)
                print(avaliacao.formatar_relatorio_avaliacao(relatorio))
                pausar_retorno()
            elif opcao == "8":
                fluxo_gerenciar_base(base, temas)
                temas = base_dados.listar_temas(base)
                resumo_temas = base_dados.contar_por_tema(base)
            elif opcao == "0":
                limpar_tela()
                print("Encerrando o IncluiSP | Citizen Assist AI. Obrigado por utilizar!")
                break
            else:
                print("\n[ERRO] Opção inexistente. Digite um número de 0 a 8.")
                pausar_retorno()
        except (KeyboardInterrupt, EOFError):
            print("\n\n[AVISO] Operação interrompida pelo usuário. Retornando ao menu principal...")
            time.sleep(1.2)


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        print("\n\nEncerrando o IncluiSP | Citizen Assist AI. Até logo!")
