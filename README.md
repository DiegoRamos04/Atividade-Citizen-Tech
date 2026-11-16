# IncluiSP | Citizen Assist AI

Assistente digital em terminal que orienta pessoas com deficiência (PcD) e seus acompanhantes sobre documentos, benefícios, direitos e mobilidade na cidade de São Paulo. Projeto da Global Solution 2026.2 (FIAP), desafio CitizenTech, case Citizen Assist AI.

## 1. Equipe

| Integrante | RM |
|---|---|
| Diego Ramos dos Santos | 570889 |
| Heitor Assis Duenhas | 570472 |
| Pedro Ribeiro Gesini | 569421 |

Repositório: https://github.com/DiegoRamos04/Atividade-Citizen-Tech

---

## 2. Problema, público e temas

### Problema

Quem precisa de uma orientação sobre transporte gratuito, benefícios ou direitos costuma encontrar a informação espalhada em vários sites, com linguagem técnica e sem indicação de fonte ou data. A busca fica lenta e pode levar a interpretações erradas.

### Solução

O IncluiSP recebe uma pergunta ou uma escolha de menu, localiza a orientação em uma base verificada, mostra a resposta com a fonte e a data de verificação e avisa quando não há resposta confiável. O protótipo não usa modelo de linguagem nem API externa: toda resposta vem do arquivo `data/base.json`.

### Público beneficiado

Pessoas com deficiência, acompanhantes, familiares e cuidadores que usam serviços em São Paulo. A maior parte dos registros trata da capital paulista. Alguns têm abrangência nacional (BPC, IPI, ENEM).

### Escopo

| O assistente faz | O assistente não faz |
|---|---|
| Responde com base em 23 orientações verificadas | Não é canal oficial de nenhum órgão público |
| Mostra fonte e data de verificação em toda resposta | Não consulta sites ou sistemas em tempo real |
| Avisa quando não encontra resposta e não inventa instruções | Não monitora elevadores, clima ou bloqueios viários |
| Sugere assuntos relacionados para continuar a consulta | Não pede nem guarda dados pessoais |

### Temas abordados

| Tema | Subtema | Registros (IDs) |
|---|---|---|
| Documentação e Benefícios | Assistência Social e Identificação | 1, 6, 16, 23 |
| Documentação e Benefícios | Isenções e Credenciais Veiculares | 4, 5, 7 |
| Direitos em Serviços Públicos | Atendimento e Educação | 2, 8, 9, 11 |
| Direitos em Serviços Públicos | Cultura, Lazer e Emergências | 10, 19, 20, 22 |
| Mobilidade e Rotas | Transporte Público Adaptado | 13, 14, 17, 18 |
| Mobilidade e Rotas | Vias, Parques e Rotas Digitais | 3, 12, 15, 21 |

Total: 23 orientações, 3 temas e 6 subtemas.

### Conteúdos aplicados

| Fase | Conteúdo | Onde aparece |
|---|---|---|
| 1 a 3 | Python, lógica booleana, listas, dicionários | Validações, menus e condicionais em todo o código |
| 4 | Listas, tuplas, dicionários, leitura e organização de dados, grafos, Dijkstra | `base_dados.py`, hierarquia e grafo de assuntos em `busca_grafo.py` |
| 5 | Arquivos JSON, instruções e saídas estruturadas, lógica booleana | `data/base.json`, modelos de prompt em `prompts.py` |
| 6 | Métricas em Python, assistente virtual, busca e comparação de algoritmos | `avaliacao.py`, comparação entre busca simples e busca ranqueada |

---

## 3. Base de conhecimento, estruturas e busca

### 3.1 Arquivo e campos

A base fica em `data/base.json`, na chave `base_conhecimento`. Cada registro tem os campos abaixo.

| Campo | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `id` | inteiro positivo, único | Sim | Identificador do registro |
| `tema` | texto | Sim | Tema principal |
| `subtema` | texto | Não (padrão "Geral") | Segundo nível da hierarquia |
| `pergunta` | texto | Sim | Pergunta de referência |
| `palavras_chave` | lista não vazia | Sim | Termos usados na busca |
| `orientacao` | texto | Sim | Orientação resumida |
| `fonte` | texto | Sim | Referência consultada (lei, órgão ou endereço) |
| `data_verificacao` | texto (AAAA-MM-DD) | Sim | Data em que a informação foi conferida |
| `relacionados` | lista de `{id, motivo}` | Não | Conexões do grafo definidas no próprio registro |

Exemplo (registro 23):

```json
{
  "id": 23,
  "tema": "Documentação e Benefícios",
  "subtema": "Assistência Social e Identificação",
  "pergunta": "Como solicitar a Carteira de Identificação da Pessoa com Transtorno do Espectro Autista (CiPTEA)?",
  "palavras_chave": ["ciptea", "autismo", "tea", "carteira autista", "identificacao"],
  "orientacao": "A CiPTEA é gratuita e pode ser solicitada online pelo portal da Secretaria dos Direitos da Pessoa com Deficiência de SP, apresentando laudo médico com CID e documentos pessoais.",
  "fonte": "Portal CiPTEA SP (ciptea.sp.gov.br)",
  "data_verificacao": "2026-11-16",
  "relacionados": [
    {"id": 2, "motivo": "Direito a acompanhante no SUS"},
    {"id": 9, "motivo": "Prioridade de atendimento em filas"}
  ]
}
```

### 3.2 Validação e tratamento de erros na leitura

A leitura é feita por `base_dados.carregar_base_conhecimento()`.

- Arquivo ausente, vazio, com JSON inválido ou sem a chave `base_conhecimento`: o sistema mostra uma mensagem de erro e encerra com aviso de falha.
- Registro sem campo obrigatório, com campo vazio, `palavras_chave` vazia, `id` que não seja inteiro positivo ou `id` duplicado: o registro é ignorado e o sistema informa a posição dele no arquivo.
- Os temas disponíveis são extraídos da base ao iniciar e exibidos na tela inicial.

### 3.3 Como acrescentar ou corrigir registros

Sem alterar o código, de duas formas:

1. Pela opção 8 do menu, que pede os campos, valida, atribui o próximo ID e grava em `data/base.json`.
2. Editando `data/base.json` diretamente.

Registros novos entram na busca (o índice é refeito) e no grafo. Se o registro não tiver conexões definidas, o sistema liga a outros registros com palavras-chave em comum ou do mesmo tema.

### 3.4 Fontes consultadas

Todas as orientações foram conferidas nas fontes abaixo. As datas de verificação foram 13/11/2026 (IDs 1 a 15), 14/11/2026 (IDs 16 a 22) e 16/11/2026 (ID 23).

| ID | Assunto | Fonte |
|---|---|---|
| 1 | Bilhete Único Especial | https://sptrans.com.br/deficiente |
| 2 | Acompanhante em consultas (SUS) | Lei nº 13.146/2015 (Arts. 18 e 22) e Portaria MS nº 1.820/2009 |
| 3 | Acessibilidade da Estação da Luz | https://www.metro.sp.gov.br/sua-viagem/acessibilidade |
| 4 | Isenção de IPVA | SIVEI / Secretaria da Fazenda SP (portal.fazenda.sp.gov.br/servicos/ipva) |
| 5 | Credencial Defis (vaga exclusiva) | Portal SP156 - Cartão Defis (sp156.prefeitura.sp.gov.br) e Res. CONTRAN 965/2022 |
| 6 | BPC/LOAS | Lei nº 8.742/1993 |
| 7 | Isenção de IPI na compra de carro | SISEN / Receita Federal (gov.br/receitafederal/pt-br/assuntos/isencoes/ipi) |
| 8 | Cotas em concursos públicos | Lei nº 8.112/1990, Decreto nº 9.508/2018 e LC Estadual SP nº 683/1992 |
| 9 | Atendimento prioritário | Lei nº 13.146/2015 |
| 10 | Meia-entrada | Lei nº 12.933/2013 |
| 11 | Tempo adicional no ENEM | Edital do ENEM / Inep |
| 12 | Avenida Paulista | SMPED / Prefeitura de SP (prefeitura.sp.gov.br/cidade/secretarias/pessoa_com_deficiencia) |
| 13 | Ônibus com elevador | SPTrans (sptrans.com.br/acessibilidade) |
| 14 | Táxi Acessível | DTP / Prefeitura de SP (prefeitura.sp.gov.br/cidade/secretarias/transportes) |
| 15 | Parque Ibirapuera | Urbia / Parque Ibirapuera (parqueibirapuera.org/planeje-sua-visita) |
| 16 | BPC x auxílio por incapacidade | https://www.gov.br/pt-br/servicos/solicitar-beneficio-assistencial-a-pessoa-com-deficiencia |
| 17 | Serviço Atende+ | https://www.sptrans.com.br/atende |
| 18 | Elevador do metrô quebrado | https://www.metro.sp.gov.br/pt_BR/sua-viagem/acessibilidade/ |
| 19 | Recusa de embarque | Lei 13.146/2015 e https://www.sptrans.com.br/fale-conosco/contatos/ |
| 20 | Museus e gratuidade | Pinacoteca, MASP, Museu do Futebol e Catavento (sites oficiais) |
| 21 | Google Maps e Uber Assist | support.google.com/accessibility/answer/6396990 e uber.com/br/pt-br/ride/assist |
| 22 | Abrigo em tempestades | https://cge.prefeitura.sp.gov.br/v3/dicas.jsp |
| 23 | CiPTEA | Portal CiPTEA SP (ciptea.sp.gov.br) |

### 3.5 Estruturas de dados

| Estrutura | Uso | Arquivo |
|---|---|---|
| Lista de dicionários | Registros carregados do JSON | `base_dados.py` |
| Tupla | Campos obrigatórios e arestas `(id, motivo)` | `base_dados.py`, `busca_grafo.py` |
| Conjunto (`set`) | Tokens da consulta, stopwords e IDs candidatos | `busca_grafo.py` |
| Dicionário de sinônimos | Expansão de termos (ex.: "pcd" e "deficiente") | `busca_grafo.py` |
| Índice invertido (`token -> set de IDs`) | Seleciona candidatos antes de pontuar | `busca_grafo.py` |
| Dicionário aninhado | Hierarquia tema -> subtema -> orientações | `busca_grafo.py` |
| Lista de adjacência | Grafo de assuntos relacionados | `busca_grafo.py` |
| Fila de prioridade (`heapq`) | Algoritmo de Dijkstra | `busca_grafo.py` |

### 3.6 Hierarquia e grafo

**Hierarquia (3 níveis).** Tema -> subtema -> orientação. Serve para a navegação por menu (opção 2) e representa a relação "pertence a". O subtema vem do campo `subtema` do JSON.

**Grafo de assuntos.** Cada orientação é um nó. As arestas ligam assuntos complementares, alternativos ou o próximo passo da consulta (por exemplo, Bilhete Único Especial -> Serviço Atende+ -> recusa de embarque). O grafo é direcionado e cada nó tem de 3 a 4 vizinhos. As conexões vêm de três fontes, em ordem de prioridade:

1. Campo `relacionados` do próprio registro no JSON.
2. Dicionário `ARESTAS_SEMANTICAS` em `busca_grafo.py` (registros 1 a 22).
3. Preenchimento automático por palavras-chave em comum ou mesmo tema, quando o registro tem menos de 3 vizinhos.

Depois de cada resposta, o sistema mostra 3 assuntos relacionados com o motivo da conexão, e o usuário pode seguir por qualquer um deles.

**Menor caminho (Dijkstra).** A opção 6 usa o algoritmo de Dijkstra para achar a trilha mais curta entre duas orientações. O custo da aresta é 1 quando os assuntos são do mesmo tema e 2 quando mudam de tema.

### 3.7 Estratégia de busca

A busca (`buscar_orientacoes`) é ranqueada por pontuação e funciona assim:

1. **Normalização:** minúsculas, remoção de acentos e de pontuação.
2. **Tokenização:** descarte de stopwords (como "como", "para", "de") e de palavras de uma letra.
3. **Expansão:** radical leve em português (plurais) e sinônimos cadastrados.
4. **Candidatos:** consulta ao índice invertido, que reúne os registros com ao menos um termo em comum.
5. **Pontuação** dos candidatos:

| Critério | Pontos |
|---|---|
| Expressão exata de uma palavra-chave na consulta | +10 (+4 por palavra extra em expressões compostas) |
| Termo da consulta igual a termo de palavra-chave | +4 por termo |
| Termo coincidente com palavra-chave via radical ou sinônimo | +3 por termo |
| Termo presente na pergunta de referência | +2 por termo |
| Termo presente no tema | +1 |
| Termo presente no texto da orientação | +1 por termo, máximo 2 |

Só entram no resultado os registros com pelo menos 4 pontos.

### 3.8 Comportamento com várias correspondências

Os resultados são ordenados por pontuação, com o ID menor como desempate. Depois, `classificar_resultado_busca` decide o que fazer:

| Classificação | Regra | Resposta do sistema |
|---|---|---|
| Sem correspondência | Nenhum registro chegou a 4 pontos | Aviso de limitação e alternativas |
| Ambíguo | Diferença de até 2 pontos entre o 1º e o 2º | Lista até 3 candidatos para o usuário escolher |
| Único | Diferença maior que 2 pontos | Mostra a orientação do 1º colocado |

### 3.9 Busca de referência (baseline)

`buscar_simples_palavra_chave` percorre todos os registros e retorna os que têm qualquer termo da consulta nas palavras-chave ou na pergunta, sem stopwords, pesos ou sinônimos. Um resultado é "único"; dois ou mais são "ambíguo". Ela é usada só na avaliação, para comparar com a busca ranqueada (seção 5.2).

---

## 4. Regras de resposta, modelos de prompt e limitações

### 4.1 Fluxo de consulta

1. Valida a entrada (vazia ou com menos de 2 caracteres).
2. Busca e classifica o resultado (único, ambíguo ou sem correspondência).
3. Formata a resposta conforme o modelo de prompt ativo, com fonte e data.
4. Se o registro tem um "Aviso:" próprio (IDs 16 a 22), ele é exibido separado, em destaque.
5. Oferece 3 assuntos relacionados para continuar a consulta.

O código usa condicionais e operadores lógicos nessas decisões. Um exemplo é o critério de acerto dos testes: `comportamento_obtido == "unico" and id_obtido == id_esperado`.

### 4.2 Modelos de prompt

O protótipo não usa modelo de linguagem. Por isso cada modelo é uma especificação (papel, regras e formato) implementada em Python. Os textos completos estão em `MODELOS_PROMPT` (`src/prompts.py`) e podem ser vistos na opção 4 do menu.

| | Modelo 1 — Direto | Modelo 2 — Didático (padrão) |
|---|---|---|
| **Papel** | Assistente informativo para respostas rápidas e curtas | Assistente acessível que traduz direitos, benefícios e rotas em etapas claras |
| **Regras** | Responder só com a base JSON; orientação em um bloco; citar fonte e data; incluir aviso curto de que não é canal oficial; nunca pedir dados pessoais | Confirmar o assunto identificado; linguagem simples e estruturada; destacar fonte e data; explicitar limites, caráter não oficial e necessidade de confirmação; sugerir até 3 assuntos relacionados |
| **Formato** | Tema, orientação, atenção (se houver), fonte e data, aviso | 4 blocos: (1) assunto identificado, (2) orientação cidadã, (3) fonte e limites, (4) assuntos relacionados |

### 4.3 Comparação dos modelos

A comparação é feita nas 13 consultas de teste que têm resposta esperada (T01 a T10 e T16 a T18). Os critérios medem a presença de cada elemento na resposta. É possível ver o resultado na opção 5 do menu ou na opção 7.

| Critério | Modelo 1 (Direto) | Modelo 2 (Didático) |
|---|---|---|
| Cita a fonte | 100% | 100% |
| Cita a data de verificação | 100% | 100% |
| Exibe aviso de limitação | 100% | 100% |
| Sugere assuntos relacionados | 0% | 100% |
| Tamanho médio da resposta | 13.5 linhas | 34.2 linhas |

**Conclusão.** Os dois modelos são consistentes, porque seguem sempre o mesmo formato. O Didático foi adotado como padrão por separar identificação do assunto, orientação, fonte e limites e por incluir a continuidade da consulta. O custo é o texto mais longo, e um participante do teste de usabilidade comentou o excesso de texto. Por isso o Direto continua disponível na opção 4. Os critérios medem a presença dos elementos, não o quanto o leitor entende a resposta.

### 4.4 Tratamento de limitações

| Situação | Comportamento |
|---|---|
| Entrada vazia | Mensagem `[ENTRADA VAZIA]`, sem busca |
| Entrada com 1 caractere | Mensagem `[CONSULTA MUITO CURTA]`, sem busca |
| Opção de menu inexistente | `[ERRO] Opção inexistente. Digite um número de 0 a 8.` |
| ID inexistente ou não numérico | Mensagem de erro e retorno ao menu |
| Consulta ambígua | Lista até 3 candidatos e pede a escolha de um número |
| Sem resposta na base | Informa que não há orientação verificada, não inventa instruções, mostra os temas disponíveis e 3 exemplos de perguntas |
| Base ausente, vazia ou inválida | Mensagem de erro e encerramento do sistema |
| Registro inválido ou duplicado | Registro ignorado, com aviso |
| Ctrl+C | Volta ao menu ou encerra com mensagem, sem erro na tela |

---

## 5. Testes, indicadores e interpretação

Foram feitos dois tipos de avaliação: uma bateria automatizada de 18 perguntas de teste (seções 5.1 e 5.2) e um teste de facilidade de uso com 3 participantes (seção 5.3).

### 5.1 Plano de testes automatizados

A bateria está em `src/avaliacao.py` e roda pela opção 7 do menu. Ela tem 18 casos: 5 perguntas diretas, 5 reformulações em linguagem cotidiana, 5 situações de limitação (entrada vazia, 2 ambiguidades e 2 consultas fora do escopo) e 3 casos de estresse (erro de digitação, gíria e frase longa).

**Critério de acerto.** O comportamento obtido deve ser igual ao esperado. Nas respostas únicas, o ID retornado também deve ser o esperado.

**Tempo de consulta.** Medido com `time.perf_counter()` em milissegundos, incluindo validação, busca e classificação.

**Registro dos resultados.** A opção 7 grava `docs/resultados_testes.txt` e `docs/resultados_testes.csv`, com as colunas: `id_teste`, `categoria`, `consulta`, `resposta_esperada`, `resposta_obtida`, `status` e `tempo_ms`.

| ID | Categoria | Consulta | Esperado | Resultado |
|---|---|---|---|---|
| T01 | Pergunta direta | Como solicitar o Bilhete Único Especial para Pessoas com Deficiência? | ID 1 | Acerto |
| T02 | Pergunta direta | A Estação da Luz tem elevador para cadeirante? | ID 3 | Acerto |
| T03 | Pergunta direta | Como pedir isenção de IPVA em São Paulo? | ID 4 | Acerto |
| T04 | Pergunta direta | Tenho direito a acompanhante em consulta pelo SUS? | ID 2 | Acerto |
| T05 | Pergunta direta | Qual o percentual de cotas para PCD em concursos públicos? | ID 8 | Acerto |
| T06 | Reformulação | Quero usar aquela van adaptada porta a porta da SPTrans | ID 17 | Acerto |
| T07 | Reformulação | Cheguei na estação de metrô e o elevador está quebrado | ID 18 | Acerto |
| T08 | Reformulação | O motorista do ônibus recusou meu embarque e fui constrangido | ID 19 | Acerto |
| T09 | Reformulação | Quais museus em SP dão gratuidade para pessoa com deficiência e acompanhante? | ID 20 | Acerto |
| T10 | Reformulação | Vou fazer o ENEM e preciso de tempo extra na prova | ID 11 | Acerto |
| T11 | Limitação (entrada vazia) | (vazio) | Entrada inválida | Acerto |
| T12 | Limitação (ambiguidade) | bpc | Ambíguo (IDs 6 e 16) | Acerto |
| T13 | Limitação (ambiguidade) | elevador | Ambíguo (vários IDs) | Acerto |
| T14 | Limitação (fora do escopo) | Como tirar passaporte na Polícia Federal? | Sem correspondência | Acerto |
| T15 | Limitação (fora do escopo) | Como renovar a CNH vencida no Poupatempo? | Sem correspondência | Acerto |
| T16 | Estresse (erro de digitação) | Como pedir isensao de ipva? | ID 4 | Acerto |
| T17 | Estresse (gíria) | Onde consigo passe livre de busao em SP? | ID 1 | Acerto |
| T18 | Estresse (frase longa) | Oi bom dia [...] aquela carteirinha para estacionar na vaga azul de deficiente | ID 5 | Erro |

A frase completa do T18 está em `src/avaliacao.py`.

### 5.2 Indicadores e interpretação

| Indicador | Resultado |
|---|---|
| Total de testes | 18 |
| Respostas corretas | 17 |
| Falhas | 1 | 
| Taxa de acerto geral | 94.4% |
| Tempo médio de consulta | 2.944 ms |
| Tempo mínimo / máximo | 0,001 ms / 17.610 ms |

**Comparação de algoritmos de busca** (mesmos 18 casos):

| Algoritmo | Acertos | Taxa | Tempo médio |
|---|---|---|---|
| Busca simples por palavra-chave | 3/18 | 16.7% | 0.842 ms |
| Busca ranqueada (pesos, stopwords, sinônimos, índice) | 17/18 | 94.4% | 2.944 ms |

**Interpretação.**
- Os tempos ficam na ordem de milissegundos, porque a base é pequena e roda localmente. O tempo de consulta não limita o uso.
- A busca simples não descarta palavras comuns e não pontua por campo. Palavras como "como" casam com muitas perguntas e geram empates, que ela trata como ambiguidade. Falhas da busca simples: T01 (ambiguo), T02 (ambiguo), T03 (ambiguo), T04 (ambiguo), T05 (ambiguo), T06 (ambiguo), T07 (ambiguo), T08 (ambiguo), T09 (ambiguo), T10 (ambiguo), T14 (ambiguo), T15 (ambiguo), T16 (ambiguo), T17 (ambiguo), T18 (ambiguo) (ruído por palavras comuns e empates sem peso).
- A taxa de acerto vale para estes 18 casos, escritos pela própria equipe. Ela não mede o desempenho em perguntas de qualquer pessoa.
- O T16 passa porque a palavra-chave "ipva" foi digitada corretamente. A busca não corrige "isensao".

### 5.3 Teste de facilidade de uso

**Método.** Aplicamos o teste com 3 participantes (P1 a P3), sem registrar nome ou outros dados pessoais. P1 e P2 são estudantes de TI (nenhum integrante da equipe) e P3 não tem experiência com TI nem com terminal. Cada um recebeu 6 tarefas por escrito e usou o sistema (`python src/sistema.py`) sem explicação prévia. Cronometramos o tempo total de cada sessão e anotamos erros e dificuldades. Quando o participante não avançava, recebia ajuda e a tarefa era classificada como "com ajuda". Ao final, os participantes responderam a uma avaliação rápida de satisfação (escala de 1 a 5).

**Resultados por tarefa** (S = concluiu sozinho, A = concluiu com ajuda)

| Tarefa | P1 | P2 | P3 |
|---|---|---|---|
| 1. Quantidade de temas | S | S | S |
| 2. Busca do Bilhete Único Especial | S | S | S |
| 3. IPVA pelo menu de temas | S | S | S (hesitou, achou a opção sozinho) |
| 4. "bpc" e ambiguidade | S | S | A |
| 5. Pergunta fora da base (passaporte) | S | S | A |
| 6. Continuar por assunto relacionado | S (1 erro, concluiu em seguida) | A | S |
| **Tempo total da sessão** | 4 min | 5 min 30 s | 7 min 40 s |

**Satisfação (escala de 1 a 5)**

| Critério avaliado | P1 | P2 | P3 | Média |
|---|---|---|---|---|
| Linguagem clara | 5 | 4 | 4 | 4,3 |
| Facilidade de navegação | 5 | 5 | 4 | 4,7 |
| Clareza das fontes e avisos | 4 | 4 | 4 | 4,0 |

**Indicadores**

| Indicador | Cálculo | Resultado |
|---|---|---|
| Tarefas concluídas | 18 de 18 | 100% |
| Conclusão sem ajuda | 15 de 18 | 83,3% |
| Tarefas com dificuldade ou erro | 5 de 18 | 27,8% |
| Tempo médio por sessão | (240 + 330 + 460) s ÷ 3 | 343 s (5 min 43 s) |
| Tempo médio por tarefa (estimado) | 1.030 s ÷ 18 | 57 s |

**Dificuldades observadas**
- P1, tarefa 6: digitou uma pergunta que não está na base e cometeu um erro inicial, mas seguiu para um assunto relacionado e concluiu sozinho.
- P2, tarefa 6: precisou de ajuda para continuar a consulta por um assunto relacionado.
- P3, tarefa 3: demorou alguns segundos para localizar a opção correta do menu e concluiu sem ajuda.
- P3, tarefa 4: após digitar "bpc", precisou de ajuda para chegar à orientação sobre BPC e auxílio por incapacidade.
- P3, tarefa 5: procurou a pergunta em outra opção do menu por ter feito algo parecido na tarefa 2. Precisou de ajuda.
- P1 comentou que as respostas têm muito texto para o tempo de leitura.

**Interpretação.** Todas as tarefas foram concluídas, e 83,3% delas sem ajuda. As dificuldades se concentraram em três pontos: continuar a consulta por assuntos relacionados (tarefa 6, duas ocorrências), a tela de ambiguidade (tarefa 4) e a escolha da opção do menu para perguntas em texto (tarefas 3 e 5). P3, sem experiência com terminal, concentrou os erros e foi o mais lento (7 min 40 s, contra 5 min 30 s de P2 e 4 min de P1). Isso sugere que a interface de texto pesa mais para quem não está acostumado. Na satisfação, a navegação teve média 4,7/5, a clareza da linguagem 4,3/5 e as fontes e avisos 4,0/5. Pelo código, o Modelo Didático mostra quatro blocos por resposta, e a lista de assuntos relacionados aparece duas vezes na mesma tela (no bloco 4 e no menu de continuidade). Isso aumenta o texto e pode ter contribuído para as dificuldades na tarefa 6.

### 5.4 Melhorias possíveis

1. **Reduzir o texto de cada resposta:** eliminar a repetição da lista de relacionados e colocar o aviso de limitação em uma linha, deixando a orientação e a fonte em destaque.
2. **Evitar o beco sem saída quando a pergunta não está na base:** além do aviso, mostrar os temas com opção de escolha e os assuntos mais próximos da consulta, em vez de 3 exemplos fixos.
3. **Indicar no menu principal qual opção serve para cada tipo de tarefa**, com um exemplo ao lado (por exemplo, "1. Fazer uma pergunta, como 'elevador quebrado'").
4. **Tolerar erros de digitação** na busca, com comparação aproximada de palavras.

### 5.5 Limitações da avaliação

- Os 18 casos automatizados foram escritos pela equipe, e o acerto é medido pelo ID esperado. Isso não mede a qualidade do texto da resposta.
- A base tem 23 registros. Uma base maior pode gerar mais ambiguidades e mudar os resultados.
- A busca não corrige erros de digitação (ver T16).
- No teste de usabilidade, a amostra é de 3 pessoas escolhidas por conveniência e não permite generalizar. Dois participantes são estudantes de TI, o que pode favorecer o desempenho em terminal em comparação com o público geral.
- Registramos o tempo total de cada sessão, e não o de cada tarefa. O tempo foi medido à mão e as tarefas foram definidas pela própria equipe.
- O teste não incluiu pessoas com deficiência, que fazem parte do público do projeto, e não foi feito com leitor de tela.
- A interface em terminal pode ter influenciado o desempenho de quem não tem familiaridade com ela (caso de P3).

---

## 6. Como executar

**Requisitos:** Python 3.8 ou superior. Usa apenas a biblioteca padrão, sem instalar pacotes.

```bash
git clone https://github.com/DiegoRamos04/Atividade-Citizen-Tech.git
cd Atividade-Citizen-Tech
python src/sistema.py
```

Em alguns sistemas o comando é `python3`. Os caminhos dos arquivos são resolvidos a partir da raiz do projeto, então o sistema pode ser iniciado de qualquer pasta.

### Menu principal

| Opção | Função |
|---|---|
| 1 | Fazer uma pergunta ou buscar por palavras-chave |
| 2 | Navegar por temas e subtemas |
| 3 | Consultar uma orientação diretamente pelo ID |
| 4 | Alternar o formato das respostas (Didático ou Direto) |
| 5 | Comparar os 2 modelos de prompt em uma orientação |
| 6 | Explorar a conexão entre dois assuntos no grafo (Dijkstra) |
| 7 | Executar a bateria de 18 testes, gerar os indicadores e salvar em `docs/` |
| 8 | Gerenciar a base: adicionar ou corrigir orientações |
| 0 | Sair |

### Estrutura do repositório

```
.
├── README.md
├── data/
│   └── base.json                 # base de conhecimento (23 orientações)
├── docs/
│   ├── relatorio.pdf             # relatório técnico
│   ├── link_video.txt            # link do vídeo no YouTube
│   ├── uso_ia.md                 # uso de IA e validação crítica
│   ├── resultados_testes.csv     # registro dos testes (gerado pela opção 7)
│   └── resultados_testes.txt     # relatório dos testes (gerado pela opção 7)
├── incluisp/                     # versão web complementar (opcional)
└── src/
    ├── sistema.py                # menu, fluxos de consulta e navegação
    ├── base_dados.py             # leitura, validação e manutenção da base
    ├── busca_grafo.py            # busca, hierarquia, grafo e Dijkstra
    ├── prompts.py                # modelos de prompt e mensagens
    └── avaliacao.py              # testes, indicadores e comparações
```

---

## 7. Exemplos de perguntas e respostas

| Entrada | Comportamento | Registro | Fonte exibida |
|---|---|---|---|
| Como solicitar o Bilhete Único Especial para Pessoas com Deficiência? | Resposta única | ID 1 | https://sptrans.com.br/deficiente |
| Como pedir isenção de IPVA em São Paulo? | Resposta única | ID 4 | SIVEI / Secretaria da Fazenda SP |
| Cheguei na estação de metrô e o elevador está quebrado | Resposta única | ID 18 | Metrô de São Paulo - Canais de Atendimento e Acessibilidade |
| bpc | Ambígua: pede a escolha entre os registros | IDs 6 e 16 | (depende da escolha) |
| elevador | Ambígua: pede a escolha entre os registros | IDs 13, 18 e 3 | (depende da escolha) |
| Como tirar passaporte na Polícia Federal? | Sem correspondência: informa o limite e sugere temas | nenhum | nenhuma |

**Exemplo de saída** (Modelo Direto, para a pergunta "Como pedir isenção de IPVA em São Paulo?"). Em seguida, o sistema mostra o tempo da consulta e os 3 assuntos relacionados.

```
[Modelo 1 — Resposta Direta e Objetiva]
Tema: Documentação e Benefícios | Registro #4

Orientação: Pessoas com deficiência física, visual, mental ou autistas
têm direito à isenção do IPVA para um veículo em seu nome. Em São Paulo,
o pedido deve ser feito pelo sistema SIVEI da Secretaria da Fazenda,
apresentando laudo médico pericial emitido por clínica credenciada ao
Detran.

Fonte: SIVEI / Secretaria da Fazenda SP
(portal.fazenda.sp.gov.br/servicos/ipva) (Verificado em: 2026-11-13)
Aviso: Este assistente NÃO é canal oficial de governo; confirme regras
atualizadas nos órgãos públicos.
```

**Entradas inválidas**

| Entrada | Mensagem |
|---|---|
| Consulta em branco | `[ENTRADA VAZIA] Você enviou uma consulta em branco. Digite uma palavra-chave ou pergunta (ex.: 'bilhete único').` |
| Apenas 1 caractere | `[CONSULTA MUITO CURTA] Digite ao menos uma palavra completa para que eu possa buscar na base.` |
| Opção 9 no menu | `[ERRO] Opção inexistente. Digite um número de 0 a 8.` |
| ID 99 na opção 3 | `[ERRO] Nenhuma orientação encontrada com ID #99.` |

---

## 8. Cuidados: clareza, acessibilidade, privacidade e informação não oficial

**Clareza.** As orientações são resumidas em linguagem simples. Toda resposta mostra fonte e data de verificação. Quando a orientação exige confirmação (IDs 16 a 22), o aviso específico aparece em destaque.

**Acessibilidade.** A saída é só texto, sem cores nem imagens, com linhas de até 72 colunas e sem palavras cortadas. Os menus são numerados e o formato da resposta pode ser trocado para uma versão mais curta (opção 4). Não testamos o sistema com leitor de tela.

**Privacidade.** O sistema não pede nem guarda dados pessoais. As consultas digitadas não são salvas. Os únicos arquivos gravados são `data/base.json` (pela opção 8) e os resultados dos testes em `docs/`. A tela inicial pede ao usuário que não informe dados pessoais.

**Informação não oficial.** O IncluiSP é um protótipo acadêmico. Não representa SPTrans, Metrô, INSS, Prefeitura ou qualquer outro órgão e não promete integração com eles. A tela inicial e as respostas avisam que o assistente não substitui os canais oficiais e que as regras devem ser confirmadas. Registros que dependem de situação em tempo real (elevadores, chuva) informam que o assistente não monitora essas condições.

**Uso de IA.** O protótipo não usa modelo de IA: as respostas vêm só da base verificada. As ferramentas de IA usadas no desenvolvimento, os prompts testados e a validação crítica das respostas estão em [`docs/uso_ia.md`](docs/uso_ia.md).

---

## 9. Vídeo de apresentação

Link (YouTube, "Não Listado"): [PREENCHER]

O mesmo endereço está em `docs/link_video.txt`.

---

## 10. Conclusões, limitações e possibilidades de melhoria

### Conclusões

O assistente cobre o fluxo pedido no edital: recebe a pergunta ou a escolha de menu, localiza a orientação, mostra resposta, fonte e data e informa o limite quando não há base. A base tem 23 orientações em 3 temas e 6 subtemas, com validação na leitura e manutenção pelo menu. A busca ranqueada com índice invertido foi comparada com uma busca simples, e os dois modelos de prompt foram comparados nas mesmas perguntas de teste. O teste com 3 pessoas apontou onde o fluxo precisa melhorar: navegação por assuntos relacionados, tela de ambiguidade e quantidade de texto.

### Limitações

- A base é pequena e concentrada em São Paulo, e as orientações podem mudar depois da data de verificação.
- Os sinônimos e as conexões do grafo (`ARESTAS_SEMANTICAS`) são cadastrados à mão. O grafo é direcionado: registros novos só são alcançados pela navegação se algum registro apontar para eles.
- A busca não corrige erros de digitação.
- O assistente não consulta fontes em tempo real.
- A interface em terminal exige familiaridade que nem todo usuário tem.
- A avaliação tem as limitações descritas na seção 5.5.

### Possibilidades de melhoria

- Aplicar as melhorias da seção 5.4.
- Ampliar a base e as perguntas de teste, com a participação de pessoas com deficiência.
- Gerar as conexões do grafo a partir das palavras-chave, em vez de listá-las no código.
- Criar um processo de revisão periódica das fontes e das datas de verificação.
- Oferecer interface web ou chatbot, mantendo a base única em `data/base.json`.
