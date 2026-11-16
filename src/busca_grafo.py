import heapq
import re
import unicodedata

# Conjunto de palavras comuns (stopwords) ignoradas na tokenização para evitar falsos positivos em perguntas fora da base de conhecimento.
STOPWORDS = {
    "a", "as", "o", "os", "um", "uma", "uns", "umas",
    "de", "do", "da", "dos", "das", "em", "no", "na", "nos", "nas",
    "por", "para", "com", "sem", "sob", "sobre", "entre",
    "e", "ou", "mas", "se", "que", "qual", "quais", "quem", "onde", "como",
    "é", "sao", "ser", "esta", "estao", "tem", "tenho", "ter", "posso", "pode",
    "meu", "minha", "me", "ao", "aos", "pelo", "pela", "funciona", "fazer",
}

# Arestas semânticas do Grafo de Conhecimento.
# Cada chave (ID) aponta para uma lista de tuplas (id_relacionado, motivo_conexao), interligando assuntos entre os 3 temas para continuidade da consulta.
ARESTAS_SEMANTICAS = {
    1: [
        (17, "Alternativa porta a porta (Serviço Atende+)"),
        (19, "Direitos em caso de recusa de embarque"),
        (6, "Benefício assistencial complementar (BPC/LOAS)"),
        (13, "Acessibilidade nos ônibus da SPTrans"),
    ],
    2: [
        (9, "Atendimento prioritário em hospitais e serviços"),
        (10, "Direito a acompanhante em cultura e lazer"),
        (20, "Gratuidade para PcD e acompanhante em museus"),
        (6, "Apoio financeiro assistencial (BPC/LOAS)"),
    ],
    3: [
        (18, "O que fazer se o elevador da estação estiver quebrado"),
        (20, "Pinacoteca de SP (ao lado da Estação da Luz)"),
        (12, "Outro eixo acessível integrado (Avenida Paulista)"),
        (1, "Gratuidade no transporte (Bilhete Único Especial)"),
    ],
    4: [
        (7, "Isenção de IPI na compra de veículo novo"),
        (5, "Credencial Defis para vagas exclusivas"),
        (1, "Opção de transporte público gratuito (Bilhete Único)"),
        (6, "Critérios do benefício assistencial BPC/LOAS"),
    ],
    5: [
        (4, "Isenção de IPVA para veículo de PcD"),
        (7, "Isenção de IPI na aquisição de carro zero"),
        (14, "Alternativa de deslocamento (Táxi Acessível)"),
        (15, "Acesso e vagas no Parque Ibirapuera"),
    ],
    6: [
        (16, "Diferença entre BPC/LOAS e auxílio por incapacidade"),
        (1, "Gratuidade no transporte municipal (Bilhete Único)"),
        (2, "Direito a acompanhante na rede pública (SUS)"),
        (9, "Prioridade de atendimento em agências e bancos"),
    ],
    7: [
        (4, "Isenção anual de IPVA em São Paulo"),
        (5, "Credencial de estacionamento Defis"),
        (14, "Serviço de Táxi Acessível em SP"),
        (1, "Bilhete Único Especial SPTrans"),
    ],
    8: [
        (11, "Tempo adicional em provas (ENEM e vestibulares)"),
        (9, "Atendimento prioritário em órgãos públicos"),
        (2, "Direitos previstos no Estatuto da Pessoa com Deficiência"),
        (6, "Regras de renda e benefícios sociais (BPC)"),
    ],
    9: [
        (19, "Como agir diante de constrangimento ou recusa"),
        (2, "Atendimento prioritário e acompanhante no SUS"),
        (10, "Benefícios de acesso em eventos culturais"),
        (1, "Atendimento preferencial nos postos SPTrans"),
    ],
    10: [
        (20, "Museus em SP com gratuidade para PcD e acompanhante"),
        (9, "Atendimento prioritário em bilheterias e filas"),
        (15, "Lazer acessível no Parque Ibirapuera"),
        (2, "Direito a acompanhante garantido pela LBI"),
    ],
    11: [
        (8, "Cotas para PcD em concursos públicos"),
        (9, "Atendimento prioritário em instituições de ensino"),
        (2, "Garantias da Lei Brasileira de Inclusão (LBI)"),
        (6, "Benefícios assistenciais para estudantes PcD"),
    ],
    12: [
        (20, "MASP e centros culturais na Avenida Paulista"),
        (3, "Conexão acessível via Metrô (Estação da Luz)"),
        (18, "Procedimento caso o elevador da estação falhe"),
        (13, "Linhas de ônibus acessíveis na região"),
    ],
    13: [
        (1, "Tarifa gratuita nos ônibus (Bilhete Único Especial)"),
        (17, "Transporte porta a porta (Serviço Atende+)"),
        (19, "Como denunciar recusa de embarque no ônibus"),
        (18, "Acessibilidade e elevadores no Metrô"),
    ],
    14: [
        (17, "Transporte adaptado gratuito (Serviço Atende+)"),
        (5, "Credencial Defis para estacionamento"),
        (21, "Uso de aplicativos de mobilidade (Maps e Uber Assist)"),
        (13, "Frota acessível de ônibus em São Paulo"),
    ],
    15: [
        (20, "Museus acessíveis em SP (incluindo MAM no Ibirapuera)"),
        (12, "Outro espaço urbano adaptado (Avenida Paulista)"),
        (5, "Credencial Defis para acesso de veículo"),
        (22, "Onde buscar abrigo seguro em caso de tempestade"),
    ],
    16: [
        (6, "Requisitos gerais e renda do BPC/LOAS"),
        (1, "Outro benefício social: Bilhete Único Especial"),
        (2, "Direitos de saúde e acompanhante no SUS"),
        (9, "Atendimento prioritário no INSS e bancos"),
    ],
    17: [
        (1, "Bilhete Único Especial para ônibus e metrô"),
        (13, "Ônibus convencionais com elevador (SPTrans)"),
        (14, "Serviço de Táxi Acessível em São Paulo"),
        (18, "Suporte em estações de metrô com elevador inoperante"),
    ],
    18: [
        (3, "Exemplo de estação acessível (Estação da Luz)"),
        (13, "Alternativa por ônibus acessível (SPTrans)"),
        (19, "Canais de denúncia e apoio ao passageiro"),
        (17, "Transporte adaptado porta a porta (Atende+)"),
    ],
    19: [
        (9, "Lei do atendimento prioritário e canais de denúncia"),
        (13, "Regras de embarque acessível nos ônibus"),
        (18, "Apoio da equipe em estações de metrô"),
        (1, "Direitos do portador do Bilhete Único Especial"),
    ],
    20: [
        (10, "Lei da Meia-Entrada em cinemas, shows e teatros"),
        (3, "Acesso via Estação da Luz (Pinacoteca e Língua Portuguesa)"),
        (12, "Acesso via Avenida Paulista (MASP e Japan House)"),
        (15, "Lazer acessível no Parque Ibirapuera"),
    ],
    21: [
        (14, "Táxi Acessível com rampa ou elevador em SP"),
        (12, "Rotas acessíveis na Avenida Paulista"),
        (18, "Como confirmar elevadores no Metrô antes de sair"),
        (17, "Serviço Atende+ da SPTrans"),
    ],
    22: [
        (15, "Cuidados em áreas abertas e parques (Ibirapuera)"),
        (12, "Locais fechados e acessíveis na Avenida Paulista"),
        (18, "Apoio das equipes em estações durante emergências"),
        (9, "Atendimento prioritário em situações de risco"),
    ],
}


def normalizar_texto(texto):
    """
    Padroniza uma string para busca: converte para minúsculas, remove acentos
    via decomposição Unicode (NFD) e limpa pontuações desnecessárias.
    """
    if not texto:
        return ""
    texto_sem_acento = "".join(
        caractere
        for caractere in unicodedata.normalize("NFD", str(texto).lower())
        if unicodedata.category(caractere) != "Mn"
    )
    texto_limpo = re.sub(r"[^a-z0-9\s+]", " ", texto_sem_acento)
    return re.sub(r"\s+", " ", texto_limpo).strip()


def extrair_tokens_relevantes(texto):
    """
    Divide o texto normalizado em tokens relevantes, descartando stopwords
    e palavras de apenas um caractere.
    """
    normalizado = normalizar_texto(texto)
    return [
        palavra
        for palavra in normalizado.split()
        if palavra not in STOPWORDS and len(palavra) > 1
    ]


def construir_hierarquia_temas(base_dados):
    """
    Representa os registros em uma estrutura hierárquica (dicionário de listas):
    Tema Principal -> Lista de Subtemas/Orientações ordenadas por ID.
    """
    hierarquia = {}
    for registro in base_dados:
        tema = registro["tema"]
        if tema not in hierarquia:
            hierarquia[tema] = []
        hierarquia[tema].append(registro)

    for tema in hierarquia:
        hierarquia[tema].sort(key=lambda item: int(item["id"]))

    return hierarquia


def filtrar_por_tema(base_dados, tema_escolhido):
    """
    Retorna todas as orientações pertencentes a um tema selecionado no menu.
    """
    hierarquia = construir_hierarquia_temas(base_dados)
    return hierarquia.get(tema_escolhido, [])


def construir_grafo_conhecimento(base_dados):
    """
    Constrói o grafo completo de relações entre os registros da base.
    Prioridade das conexões:
      1. Campo opcional 'relacionados' definido diretamente no registro JSON;
      2. Arestas semânticas mapeadas em ARESTAS_SEMANTICAS;
      3. Fallback dinâmico por palavras-chave e tema para registros novos.
    """
    mapa_por_id = {int(reg["id"]): reg for reg in base_dados}
    grafo = {}

    for reg_id, registro in mapa_por_id.items():
        vizinhos = []
        ids_adicionados = {reg_id}

        # 1. Lê conexões definidas diretamente no JSON (campo opcional 'relacionados')
        for rel in registro.get("relacionados", []):
            if isinstance(rel, dict) and "id" in rel:
                destino_id = int(rel["id"])
                motivo = rel.get("motivo", "Assunto relacionado cadastrado na base")
            elif isinstance(rel, int):
                destino_id = rel
                motivo = "Assunto relacionado cadastrado na base"
            else:
                continue

            if destino_id in mapa_por_id and destino_id not in ids_adicionados:
                vizinhos.append((destino_id, motivo))
                ids_adicionados.add(destino_id)

        # 2. Adiciona arestas semânticas explícitas que existam na base atual
        for destino_id, motivo in ARESTAS_SEMANTICAS.get(reg_id, []):
            if destino_id in mapa_por_id and destino_id not in ids_adicionados:
                vizinhos.append((destino_id, motivo))
                ids_adicionados.add(destino_id)

        # 3. Fallback dinâmico para garantir ao menos 3 conexões
        if len(vizinhos) < 3:
            kw_origem = {normalizar_texto(k) for k in registro["palavras_chave"]}
            for outro_id, outro_reg in mapa_por_id.items():
                if outro_id in ids_adicionados:
                    continue
                kw_destino = {normalizar_texto(k) for k in outro_reg["palavras_chave"]}
                if kw_origem.intersection(kw_destino):
                    vizinhos.append((outro_id, f"Assunto correlato ({outro_reg['tema']})"))
                    ids_adicionados.add(outro_id)
                elif outro_reg["tema"] == registro["tema"]:
                    vizinhos.append((outro_id, f"Mesmo tema: {outro_reg['tema']}"))
                    ids_adicionados.add(outro_id)

                if len(vizinhos) >= 4:
                    break

        grafo[reg_id] = vizinhos

    return grafo


def obter_relacionados(base_dados, id_registro, limite=3):
    """
    Consulta o grafo de conhecimento e retorna até 'limite' assuntos relacionados
    ao registro atual, incluindo o motivo da conexão para orientar a navegação.
    """
    id_busca = int(id_registro)
    grafo = construir_grafo_conhecimento(base_dados)
    mapa_por_id = {int(reg["id"]): reg for reg in base_dados}

    relacionados = []
    for vizinho_id, motivo in grafo.get(id_busca, []):
        if vizinho_id in mapa_por_id:
            relacionados.append({
                "registro": mapa_por_id[vizinho_id],
                "motivo": motivo,
            })
        if len(relacionados) >= limite:
            break

    return relacionados


def encontrar_caminho_assuntos(base_dados, id_origem, id_destino):
    """
    Algoritmo de Dijkstra no grafo ponderado de conhecimento (Fase 4: Grafos)
    para encontrar a trilha de menor custo semântico entre dois assuntos:
      - Custo 1: assuntos conectados dentro do mesmo tema;
      - Custo 2: transição entre temas distintos.
    """
    origem = int(id_origem)
    destino = int(id_destino)
    grafo = construir_grafo_conhecimento(base_dados)
    mapa_por_id = {int(reg["id"]): reg for reg in base_dados}

    if origem not in mapa_por_id or destino not in mapa_por_id:
        return []

    fila_prioridade = [(0, origem, [origem])]
    menores_custos = {origem: 0}

    while fila_prioridade:
        custo_atual, atual, caminho = heapq.heappop(fila_prioridade)

        if atual == destino:
            return [mapa_por_id[node_id] for node_id in caminho]

        if custo_atual > menores_custos.get(atual, float("inf")):
            continue

        tema_atual = mapa_por_id[atual]["tema"]
        for vizinho_id, _ in grafo.get(atual, []):
            peso_aresta = 1 if mapa_por_id[vizinho_id]["tema"] == tema_atual else 2
            novo_custo = custo_atual + peso_aresta

            if novo_custo < menores_custos.get(vizinho_id, float("inf")):
                menores_custos[vizinho_id] = novo_custo
                heapq.heappush(fila_prioridade, (novo_custo, vizinho_id, caminho + [vizinho_id]))

    return []


def buscar_orientacoes(base_dados, consulta, pontuacao_minima=4):
    """
    Estratégia de Busca Ranqueada por Relevância:
      - +10 pontos (+4 por termo extra) para expressão exata em 'palavras_chave';
      - +4 pontos por token relevante coincidente em 'palavras_chave';
      - +2 pontos por token relevante coincidente no enunciado da 'pergunta';
      - +1 ponto se houver coincidência no 'tema';
      - +1 ponto (máx. 2) por coincidência no texto da 'orientacao'.

    Quando existem várias correspondências, os resultados são ordenados de forma
    decrescente pela pontuação (usando o ID como desempate determinístico).
    """
    consulta_norm = normalizar_texto(consulta)
    tokens_consulta = set(extrair_tokens_relevantes(consulta))

    if not consulta_norm or not tokens_consulta:
        return []

    resultados = []

    for registro in base_dados:
        pontuacao = 0
        termos_encontrados = set()

        # 1. Avaliação das palavras-chave cadastradas (maior peso semântico)
        for kw in registro["palavras_chave"]:
            kw_norm = normalizar_texto(kw)
            if not kw_norm:
                continue

            if re.search(rf"\b{re.escape(kw_norm)}\b", consulta_norm):
                bonus_composto = (len(kw_norm.split()) - 1) * 4
                pontuacao += 10 + bonus_composto
                termos_encontrados.add(kw)
            else:
                tokens_kw = set(extrair_tokens_relevantes(kw_norm))
                coincidencias_kw = tokens_consulta.intersection(tokens_kw)
                if coincidencias_kw:
                    pontuacao += len(coincidencias_kw) * 4
                    termos_encontrados.update(coincidencias_kw)

        # 2. Avaliação dos termos presentes na pergunta de referência
        tokens_pergunta = set(extrair_tokens_relevantes(registro["pergunta"]))
        coincidencias_pergunta = tokens_consulta.intersection(tokens_pergunta)
        if coincidencias_pergunta:
            pontuacao += len(coincidencias_pergunta) * 2
            termos_encontrados.update(coincidencias_pergunta)

        # 3. Avaliação do tema
        tokens_tema = set(extrair_tokens_relevantes(registro["tema"]))
        if tokens_consulta.intersection(tokens_tema):
            pontuacao += 1

        # 4. Avaliação leve no corpo da orientação para desempate
        tokens_orientacao = set(extrair_tokens_relevantes(registro["orientacao"]))
        coincidencias_orientacao = tokens_consulta.intersection(tokens_orientacao)
        if coincidencias_orientacao:
            pontuacao += min(len(coincidencias_orientacao), 2)

        if pontuacao >= pontuacao_minima:
            resultados.append({
                "registro": registro,
                "pontuacao": pontuacao,
                "termos_encontrados": sorted(termos_encontrados),
            })

    resultados.sort(key=lambda item: (-item["pontuacao"], int(item["registro"]["id"])))
    return resultados


def classificar_resultado_busca(resultados, margem_ambiguidade=2):
    """
    Analisa os resultados ranqueados para tratar múltiplas correspondências e ambiguidades:
      - 'sem_correspondencia': nenhum registro atingiu a pontuação mínima;
      - 'ambiguo': os dois primeiros registros têm pontuações muito próximas (diferença <= margem);
      - 'unico': existe um resultado principal claramente mais relevante.
    """
    if not resultados:
        return "sem_correspondencia"

    if len(resultados) >= 2:
        diferenca = resultados[0]["pontuacao"] - resultados[1]["pontuacao"]
        if diferenca <= margem_ambiguidade:
            return "ambiguo"

    return "unico"
