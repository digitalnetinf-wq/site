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

def limpar_texto(texto):
    """Remove quebras de linha extras e múltiplos espaços brancos"""
    if not texto:
        return ""
    return re.sub(r'\s+', ' ', texto).strip()

def extrair_dados_do_texto(texto, imagens_extraidas, dir_temporario, id_preso):
    
    def buscar_campo(label, proximo_label=None):
        """Busca a informação baseada na label e limpa o resultado"""
        if proximo_label:
            # Busca tudo entre a label atual e a próxima label
            padrao = rf"{label}\s*:?\s*(.*?)(?=\s*{proximo_label}\s*:?|$)"
        else:
            # Busca tudo até a quebra de linha
            padrao = rf"{label}\s*:?\s*([^\n]+)"
            
        match = re.search(padrao, texto, re.IGNORECASE | re.DOTALL)
        if match:
            resultado = match.group(1)
            # Se o resultado acidentalmente capturou outra label (fallback de segurança)
            if ":" in resultado and len(resultado.split(":")[0]) < 20:
                resultado = resultado.split(":")[0]
                
            return limpar_texto(resultado)
        return ""

    # Extração de Dados Pessoais e Criminais
    nome_preso = buscar_campo("Nome", "CPF") or buscar_campo("Nome")
    if not nome_preso:
        nome_preso = "Não Identificado"

    # Mover e renomear as fotos para a pasta /fotos
    # Assumindo: [0] Brasão/Logo, [1] Frente, [2] Perfil Esq, [3] Perfil Dir
    def processar_foto(index, sufixo):
        if len(imagens_extraidas) > index:
            img_original = imagens_extraidas[index]
            extensao = img_original.split('.')[-1].lower()
            
            # Aceita apenas arquivos de imagem comuns
            if extensao in ['jpg', 'jpeg', 'png']:
                novo_nome = f"{id_preso}_{sufixo}.{extensao}"
                caminho_antigo = os.path.join(dir_temporario, img_original)
                caminho_novo = os.path.join(PASTA_FOTOS, novo_nome)
                
                try:
                    shutil.copy(caminho_antigo, caminho_novo)
                    return f"./fotos/{novo_nome}"
                except Exception as e:
                    print(f"Erro ao copiar imagem {sufixo}: {e}")
        return ""

    # Montando o Dicionário EXATAMENTE como o frontend espera
    dados = {
        "id": id_preso,
        "nome": nome_preso,
        "cpf": buscar_campo("CPF", "Mãe") or buscar_campo("CPF"),
        "mae": buscar_campo("Mãe", "Pai") or buscar_campo("Mãe") or buscar_campo("Nome da Mãe"),
        "pai": buscar_campo("Pai", "RG") or buscar_campo("Pai") or buscar_campo("Nome do Pai"),
        "rg": buscar_campo("RG", "Data de Nascimento") or buscar_campo("RG"),
        "dataNascimento": buscar_campo("Data de Nascimento", "Naturalidade") or buscar_campo("Data de Nascimento"),
        "naturalidade": buscar_campo("Naturalidade", "Estado Civil") or buscar_campo("Naturalidade"),
        "estadoCivil": buscar_campo("Estado Civil", "Profissão") or buscar_campo("Estado Civil"),
        "profissao": buscar_campo("Profissão", "Cônjuge") or buscar_campo("Profissão"),
        "conjuge": buscar_campo("Cônjuge", "Alcunha") or buscar_campo("Cônjuge"),
        "alcunha": buscar_campo("Alcunha", "Rua") or buscar_campo("Alcunha"),
        "rua": buscar_campo("Rua", "Bairro") or buscar_campo("Rua") or buscar_campo("Endereço"),
        "bairro": buscar_campo("Bairro", "Artigo") or buscar_campo("Bairro"),
        "artigo": buscar_campo("Artigo", "Número do BO") or buscar_campo("Artigo") or buscar_campo("Crime"),
        "bo": buscar_campo("Número do BO", "Orcrim") or buscar_campo("Número do BO") or buscar_campo("BO"),
        "orcrim": buscar_campo("Orcrim", "Data de entrada") or buscar_campo("Orcrim") or buscar_campo("Facção"),
        "dataEntrada": buscar_campo("Data de entrada", "Data de saída") or buscar_campo("Data de entrada"),
        
        # Fotos
        "fotoFrente": processar_foto(1, "frente"),
        "fotoEsquerdo": processar_foto(2, "esq"),
        "fotoDireito": processar_foto(3, "dir")
    }
    
    return dados

def processar_fichas():
    banco_de_dados = []

    # Carrega o banco existente
    if os.path.exists(ARQUIVO_JSON):
        with open(ARQUIVO_JSON, 'r', encoding='utf-8') as f:
            try:
                banco_de_dados = json.load(f)
            except json.JSONDecodeError:
                print("Aviso: arquivo dados.json estava corrompido ou vazio. Criando um novo.")
                banco_de_dados = []

    arquivos_docx = [f for f in os.listdir(PASTA_FICHAS) if f.endswith('.docx') and not f.startswith('~')]

    if not arquivos_docx:
        print("Nenhuma ficha nova encontrada na pasta 'fichas_docx'.")
        return

    processados = 0
    
    for arquivo in arquivos_docx:
        caminho_arquivo = os.path.join(PASTA_FICHAS, arquivo)
        print(f"\n📄 Lendo arquivo: {arquivo}...")

        id_unico = uuid.uuid4().hex[:8]

        with tempfile.TemporaryDirectory() as temp_dir:
            try:
                # Extrai o texto e as imagens para a pasta temporária
                texto = docx2txt.process(caminho_arquivo, temp_dir)
                imagens_geradas = sorted(os.listdir(temp_dir))
                
                dados_extraidos = extrair_dados_do_texto(texto, imagens_geradas, temp_dir, id_unico)
                
                # Verificação de Duplicidade (checa por CPF ou Número do BO)
                duplicado = False
                for d in banco_de_dados:
                    tem_cpf = dados_extraidos['cpf'] and d.get('cpf') == dados_extraidos['cpf']
                    tem_bo = dados_extraidos['bo'] and d.get('bo') == dados_extraidos['bo']
                    
                    if tem_cpf and tem_bo:
                        duplicado = True
                        break
                
                if not duplicado:
                    banco_de_dados.insert(0, dados_extraidos) # Insere no topo da lista
                    processados += 1
                    print(f" ✅ Adicionado: {dados_extraidos['nome']} | Art: {dados_extraidos['artigo']}")
                else:
                    print(f" ⚠️ Ignorado (Duplicado): Preso {dados_extraidos['nome']} já existe no sistema.")

                # Apaga o .docx original para a pasta ficar limpa
                os.remove(caminho_arquivo)
                
            except Exception as e:
                print(f" ❌ Erro ao processar '{arquivo}': {e}")

    # Salva o arquivo JSON atualizado
    if processados > 0:
        with open(ARQUIVO_JSON, 'w', encoding='utf-8') as f:
            json.dump(banco_de_dados, f, ensure_ascii=False, indent=4)
        print(f"\n🎉 SUCESSO! {processados} nova(s) ficha(s) processada(s) e injetada(s) no sistema.")
    else:
        print("\nNenhuma nova ficha foi adicionada ao sistema.")

if __name__ == "__main__":
    print("Iniciando Sistema de Processamento de Fichas (Polícia Civil BA)...")
    processar_fichas()