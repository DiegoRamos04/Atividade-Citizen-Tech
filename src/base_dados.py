import json
from pathlib import Path

# Localiza a raiz do projeto automaticamente, independente de onde o terminal esteja
RAIZ_PROJETO = Path(__file__).resolve().parent.parent
CAMINHO_PADRAO_BASE = RAIZ_PROJETO / "data" / "base.json"

# Tupla com os campos obrigatórios exigidos pelo edital 
CAMPOS_OBRIGATORIOS = (
    "id",
    "tema",
    "pergunta",
    "palavras_chave",
    "orientacao",
    "fonte",
    "data_verificacao",
)


def validar_registro(registro, ids_existentes=None):
    """
    Verifica se um dicionário de orientação possui todos os campos essenciais
    preenchidos, se o 'id' é um inteiro positivo único (quando ids_existentes
    é informado) e se os tipos dos campos são válidos.
    """
    if not isinstance(registro, dict):
        return False

    for campo in CAMPOS_OBRIGATORIOS:
        if campo not in registro:
            return False
        valor = registro[campo]
        if valor is None or (isinstance(valor, str) and not valor.strip()):
            return False

    # Valida tipo e valor do ID (em Python bool é subclasse de int, então excluímos bool)
    id_valor = registro["id"]
    if isinstance(id_valor, bool) or not isinstance(id_valor, int) or id_valor <= 0:
        return False

    # Verifica duplicidade de ID caso um conjunto de controle seja fornecido
    if ids_existentes is not None and id_valor in ids_existentes:
        return False

    # Garante que palavras_chave seja uma lista não vazia
    if not isinstance(registro["palavras_chave"], list) or len(registro["palavras_chave"]) == 0:
        return False

    return True


def carregar_base_conhecimento(caminho_arquivo=CAMINHO_PADRAO_BASE):
    """
    Lê o arquivo JSON, valida os registros (incluindo tipo e unicidade do ID)
    e trata erros de arquivo ausente, vazio ou com estrutura inconsistente.
    """
    try:
        with open(caminho_arquivo, "r", encoding="utf-8") as arquivo:
            dados = json.load(arquivo)

        if not isinstance(dados, dict) or "base_conhecimento" not in dados:
            print(f"[ERRO] O arquivo '{caminho_arquivo}' não contém a chave 'base_conhecimento'.")
            return []

        lista_bruta = dados["base_conhecimento"]
        if not isinstance(lista_bruta, list) or len(lista_bruta) == 0:
            print(f"[ERRO] A base de conhecimento em '{caminho_arquivo}' está vazia.")
            return []

        registros_validos = []
        ids_vistos = set()
        for indice, item in enumerate(lista_bruta, start=1):
            if validar_registro(item, ids_existentes=ids_vistos):
                registros_validos.append(item)
                ids_vistos.add(item["id"])
            else:
                print(f"[AVISO] Registro na posição {indice} ignorado por estar incompleto, inválido ou com ID duplicado.")

        return registros_validos

    except FileNotFoundError:
        print(f"[ERRO] O arquivo '{caminho_arquivo}' não foi encontrado.")
        print("Dica: Verifique se o arquivo 'data/base.json' existe na pasta raiz do projeto.")
        return []

    except json.JSONDecodeError:
        print(f"[ERRO] O arquivo '{caminho_arquivo}' está vazio ou possui sintaxe JSON inválida.")
        return []

    except Exception as erro:
        print(f"[ERRO] Falha inesperada ao carregar a base de dados: {erro}")
        return []


def listar_temas(base_dados):
    """
    Extrai e ordena dinamicamente os temas únicos disponíveis na base.
    """
    temas = sorted({registro["tema"] for registro in base_dados})
    return temas


def contar_por_tema(base_dados):
    """
    Retorna um dicionário com a quantidade de orientações por tema.
    """
    contagem = {}
    for registro in base_dados:
        tema = registro["tema"]
        contagem[tema] = contagem.get(tema, 0) + 1
    return contagem


def buscar_por_id(base_dados, id_procurado):
    """
    Recupera um registro específico pelo seu identificador numérico (id).
    """
    for registro in base_dados:
        if registro["id"] == id_procurado:
            return registro
    return None

def salvar_base_conhecimento(base_dados, caminho_arquivo=CAMINHO_PADRAO_BASE):
    """
    Persiste a lista atualizada de orientações no arquivo JSON com indentação
    legível e codificação UTF-8.
    """
    estrutura = {"base_conhecimento": base_dados}
    with open(caminho_arquivo, "w", encoding="utf-8") as arquivo:
        json.dump(estrutura, arquivo, ensure_ascii=False, indent=2)


def obter_proximo_id(base_dados):
    """
    Calcula o próximo identificador numérico sequencial disponível na base.
    """
    if not base_dados:
        return 1
    return max(int(reg["id"]) for reg in base_dados) + 1


def adicionar_registro(base_dados, novo_registro, caminho_arquivo=CAMINHO_PADRAO_BASE):
    """
    Valida os campos obrigatórios de um novo registro, atribui o próximo ID
    automaticamente (caso não informado), anexa à base e salva no arquivo JSON.
    """
    registro_preparado = dict(novo_registro)
    if "id" not in registro_preparado or registro_preparado["id"] is None:
        registro_preparado["id"] = obter_proximo_id(base_dados)

    if not validar_registro(registro_preparado):
        return False, "Registro inválido: verifique se todos os campos obrigatórios foram preenchidos."

    if buscar_por_id(base_dados, int(registro_preparado["id"])) is not None:
        return False, f"Já existe um registro cadastrado com o ID #{registro_preparado['id']}."

    base_dados.append(registro_preparado)
    salvar_base_conhecimento(base_dados, caminho_arquivo)
    return True, f"Registro ID #{registro_preparado['id']} adicionado e salvo com sucesso!"


def atualizar_registro(base_dados, id_registro, campos_atualizados, caminho_arquivo=CAMINHO_PADRAO_BASE):
    """
    Atualiza campos de um registro existente (como orientação, fonte, data ou
    assuntos relacionados), valida a integridade e grava no arquivo JSON.
    """
    registro_atual = buscar_por_id(base_dados, int(id_registro))
    if not registro_atual:
        return False, f"Registro ID #{id_registro} não encontrado na base."

    copia_validacao = dict(registro_atual)
    for chave, valor in campos_atualizados.items():
        if valor is not None:
            copia_validacao[chave] = valor

    if not validar_registro(copia_validacao):
        return False, "Alteração rejeitada: nenhum campo obrigatório pode ficar vazio."

    registro_atual.update(copia_validacao)
    salvar_base_conhecimento(base_dados, caminho_arquivo)
    return True, f"Registro ID #{id_registro} atualizado e salvo com sucesso!"