import csv
from pathlib import Path
import time
from busca_grafo import (
    buscar_orientacoes,
    buscar_simples_palavra_chave,
    classificar_resultado_busca,
    classificar_resultado_simples,
)
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
    # Cenários de Estresse Lexical (Erros de Digitação, Gírias e Frases Longas)
    {
        "id_teste": "T16",
        "categoria": "Estresse (Erro de Digitação)",
        "consulta": "Como pedir isensao de ipva?",
        "comportamento_esperado": "unico",
        "id_esperado": 4,
        "descricao_esperada": "Identificar isenção de IPVA mesmo com erro ortográfico (ID #4)",
    },
    {
        "id_teste": "T17",
        "categoria": "Estresse (Gíria Regional)",
        "consulta": "Onde consigo passe livre de busao em SP?",
        "comportamento_esperado": "unico",
        "id_esperado": 1,
        "descricao_esperada": "Identificar Bilhete Único Especial a partir de gíria (ID #1)",
    },
    {
        "id_teste": "T18",
        "categoria": "Estresse (Frase Longa)",
        "consulta": (
            "Oi bom dia tudo bem eu queria saber se por acaso existe algum lugar "
            "na cidade onde eu possa pedir aquela carteirinha para estacionar na "
            "vaga azul de deficiente"
        ),
        "comportamento_esperado": "unico",
        "id_esperado": 5,
        "descricao_esperada": "Filtrar ruído coloquial e recuperar Credencial Defis (ID #5)",
    },
]


def executar_caso_teste(base_dados, caso, indice_invertido=None):
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
        resultados = buscar_orientacoes(base_dados, consulta, indice_invertido=indice_invertido)
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

def comparar_algoritmos_busca(base_dados, casos=CASOS_DE_TESTE):
    """
    Executa os mesmos casos de teste no algoritmo baseline (Busca Simples por
    palavra-chave sem pesos) e compara os indicadores com a Busca Ranqueada.
    """
    acertos_simples = 0
    tempos_simples = []
    divergencias = []

    for caso in casos:
        consulta = caso["consulta"]
        inicio = time.perf_counter()

        eh_valida, _ = validar_entrada_consulta(consulta)
        if not eh_valida:
            comp_obtido = "entrada_invalida"
            id_obtido = None
        else:
            res_simples = buscar_simples_palavra_chave(base_dados, consulta)
            comp_obtido = classificar_resultado_simples(res_simples)
            id_obtido = int(res_simples[0]["registro"]["id"]) if comp_obtido == "unico" else None

        tempo_ms = (time.perf_counter() - inicio) * 1000
        tempos_simples.append(tempo_ms)

        if caso["comportamento_esperado"] == "unico":
            acertou = comp_obtido == "unico" and id_obtido == caso["id_esperado"]
        else:
            acertou = comp_obtido == caso["comportamento_esperado"]

        if acertou:
            acertos_simples += 1
        else:
            divergencias.append(f"{caso['id_teste']} ({comp_obtido})")

    total = len(casos)
    taxa_simples = (acertos_simples / total * 100) if total > 0 else 0.0
    tempo_medio_simples = sum(tempos_simples) / total if total > 0 else 0.0

    return {
        "total_testes": total,
        "acertos_simples": acertos_simples,
        "taxa_simples": taxa_simples,
        "tempo_medio_simples_ms": tempo_medio_simples,
        "divergencias_simples": divergencias,
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
    indice_invertido = busca_grafo.construir_indice_invertido(base_dados)

    for caso in casos:
        resultado = executar_caso_teste(base_dados, caso, indice_invertido=indice_invertido)
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
        if caso.get("id_esperado") is not None:
            res_busca = busca_grafo.buscar_orientacoes(base_dados, caso["consulta"], indice_invertido=indice_invertido)
            if res_busca:
                casos_validos_prompt.append({"registro": res_busca[0]["registro"]})

    comparacao_prompts = prompts.avaliar_modelos_em_consultas(
        casos_validos_prompt,
        lambda reg_id: busca_grafo.obter_relacionados(base_dados, reg_id, limite=3),
    )
    comparacao_algoritmos = comparar_algoritmos_busca(base_dados, casos)

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
        "comparacao_algoritmos": comparacao_algoritmos,
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

    if relatorio.get("comparacao_algoritmos"):
        comp = relatorio["comparacao_algoritmos"]
        linhas.append("")
        linhas.append("-" * 76)
        linhas.append(f"COMPARAÇÃO DE ALGORITMOS DE BUSCA (MESMOS {comp['total_testes']} TESTES)")
        linhas.append("-" * 76)
        linhas.append(f"{'Algoritmo':<36} | {'Acertos':<11} | {'Taxa':<8} | {'Tempo Médio'}")
        linhas.append("-" * 76)
        linhas.append(
            f"{'1. Busca Simples (Palavra-Chave)':<36} | "
            f"{comp['acertos_simples']:>2}/{comp['total_testes']:<8} | "
            f"{comp['taxa_simples']:>6.1f}% | "
            f"{comp['tempo_medio_simples_ms']:>7.3f} ms"
        )
        linhas.append(
            f"{'2. Busca Ranqueada (Pesos+Stopwords)':<36} | "
            f"{relatorio['total_acertos']:>2}/{relatorio['total_testes']:<8} | "
            f"{relatorio['taxa_acerto']:>6.1f}% | "
            f"{relatorio['tempo_medio_ms']:>7.3f} ms"
        )
        linhas.append("-" * 76)
        if comp["divergencias_simples"]:
            linhas.append(
                f"  • Falhas na Busca Simples: {', '.join(comp['divergencias_simples'])} "
                "(ruído por palavras comuns e empates sem peso)."
            )

    if relatorio.get("comparacao_prompts"):
        linhas.append("")
        linhas.append(prompts.formatar_comparacao_testes(relatorio["comparacao_prompts"]))

    linhas.append("=" * 76)
    return "\n".join(linhas)

def salvar_resultados_testes(relatorio, diretorio_saida=None):
    """
    Persiste o relatório completo dos testes em docs/resultados_testes.txt
    e a tabela estruturada em docs/resultados_testes.csv (esperado, obtido,
    acerto/erro e tempo em ms), atendendo à evidência documental do edital.
    """
    raiz_projeto = Path(__file__).resolve().parent.parent
    pasta_docs = Path(diretorio_saida) if diretorio_saida else raiz_projeto / "docs"
    pasta_docs.mkdir(parents=True, exist_ok=True)

    caminho_txt = pasta_docs / "resultados_testes.txt"
    caminho_csv = pasta_docs / "resultados_testes.csv"

    texto_relatorio = formatar_relatorio_avaliacao(relatorio)
    caminho_txt.write_text(texto_relatorio + "\n", encoding="utf-8")

    with caminho_csv.open("w", encoding="utf-8-sig", newline="") as arquivo_csv:
        escritor = csv.writer(arquivo_csv, delimiter=",")
        escritor.writerow([
            "id_teste",
            "categoria",
            "consulta",
            "resposta_esperada",
            "resposta_obtida",
            "status",
            "tempo_ms",
        ])
        for item in relatorio["resultados"]:
            escritor.writerow([
                item["id_teste"],
                item["categoria"],
                item["consulta"],
                item["descricao_esperada"],
                item["descricao_obtida"],
                "ACERTO" if item["acertou"] else "ERRO",
                f"{item['tempo_ms']:.3f}",
            ])

    return caminho_txt, caminho_csv
