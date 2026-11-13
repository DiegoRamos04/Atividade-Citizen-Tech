import json

def carregar_base_conhecimento(caminho_arquivo="data/base.json"):

    try:
        # Tenta abrir o arquivo em modo de leitura ('r') com codificação UTF-8 para aceitar acentos
        with open(caminho_arquivo, 'r', encoding='utf-8') as arquivo:
            # Converte o texto do JSON para estruturas de dados do Python (dicionários e listas)
            dados = json.load(arquivo)
            
            # Retorna apenas a lista que está dentro da chave "base_conhecimento"
            return dados.get("base_conhecimento", [])
            
    except FileNotFoundError:
        # Tratamento caso o arquivo não exista no local indicado
        print(f"[ERRO] O arquivo '{caminho_arquivo}' não foi encontrado.")
        print("Dica: Certifique-se de executar o programa a partir da pasta raiz do projeto.")
        return []
        
    except json.JSONDecodeError:
        # Tratamento caso o arquivo esteja vazio ou com algum erro de sintaxe
        print(f"[ERRO] O arquivo '{caminho_arquivo}' possui formatação inválida ou está vazio.")
        return []
        
    except Exception as e:
        # Tratamento genérico para qualquer outro erro inesperado
        print(f"[ERRO] Ocorreu um problema inesperado ao ler a base de dados: {e}")
        return []

# Este bloco só executa se você rodar este arquivo diretamente.
if __name__ == "__main__":
    print("Iniciando o sistema Citizen Assist AI...")
    base_dados = carregar_base_conhecimento()
    
    if base_dados:
        print(f"\n[SUCESSO] Base de dados carregada com {len(base_dados)} orientações!")
        print("-" * 40)
        print("Mostrando o primeiro registro para conferência:")
        print(f"Tema: {base_dados[0]['tema']}")
        print(f"Pergunta: {base_dados[0]['pergunta']}")
        print(f"Fonte: {base_dados[0]['fonte']}")
        print("-" * 40)
    else:
        print("\n[FALHA] Não foi possível carregar as orientações. Verifique os erros acima.")
