import textwrap

LARGURA_TEXTO = 72

# Definição estruturada dos Modelos de Prompt / Instrução de Resposta
# Cada modelo estabelece papel do assistente, regras de conduta, formato de saída e obrigatoriedade de citação de fonte e limites.
MODELOS_PROMPT = {
    "direto": {
        "codigo": "direto",
        "nome": "Modelo 1 — Resposta Direta e Objetiva",
        "papel_assistente": (
            "Assistente digital informativo do IncluiSP focado em respostas rápidas, "
            "curtas e sem rodeios para consulta ágil em dispositivos móveis ou leitores de tela."
        ),
        "regras_instrucao": (
            "1. Responder exclusivamente com base nos dados verificados da base JSON.",
            "2. Apresentar a orientação de forma direta em um único bloco de texto.",
            "3. Citar obrigatoriamente a fonte oficial e a data de verificação.",
            "4. Incluir aviso curto de que o sistema não é canal oficial de governo.",
            "5. Nunca solicitar CPF, RG, endereço ou dados pessoais sensíveis.",
        ),
        "formato_saida": "Bloco compacto: [Tema] -> [Orientação] -> [Fonte/Data] -> [Aviso curto].",
    },
    "didatico": {
        "codigo": "didatico",
        "nome": "Modelo 2 — Guia Estruturado e Acessível (Cadeia de Instrução)",
        "papel_assistente": (
            "Assistente cidadão acessível do IncluiSP, especializado em traduzir direitos, "
            "benefícios e rotas de acessibilidade em etapas claras, inclusivas e seguras."
        ),
        "regras_instrucao": (
            "1. Contextualizar o tema e a pergunta correspondida para confirmar o assunto.",
            "2. Apresentar a orientação em linguagem simples, acessível e estruturada.",
            "3. Destacar a referência verificada e a data de conferência da informação.",
            "4. Explicitar limites do assistente, caráter não oficial e necessidade de confirmação.",
            "5. Sugerir até 3 assuntos relacionados (via grafo) para continuidade da consulta.",
        ),
        "formato_saida": (
            "Saída em 4 blocos: (1) Identificação do Assunto, (2) Orientação Cidadã, "
            "(3) Fonte e Transparência/Limites, (4) Próximos Passos Relacionados."
        ),
    },
}

AVISO_GERAL_NAO_OFICIAL = (
    "Este assistente tem caráter exclusivamente informativo e NÃO substitui canais "
    "oficiais de órgãos públicos (como SPTrans, Metrô, INSS ou Prefeitura). "
    "Não informe dados pessoais sensíveis e confirme requisitos atualizados antes de solicitar serviços."
)


def formatar_paragrafo(texto, recuo_inicial="   ", recuo_seguinte="   ", largura=LARGURA_TEXTO):
    """
    Quebra textos longos respeitando o limite de colunas do terminal,
    evitando que palavras sejam cortadas ao meio na borda da janela.
    """
    return textwrap.fill(
        str(texto).strip(),
        width=largura,
        initial_indent=recuo_inicial,
        subsequent_indent=recuo_seguinte,
        break_long_words=False,
        break_on_hyphens=False,
    )


def validar_entrada_consulta(texto_entrada):
    """
    Aplica lógica booleana para validar a entrada textual do usuário antes da busca.
    Trata entradas vazias, apenas espaços ou textos curtos demais sem significado.
    Retorna uma tupla: (eh_valida: bool, mensagem_erro: str).
    """
    if texto_entrada is None or not isinstance(texto_entrada, str):
        return False, "[ENTRADA INVÁLIDA] Nenhuma pergunta foi recebida. Digite sua dúvida ou escolha uma opção do menu."

    texto_limpo = texto_entrada.strip()

    if len(texto_limpo) == 0:
        return False, "[ENTRADA VAZIA] Você enviou uma consulta em branco. Digite uma palavra-chave ou pergunta (ex.: 'bilhete único')."

    if len(texto_limpo) < 2:
        return False, "[CONSULTA MUITO CURTA] Digite ao menos uma palavra completa para que eu possa buscar na base."

    return True, ""


def _separar_orientacao_e_aviso(texto_orientacao):
    """
    Separa o corpo principal da orientação de eventuais avisos específicos já embutidos
    no JSON (como nos registros 16 a 22), evitando repetição na formatação.
    """
    marcador = "Aviso:"
    if marcador in texto_orientacao:
        partes = texto_orientacao.split(marcador, 1)
        corpo = partes[0].strip()
        aviso_especifico = partes[1].strip()
        return corpo, aviso_especifico
    return texto_orientacao.strip(), ""


def gerar_resposta_estruturada(registro, modelo="didatico", relacionados=None, pontuacao=None):
    """
    Formata a resposta final conforme o modelo de prompt selecionado ('direto' ou 'didatico'),
    garantindo clareza, citação obrigatória da fonte, aviso de limitação e sugestões do grafo.
    """
    if modelo not in MODELOS_PROMPT:
        modelo = "didatico"

    corpo_orientacao, aviso_especifico = _separar_orientacao_e_aviso(registro["orientacao"])
    linhas = []

    if modelo == "direto":
        # Modelo 1: Resposta Direta e Objetiva
        linhas.append("-" * LARGURA_TEXTO)
        linhas.append(f"[{MODELOS_PROMPT['direto']['nome']}]")
        linhas.append(f"Tema: {registro['tema']} | Registro #{registro['id']}")
        linhas.append("")
        linhas.append(
            formatar_paragrafo(
                f"Orientação: {corpo_orientacao}",
                recuo_inicial="",
                recuo_seguinte="",
            )
        )
        if aviso_especifico:
            linhas.append(
                formatar_paragrafo(
                    f"Atenção: {aviso_especifico}",
                    recuo_inicial="",
                    recuo_seguinte="",
                )
            )
        linhas.append("")
        linhas.append(
            formatar_paragrafo(
                f"Fonte: {registro['fonte']} (Verificado em: {registro['data_verificacao']})",
                recuo_inicial="",
                recuo_seguinte="",
            )
        )
        linhas.append(
            formatar_paragrafo(
                "Aviso: Informação orientativa; confirme regras atualizadas nos canais oficiais.",
                recuo_inicial="",
                recuo_seguinte="",
            )
        )
        linhas.append("-" * LARGURA_TEXTO)

    else:
        # Modelo 2: Guia Estruturado e Acessível (Cadeia de Instrução)
        linhas.append("=" * LARGURA_TEXTO)
        linhas.append(f"[{MODELOS_PROMPT['didatico']['nome']}]")
        linhas.append("=" * LARGURA_TEXTO)
        linhas.append(f"1. ASSUNTO IDENTIFICADO (ID #{registro['id']} — {registro['tema']})")
        linhas.append(
            formatar_paragrafo(
                f"Pergunta de referência: {registro['pergunta']}",
                recuo_inicial="   ",
                recuo_seguinte="   ",
            )
        )
        if pontuacao is not None:
            linhas.append(f"   Relevância da correspondência: {pontuacao} pontos")

        linhas.append("\n2. ORIENTAÇÃO CIDADÃ")
        linhas.append(formatar_paragrafo(corpo_orientacao))

        linhas.append("\n3. FONTE VERIFICADA E LIMITES DE RESPONSABILIDADE")
        linhas.append(
            formatar_paragrafo(
                f"Fonte consultada: {registro['fonte']}",
                recuo_inicial="   • ",
                recuo_seguinte="     ",
            )
        )
        linhas.append(f"   • Data de verificação: {registro['data_verificacao']}")
        if aviso_especifico:
            linhas.append(
                formatar_paragrafo(
                    f"Observação importante: {aviso_especifico}",
                    recuo_inicial="   • ",
                    recuo_seguinte="     ",
                )
            )
        linhas.append(
            formatar_paragrafo(
                f"Limite de atendimento: {AVISO_GERAL_NAO_OFICIAL}",
                recuo_inicial="   • ",
                recuo_seguinte="     ",
            )
        )

        if relacionados:
            linhas.append("\n4. ASSUNTOS RELACIONADOS PARA CONTINUAR SUA CONSULTA (GRAFO)")
            for idx, item in enumerate(relacionados, start=1):
                reg_rel = item["registro"]
                motivo = item["motivo"]
                linhas.append(
                    formatar_paragrafo(
                        f"[{idx}] ID #{reg_rel['id']} ({reg_rel['tema']}): {reg_rel['pergunta']}",
                        recuo_inicial="   ",
                        recuo_seguinte="       ",
                    )
                )
                linhas.append(
                    formatar_paragrafo(
                        f"↳ Conexão: {motivo}",
                        recuo_inicial="       ",
                        recuo_seguinte="         ",
                    )
                )

        linhas.append("=" * LARGURA_TEXTO)

    return "\n".join(linhas)


def gerar_resposta_ambigua(consulta, candidatos, limite=3):
    """
    Trata consultas ambíguas (quando dois ou mais registros têm pontuação muito próxima),
    apresentando as alternativas encontradas para que o cidadão escolha com precisão.
    """
    linhas = []
    linhas.append("-" * LARGURA_TEXTO)
    linhas.append("[CONSULTA AMBÍGUA — MÚLTIPLAS CORRESPONDÊNCIAS ENCONTRADAS]")
    linhas.append(
        formatar_paragrafo(
            f"Sua busca por '{consulta}' corresponde a mais de uma orientação na base.",
            recuo_inicial="",
            recuo_seguinte="",
        )
    )
    linhas.append("Para evitar uma resposta imprecisa, escolha uma das opções abaixo:\n")

    for idx, item in enumerate(candidatos[:limite], start=1):
        reg = item["registro"]
        linhas.append(
            formatar_paragrafo(
                f"{idx}. [ID #{reg['id']} | {reg['tema']}] {reg['pergunta']}",
                recuo_inicial="  ",
                recuo_seguinte="     ",
            )
        )

    linhas.append("")
    linhas.append(
        formatar_paragrafo(
            "Dica: Digite o número da opção desejada ou refine sua pergunta com mais detalhes.",
            recuo_inicial="",
            recuo_seguinte="",
        )
    )
    linhas.append("-" * LARGURA_TEXTO)
    return "\n".join(linhas)


def gerar_resposta_sem_correspondencia(consulta, temas_disponiveis, sugestoes_iniciais=None):
    """
    Trata perguntas fora do escopo ou sem correspondência confiável na base.
    Cumpre a regra de transparência: não inventa respostas e oferece caminhos alternativos.
    """
    linhas = []
    linhas.append("-" * LARGURA_TEXTO)
    linhas.append("[SEM CORRESPONDÊNCIA NA BASE DE CONHECIMENTO]")
    linhas.append(
        formatar_paragrafo(
            f"Não encontrei orientações verificadas para '{consulta}' na base atual do IncluiSP.",
            recuo_inicial="",
            recuo_seguinte="",
        )
    )
    linhas.append(
        formatar_paragrafo(
            "Por segurança e responsabilidade, este assistente não inventa instruções nem responde assuntos fora do escopo cadastrado.",
            recuo_inicial="",
            recuo_seguinte="",
        )
    )

    if temas_disponiveis:
        linhas.append("\nTemas disponíveis que você pode explorar:")
        for idx, tema in enumerate(temas_disponiveis, start=1):
            linhas.append(f"  • {idx}. {tema}")

    if sugestoes_iniciais:
        linhas.append("\nExemplos de perguntas que posso responder agora:")
        for reg in sugestoes_iniciais[:3]:
            linhas.append(
                formatar_paragrafo(
                    f"[ID #{reg['id']}] {reg['pergunta']}",
                    recuo_inicial="  - ",
                    recuo_seguinte="    ",
                )
            )

    linhas.append("")
    linhas.append(
        formatar_paragrafo(
            "Canais públicos gerais em São Paulo: Central SP156 (Prefeitura/SPTrans) ou Gov.br.",
            recuo_inicial="",
            recuo_seguinte="",
        )
    )
    linhas.append("-" * LARGURA_TEXTO)
    return "\n".join(linhas)


def comparar_modelos_prompt(registro, relacionados=None):
    """
    Gera uma comparação lado a lado (sequencial) entre o Modelo 1 (Direto) e o Modelo 2 (Didático)
    para uma mesma orientação, facilitando a análise qualitativa no relatório e no terminal.
    """
    bloco_comparacao = [
        "*" * LARGURA_TEXTO,
        "COMPARAÇÃO DE ESTRATÉGIAS DE PROMPT / FORMATAÇÃO DE RESPOSTA",
        "*" * LARGURA_TEXTO,
        gerar_resposta_estruturada(registro, modelo="direto"),
        "",
        gerar_resposta_estruturada(registro, modelo="didatico", relacionados=relacionados),
        "\n[ANÁLISE TÉCNICA DAS ESTRATÉGIAS]",
        formatar_paragrafo(
            "O Modelo 1 (Direto) reduz a carga visual e acelera leituras pontuais.",
            recuo_inicial="• ",
            recuo_seguinte="  ",
        ),
        formatar_paragrafo(
            "O Modelo 2 (Didático) oferece maior clareza, transparência sobre limites e continuidade via grafo de assuntos relacionados, sendo mais indicado para orientação cidadã acessível.",
            recuo_inicial="• ",
            recuo_seguinte="  ",
        ),
        "*" * LARGURA_TEXTO,
    ]
    return "\n".join(bloco_comparacao)
