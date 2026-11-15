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


def validar_registro(registro):
    """
    Verifica se um dicionário de orientação possui todos os campos essenciais
    preenchidos e com tipos válidos.
    """
    if not isinstance(registro, dict):
        return False

    for campo in CAMPOS_OBRIGATORIOS:
        if campo not in registro:
            return False
        valor = registro[campo]
        if valor is None or (isinstance(valor, str) and not valor.strip()):
            return False

    # Garante que palavras_chave seja uma lista não vazia
    if not isinstance(registro["palavras_chave"], list) or len(registro["palavras_chave"]) == 0:
        return False

    return True


def carregar_base_conhecimento(caminho_arquivo=CAMINHO_PADRAO_BASE):
    """
    Lê o arquivo JSON, valida os registros e trata erros de arquivo ausente,
    vazio ou com estrutura inconsistente.
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
        for indice, item in enumerate(lista_bruta, start=1):
            if validar_registro(item):
                registros_validos.append(item)
            else:
                print(f"[AVISO] Registro na posição {indice} ignorado por estar incompleto ou inválido.")

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
