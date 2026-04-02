import json
import os
import re
import docx2txt
import tempfile
import shutil
import uuid

# Configurações de Pastas
PASTA_FICHAS = './fichas_docx'
PASTA_FOTOS = './fotos'
ARQUIVO_JSON = './dados.json'

os.makedirs(PASTA_FICHAS, exist_ok=True)
os.makedirs(PASTA_FOTOS, exist_ok=True)

def extrair_dados_do_texto(texto, imagens_extraidas, dir_temporario, id_preso):
    def buscar_campo(label, proximo_label=""):
        # Regex flexível para achar os dados entre as labels
        if proximo_label:
            padrao = rf"{label}\s*:?\s*(.*?)(?=\s*{proximo_label}\s*:?|$)"
        else:
            padrao = rf"{label}\s*:?\s*([^\n,]+)"
            
        match = re.search(padrao, texto, re.IGNORECASE | re.DOTALL)
        if match:
            return match.group(1).replace("\n", " ").strip()
        return ""

    nome_preso = buscar_campo("Nome", "CPF") or buscar_campo("Nome")
    if not nome_preso:
        nome_preso = "Não Identificado"

    # Mover e renomear as fotos para a pasta /fotos
    # [0] costuma ser o brasão, [1] Frente, [2] Perfil Esq, [3] Perfil Dir
    foto_frente = ""
    foto_esq = ""
    foto_dir = ""

    def processar_foto(index, sufixo):
        if len(imagens_extraidas) > index:
            img_original = imagens_extraidas[index]
            extensao = img_original.split('.')[-1]
            novo_nome = f"{id_preso}_{sufixo}.{extensao}"
            caminho_antigo = os.path.join(dir_temporario, img_original)
            caminho_novo = os.path.join(PASTA_FOTOS, novo_nome)
            shutil.copy(caminho_antigo, caminho_novo)
            return f"./fotos/{novo_nome}"
        return ""

    foto_frente = processar_foto(1, "frente")
    foto_esq = processar_foto(2, "esq")
    foto_dir = processar_foto(3, "dir")

    return {
        "id": id_preso,
        "nome": nome_preso,
        "cpf": buscar_campo("CPF", "Mãe") or buscar_campo("CPF"),
        "mae": buscar_campo("Mãe", "RG") or buscar_campo("Mãe"),
        "pai": buscar_campo("Pai", "Data de Nascimento") or buscar_campo("Pai"),
        "rg": buscar_campo("RG", "Pai") or buscar_campo("RG"),
        "dataNascimento": buscar_campo("Data de Nascimento", "Alcunha") or buscar_campo("Data de Nascimento"),
        "bo": buscar_campo("Número do BO", "Artigo") or buscar_campo("Número do BO"),
        "artigo": buscar_campo("Artigo", "Estado Civil") or buscar_campo("Artigo"),
        "naturalidade": buscar_campo("Naturalidade", "Cidade") or buscar_campo("Naturalidade"),
        "bairro": buscar_campo("Bairro", "Rua") or buscar_campo("Bairro"),
        "rua": buscar_campo("Rua", "Número") or buscar_campo("Rua"),
        "dataEntrada": buscar_campo("Data de entrada", "Data de saída") or buscar_campo("Data de entrada"),
        "fotoFrente": foto_frente,
        "fotoEsquerdo": foto_esq,
        "fotoDireito": foto_dir,
        "alcunha": buscar_campo("Alcunha", "Orcrim") or buscar_campo("Alcunha"),
        "orcrim": buscar_campo("Orcrim", "Número do BO") or buscar_campo("Orcrim"),
        "estadoCivil": buscar_campo("Estado Civil", "Cônjuge") or buscar_campo("Estado Civil"),
        "conjuge": buscar_campo("Cônjuge", "Profissão") or buscar_campo("Cônjuge"),
        "profissao": buscar_campo("Profissão", "Naturalidade") or buscar_campo("Profissão")
    }

def processar_fichas():
    banco_de_dados = []

    if os.path.exists(ARQUIVO_JSON):
        with open(ARQUIVO_JSON, 'r', encoding='utf-8') as f:
            try:
                banco_de_dados = json.load(f)
            except json.JSONDecodeError:
                banco_de_dados = []

    arquivos_docx = [f for f in os.listdir(PASTA_FICHAS) if f.endswith('.docx')]

    if not arquivos_docx:
        print("Nenhuma ficha nova encontrada na pasta 'fichas_docx'.")
        return

    processados = 0
    for arquivo in arquivos_docx:
        caminho_arquivo = os.path.join(PASTA_FICHAS, arquivo)
        print(f"Lendo arquivo: {arquivo}...")

        # Gerar um ID único para esse preso e suas fotos
        id_unico = uuid.uuid4().hex[:8]

        # Extrair texto e imagens usando um diretório temporário
        with tempfile.TemporaryDirectory() as temp_dir:
            texto = docx2txt.process(caminho_arquivo, temp_dir)
            imagens_geradas = sorted(os.listdir(temp_dir))
            
            dados_extraidos = extrair_dados_do_texto(texto, imagens_geradas, temp_dir, id_unico)
            
            # Evitar adicionar duplicados (checa se já tem alguém com o mesmo BO e CPF)
            duplicado = False
            for d in banco_de_dados:
                if d.get('cpf') == dados_extraidos['cpf'] and d.get('bo') == dados_extraidos['bo']:
                    duplicado = True
                    break
            
            if not duplicado:
                banco_de_dados.insert(0, dados_extraidos)
                processados += 1
            else:
                print(f" -> Preso {dados_extraidos['nome']} já existe no sistema. Ignorando.")

        # Opcional: Apaga o .docx original para a pasta ficar limpa após o processamento
        os.remove(caminho_arquivo)

    with open(ARQUIVO_JSON, 'w', encoding='utf-8') as f:
        json.dump(banco_de_dados, f, ensure_ascii=False, indent=4)
    
    print(f"SUCESSO! {processados} nova(s) ficha(s) processada(s) e adicionada(s) ao dados.json.")

if __name__ == "__main__":
    processar_fichas()