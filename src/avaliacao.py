import time

from busca_grafo import buscar_orientacoes, classificar_resultado_busca
import busca_grafo
from prompts import validar_entrada_consulta
import prompts

CASOS_DE_TESTE = [
    # Perguntas Diretas
    {
        "id_teste": "T01",
        "categoria": "Pergunta Direta",
        "consulta": "Como solicitar o Bilhete Único Especial para Pessoas com Deficiência?",
        "comportamento_esperado": "unico",
        "id_esperado": 1,
        "descricao_esperada": "Orientação sobre Bilhete Único Especial da SPTrans (ID #1)",
    },
    {
        "id_teste": "T02",
        "categoria": "Pergunta Direta",
        "consulta": "A Estação da Luz tem elevador para cadeirante?",
        "comportamento_esperado": "unico",
        "id_esperado": 3,
        "descricao_esperada": "Acessibilidade e elevadores da Estação da Luz (ID #3)",
    },
    {
        "id_teste": "T03",
        "categoria": "Pergunta Direta",
        "consulta": "Como pedir isenção de IPVA em São Paulo?",
        "comportamento_esperado": "unico",
        "id_esperado": 4,
        "descricao_esperada": "Isenção de IPVA via sistema SIVEI/Fazenda SP (ID #4)",
    },
    {
        "id_teste": "T04",
        "categoria": "Pergunta Direta",
        "consulta": "Tenho direito a acompanhante em consulta pelo SUS?",
        "comportamento_esperado": "unico",
        "id_esperado": 2,
        "descricao_esperada": "Direito a acompanhante garantido pela LBI no SUS (ID #2)",
    },
    {
        "id_teste": "T05",
        "categoria": "Pergunta Direta",
        "consulta": "Qual o percentual de cotas para PCD em concursos públicos?",
        "comportamento_esperado": "unico",
        "id_esperado": 8,
        "descricao_esperada": "Reserva de vagas de 5% a 20% em concursos (ID #8)",
    },
    # Reformulações (Linguagem Cotidiana)
    {
        "id_teste": "T06",
        "categoria": "Reformulação",
        "consulta": "Quero usar aquela van adaptada porta a porta da SPTrans",
        "comportamento_esperado": "unico",
        "id_esperado": 17,
        "descricao_esperada": "Funcionamento e cadastro do Serviço Atende+ (ID #17)",
    },
    {
        "id_teste": "T07",
        "categoria": "Reformulação",
        "consulta": "Cheguei na estação de metrô e o elevador está quebrado",
        "comportamento_esperado": "unico",
        "id_esperado": 18,
        "descricao_esperada": "Procedimento para elevador inoperante e telefone 0800 (ID #18)",
    },
    {
        "id_teste": "T08",
        "categoria": "Reformulação",
        "consulta": "O motorista do ônibus recusou meu embarque e fui constrangido",
        "comportamento_esperado": "unico",
        "id_esperado": 19,
        "descricao_esperada": "Como agir e denunciar recusa de embarque no 156 (ID #19)",
    },
    {
        "id_teste": "T09",
        "categoria": "Reformulação",
        "consulta": "Quais museus em SP dão gratuidade para pessoa com deficiência e acompanhante?",
        "comportamento_esperado": "unico",
        "id_esperado": 20,
        "descricao_esperada": "Acessibilidade e gratuidade em museus de SP (ID #20)",
    },
    {
        "id_teste": "T10",
        "categoria": "Reformulação",
        "consulta": "Vou fazer o ENEM e preciso de tempo extra na prova",
        "comportamento_esperado": "unico",
        "id_esperado": 11,
        "descricao_esperada": "Direito a 60 minutos adicionais no ENEM/vestibulares (ID #11)",
    },
    # Cenários de Limitação e Borda (mínimo de 3 exigidos)
    {
        "id_teste": "T11",
        "categoria": "Limitação (Entrada Vazia)",
        "consulta": "   ",
        "comportamento_esperado": "entrada_invalida",
        "id_esperado": None,
        "descricao_esperada": "Bloquear entrada em branco e orientar o usuário",
    },
    {
        "id_teste": "T12",
        "categoria": "Limitação (Ambiguidade)",
        "consulta": "bpc",
        "comportamento_esperado": "ambiguo",
        "id_esperado": None,
        "descricao_esperada": "Detectar empate entre ID #6 (BPC geral) e ID #16 (BPC vs Auxílio)",
    },
    {
        "id_teste": "T13",
        "categoria": "Limitação (Ambiguidade)",
        "consulta": "elevador",
        "comportamento_esperado": "ambiguo",
        "id_esperado": None,
        "descricao_esperada": "Detectar múltiplas correspondências (Estação Luz, Ônibus, Manutenção)",
    },
    {
        "id_teste": "T14",
        "categoria": "Limitação (Fora do Escopo)",
        "consulta": "Como tirar passaporte na Polícia Federal?",
        "comportamento_esperado": "sem_correspondencia",
        "id_esperado": None,
        "descricao_esperada": "Informar ausência na base sem inventar resposta",
    },
    {
        "id_teste": "T15",
        "categoria": "Limitação (Fora do Escopo)",
        "consulta": "Como renovar a CNH vencida no Poupatempo?",
        "comportamento_esperado": "sem_correspondencia",
        "id_esperado": None,
        "descricao_esperada": "Informar ausência na base e sugerir temas disponíveis",
    },
]


def executar_caso_teste(base_dados, caso):
    """
    Executa uma única consulta da bateria de testes, mede o tempo de processamento
    em milissegundos e verifica se o resultado obtido corresponde ao esperado.
    """
    consulta = caso["consulta"]
    inicio = time.perf_counter()

    eh_valida, _ = validar_entrada_consulta(consulta)
    if not eh_valida:
        comportamento_obtido = "entrada_invalida"
        id_obtido = None
        descricao_obtida = "Entrada vazia/inválida bloqueada com sucesso"
    else:
        resultados = buscar_orientacoes(base_dados, consulta)
        comportamento_obtido = classificar_resultado_busca(resultados)

        if comportamento_obtido == "unico":
            reg = resultados[0]["registro"]
            id_obtido = int(reg["id"])
            descricao_obtida = f"ID #{id_obtido}: {reg['pergunta'][:48]}..."
        elif comportamento_obtido == "ambiguo":
            ids_candidatos = [int(item["registro"]["id"]) for item in resultados[:3]]
            id_obtido = None
            descricao_obtida = f"Ambiguidade detectada entre IDs {ids_candidatos}"
        else:
            id_obtido = None
            descricao_obtida = "Sem correspondência na base (limite informado)"

    fim = time.perf_counter()
    tempo_ms = (fim - inicio) * 1000

    # Critério de acerto: comportamento igual ao esperado e, quando aplicável, ID exato
    if caso["comportamento_esperado"] == "unico":
        acertou = (
            comportamento_obtido == "unico"
            and id_obtido == caso["id_esperado"]
        )
    else:
        acertou = comportamento_obtido == caso["comportamento_esperado"]

    return {
        "id_teste": caso["id_teste"],
        "categoria": caso["categoria"],
        "consulta": consulta.strip() if consulta.strip() else "(vazio)",
        "descricao_esperada": caso["descricao_esperada"],
        "descricao_obtida": descricao_obtida,
        "acertou": acertou,
        "tempo_ms": tempo_ms,
    }


def executar_bateria_testes(base_dados, casos=CASOS_DE_TESTE):
    """
    Executa todos os casos de teste configurados e calcula os indicadores de desempenho:
      - Total de testes, acertos e erros;
      - Taxa de acerto percentual (%);
      - Tempo médio, mínimo e máximo de consulta (ms);
      - Desempenho agrupado por categoria de teste.
    """
    resultados_detalhados = []
    por_categoria = {}

    for caso in casos:
        resultado = executar_caso_teste(base_dados, caso)
        resultados_detalhados.append(resultado)

        cat = resultado["categoria"]
        if cat not in por_categoria:
            por_categoria[cat] = {"total": 0, "acertos": 0}
        por_categoria[cat]["total"] += 1
        if resultado["acertou"]:
            por_categoria[cat]["acertos"] += 1

    total_testes = len(resultados_detalhados)
    total_acertos = sum(1 for r in resultados_detalhados if r["acertou"])
    total_erros = total_testes - total_acertos
    taxa_acerto = (total_acertos / total_testes * 100) if total_testes > 0 else 0.0

    tempos = [r["tempo_ms"] for r in resultados_detalhados]
    tempo_medio_ms = sum(tempos) / total_testes if total_testes > 0 else 0.0
    tempo_min_ms = min(tempos) if tempos else 0.0
    tempo_max_ms = max(tempos) if tempos else 0.0

    casos_validos_prompt = []
    for caso in casos:
        if caso["tipo_esperado"] is not None:
            res_busca = busca_grafo.buscar_orientacoes(base_dados, caso["pergunta"])
            if res_busca:
                casos_validos_prompt.append({"registro": res_busca[0]["registro"]})

    comparacao_prompts = prompts.avaliar_modelos_em_consultas(
        casos_validos_prompt,
        lambda reg_id: busca_grafo.obter_relacionados(base_dados, reg_id, limite=3),
    )

    return {
        "resultados": resultados_detalhados,
        "total_testes": total_testes,
        "total_acertos": total_acertos,
        "total_erros": total_erros,
        "taxa_acerto": taxa_acerto,
        "tempo_medio_ms": tempo_medio_ms,
        "tempo_min_ms": tempo_min_ms,
        "tempo_max_ms": tempo_max_ms,
        "por_categoria": por_categoria,
        "comparacao_prompts": comparacao_prompts,
    }


def formatar_relatorio_avaliacao(relatorio):
    """
    Formata os resultados e indicadores da bateria de testes para exibição clara
    no terminal (pronto para captura de tela e inclusão no relatório PDF).
    """
    linhas = []
    linhas.append("=" * 76)
    linhas.append("RELATÓRIO DE AVALIAÇÃO E INDICADORES DE DESEMPENHO — IncluiSP")
    linhas.append("=" * 76)

    for item in relatorio["resultados"]:
        status = "ACERTO" if item["acertou"] else "ERRO"
        linhas.append(
            f"[{item['id_teste']}] {status:<6} | {item['tempo_ms']:6.3f} ms | {item['categoria']}"
        )
        linhas.append(f"      Pergunta : {item['consulta']}")
        linhas.append(f"      Esperado : {item['descricao_esperada']}")
        linhas.append(f"      Obtido   : {item['descricao_obtida']}")
        linhas.append("-" * 76)

    linhas.append("INDICADORES CONSOLIDADOS:")
    linhas.append(f"  • Total de testes executados : {relatorio['total_testes']}")
    linhas.append(f"  • Respostas corretas         : {relatorio['total_acertos']}")
    linhas.append(f"  • Falhas                     : {relatorio['total_erros']}")
    linhas.append(f"  • Taxa de acerto geral       : {relatorio['taxa_acerto']:.1f}%")
    linhas.append(
        f"  • Tempo médio de consulta    : {relatorio['tempo_medio_ms']:.3f} ms "
        f"(mín: {relatorio['tempo_min_ms']:.3f} ms | máx: {relatorio['tempo_max_ms']:.3f} ms)"
    )

    linhas.append("\nDESEMPENHO POR CATEGORIA DE TESTE:")
    for categoria, dados in relatorio["por_categoria"].items():
        taxa_cat = (dados["acertos"] / dados["total"] * 100) if dados["total"] > 0 else 0.0
        linhas.append(
            f"  • {categoria:<30}: {dados['acertos']}/{dados['total']} ({taxa_cat:.1f}%)"
        )

    if relatorio.get("comparacao_prompts"):
        linhas.append("")
        linhas.append(prompts.formatar_comparacao_testes(relatorio["comparacao_prompts"]))

    linhas.append("=" * 76)
    return "\n".join(linhas)
