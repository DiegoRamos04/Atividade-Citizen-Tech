# Uso de Inteligência Artificial e Validação Crítica

## 1. Delimitação de Arquitetura: Tempo de Desenvolvimento vs. Tempo de Execução

Antes de detalhar as ferramentas empregadas, cabe uma distinção técnica importante sobre a arquitetura do sistema:

- **Em tempo de execução (protótipo em Python):** O assistente (`src/sistema.py`) não utiliza modelos de linguagem (LLMs) nem chamadas a APIs externas de IA. Toda resposta entregue ao cidadão é recuperada de forma determinística a partir do arquivo local `data/base.json`, utilizando normalização textual, índice invertido, pontuação ponderada por campo, navegação hierárquica em três níveis e um grafo direcionado de assuntos relacionados (`src/busca_grafo.py`).
- **Em tempo de desenvolvimento (apoio à engenharia):** Ferramentas de IA generativa (ChatGPT e Gemini) foram utilizadas exclusivamente pela equipe durante a fase de construção do projeto para acelerar tarefas específicas de pesquisa preliminar, prototipação de modelos de instrução, geração de casos de teste adversariais e revisão técnica de código e documentação.

## 2. Onde e Como a IA Foi Utilizada no Desenvolvimento

O uso de ferramentas de IA ficou restrito a quatro frentes de apoio, sempre sob supervisão e decisão final dos integrantes da equipe:

| Frente de Trabalho | Ferramenta / Uso Aplicado | Artefatos Impactados |
| --- | --- | --- |
| Estruturação de Modelos de Prompt | Elaboração e contraste de dois formatos de instrução de resposta, definindo papel do assistente, regras de conduta, citação obrigatória de fonte e avisos de limitação. | `src/prompts.py` (`MODELOS_PROMPT`) |
| Síntese Inicial da Base de Conhecimento | Apoio na redação resumida de normas extensas (como a Lei Brasileira de Inclusão) e na sugestão inicial de palavras-chave e sinônimos cotidianos usados por cidadãos. | `data/base.json` e `SINONIMOS_E_RADICAIS` (`src/busca_grafo.py`) |
| Planejamento de Testes e Estresse | Geração de reformulações coloquiais, consultas fora de escopo, erros de digitação e frases longas com ruído para testar os limites do algoritmo de busca. | `CASOS_DE_TESTE` (`src/avaliacao.py`) |
| Revisão de Código e Documentação | Revisão de legibilidade, separação de responsabilidades entre módulos e verificação de aderência aos itens exigidos no edital. | `src/*.py`, `README.md` e `docs/relatorio.pdf` |

## 3. Justificativa Técnica para Não Usar LLMs no Protótipo

Em conformidade com as regras técnicas do edital, optamos por um motor de recuperação da informação fechado e programado em vez de acoplar um modelo generativo ao terminal pelos seguintes motivos:

- **Controle contra alucinações:** O domínio do projeto envolve direitos legais, isenções tributárias e regras de transporte para pessoas com deficiência. Uma resposta inventada ou desatualizada sobre prazos de laudo médico ou canais de atendimento gera prejuízo real ao usuário. Ao restringir as respostas aos 23 registros verificados em `data/base.json`, garantimos rastreabilidade integral.
- **Transparência explícita de escopo:** Quando uma pergunta não atinge a pontuação mínima de relevância (`pontuacao_minima = 4`), o sistema informa que não possui base confiável e exibe os temas disponíveis, em vez de extrapolar ou simular conhecimento oficial.
- **Desempenho e privacidade:** A execução local usando apenas a biblioteca padrão do Python alcançou tempo médio de consulta de 2,944 ms nos 18 testes automatizados, sem dependência de rede, sem custo de tokens e sem envio de consultas do usuário para servidores de terceiros.

## 4. Validação Crítica Realizada pela Equipe

Nenhuma saída gerada com apoio de IA foi incorporada diretamente sem auditoria. O processo de validação foi dividido em quatro etapas práticas.

### 4.1 Verificação das Fontes e da Legislação da Base (`data/base.json`)

Todos os 23 registros da base de conhecimento passaram por verificação manual nos portais oficiais dos órgãos responsáveis e na legislação vigente nas datas registradas no próprio JSON (2026-11-13 para os IDs 1 a 15, 2026-11-14 para os IDs 16 a 22 e 2026-11-16 para o ID 23).

Durante essa auditoria, identificamos e corrigimos imprecisões comuns em rascunhos gerados por IA:

- **Especificidade local (São Paulo):** Rascunhos iniciais tendiam a misturar regras federais com procedimentos municipais. Ajustamos os registros para apontar os canais exatos da capital paulista, como o Portal SP156 para o Cartão Defis (ID #5), o sistema SIVEI da Secretaria da Fazenda SP para isenção de IPVA (ID #4) e os postos da SPTrans para o Bilhete Único Especial (ID #1), incluindo a validade de 90 dias do laudo médico.
- **Restrições operacionais de serviços:** No registro sobre aplicativos de mobilidade (ID #21), incluímos explicitamente a ressalva de que a categoria Uber Assist oferece apoio de motoristas treinados, mas os veículos não possuem rampa ou elevador para embarque na própria cadeira de rodas.
- **Inserção de avisos de limitação em tempo real:** Nos registros de situações dinâmicas ou emergenciais (IDs 16 a 22), adicionamos cláusulas iniciadas por "Aviso:" (tratadas de forma destacada pela função `_separar_orientacao_e_aviso` em `src/prompts.py`) informando que o protótipo não monitora elevadores do metrô nem condições climáticas em tempo real.

### 4.2 Validação Empírica dos Dois Modelos de Prompt (`src/prompts.py`)

Para evitar uma escolha subjetiva entre os modelos de instrução estruturados com apoio de IA, implementamos a função `avaliar_modelos_em_consultas()` em `src/prompts.py`. Ela executa o Modelo 1 (Direto) e o Modelo 2 (Didático) sobre os 13 casos de teste com resposta válida (T01 a T10 e T16 a T18) e contabiliza critérios objetivos de saída:

| Critério Avaliado | Modelo 1 (Direto) | Modelo 2 (Didático) |
| --- | --- | --- |
| Cita fonte oficial | 100,0% | 100,0% |
| Cita data de verificação | 100,0% | 100,0% |
| Exibe aviso de limitação | 100,0% | 100,0% |
| Sugere relacionados (grafo) | 0,0% | 100,0% |
| Tamanho médio da resposta | 13,5 linhas | 34,2 linhas |

**Análise crítica da equipe:** Os números confirmaram que ambos os modelos cumprem os requisitos mínimos de rastreabilidade (100% em fonte, data e aviso). O Modelo 2 foi escolhido como padrão por segmentar a leitura em quatro blocos e integrar a continuidade via grafo de conhecimento. Entretanto, no teste de facilidade de uso com três participantes (P1 a P3), observamos que o volume médio de 34,2 linhas exigiu maior esforço de leitura (relatado por P1) e gerou hesitação na navegação por assuntos relacionados (P2 e P3). Por isso, mantivemos a opção 4 no menu principal para permitir a alternância rápida para o Modelo 1 (13,5 linhas).

### 4.3 Auditoria do Algoritmo de Busca e Diagnóstico de Falha (`src/avaliacao.py`)

Validamos o impacto das regras de normalização, stopwords, radicalização leve e sinônimos comparando a busca ranqueada contra uma busca simples linear por palavra-chave (`buscar_simples_palavra_chave`) nos mesmos 18 casos de teste:

- **Busca Simples (baseline):** 3 acertos em 18 testes (16,7%), com tempo médio de 0,842 ms. Falhou em 15 casos por gerar empates artificiais em palavras comuns. Ex: "como".
- **Busca Ranqueada (solução adotada):** 17 acertos em 18 testes (94,4%), com tempo médio de 2,944 ms.

**Análise crítica da falha no teste T18:** O caso T18 ("Oi bom dia tudo bem eu queria saber se por acaso existe algum lugar na cidade onde eu possa pedir aquela carteirinha para estacionar na vaga azul de deficiente") foi projetado para testar ruído coloquial. O algoritmo retornou o ID #8 (cotas em concursos públicos, 11 pontos) em vez do ID #5 (Credencial Defis).

Ao auditar a pontuação, verificamos que os termos "deficiente" e "vaga" pontuaram no ID #8 por meio do dicionário de sinônimos (deficiente -> pcd) e radicalização (vaga -> vagas), enquanto "carteirinha" e "estacionar" não possuíam mapeamento para "credencial" e "estacionamento" no ID #5. Optamos por manter o caso T18 como erro registrado em `docs/resultados_testes.csv` para evidenciar com transparência a limitação de dicionários de sinônimos cadastrados manualmente.

### 4.4 Revisão de Integridade de Dados, Privacidade e Escopo

Todo o código produzido foi testado localmente pela equipe para assegurar conformidade com as restrições do edital:

- **Validação de entrada e schema:** Verificamos que `validar_registro()` em `src/base_dados.py` rejeita registros incompletos, IDs duplicados ou booleanos tratados como inteiros, enquanto `validar_entrada_consulta()` em `src/prompts.py` bloqueia entradas vazias ou com menos de dois caracteres antes da busca.
- **Privacidade:** Confirmamos que nenhum módulo solicita, armazena ou registra CPF, RG, endereço ou histórico identificável do cidadão.
- **Separação de entregas:** O repositório contém uma interface web complementar na pasta `incluisp/` desenvolvida como extensão opcional, mas toda a avaliação técnica, métricas e validação crítica deste documento referem-se diretamente ao protótipo principal em Python (`src/` e `data/base.json`).

## 5. Declaração de Autoria e Responsabilidade

A equipe declara que compreende integralmente o funcionamento de todos os módulos, estruturas de dados e algoritmos presentes neste repositório. As ferramentas de IA atuaram como suporte auxiliar de produtividade, cabendo exclusivamente aos integrantes da equipe a definição da arquitetura, a conferência das fontes oficiais, a execução dos testes automatizados e de usabilidade e a análise crítica dos resultados.
