import json
import os
import re
import docx2txt
import tempfile
import shutil
import uuid

# Tenta importar o Pillow para compressão de imagens
try:
    from PIL import Image
    USA_PILLOW = True
except ImportError:
    USA_PILLOW = False
    print("⚠️ Aviso: Biblioteca 'Pillow' não instalada. As imagens não serão comprimidas.")
    print("Para instalar, rode no terminal: pip install Pillow")

# Configurações de Pastas
PASTA_FICHAS = './fichas_docx'
PASTA_FOTOS = './fotos'
ARQUIVO_JSON = './dados.json'

os.makedirs(PASTA_FICHAS, exist_ok=True)
os.makedirs(PASTA_FOTOS, exist_ok=True)

def limpar_texto(texto):
    if not texto: return ""
    return re.sub(r'\s+', ' ', texto).strip()

def extrair_dados_do_texto(texto, imagens_extraidas, dir_temporario, id_preso):
    
    def buscar_campo(label, proximo_label=None):
        if proximo_label:
            # Captura tudo desde o label atual até encontrar o próximo label
            padrao = rf"{label}\s*:?\s*(.*?)(?=\s*{proximo_label}\s*:?|$)"
        else:
            padrao = rf"{label}\s*:?\s*([^\n]+)"
            
        match = re.search(padrao, texto, re.IGNORECASE | re.DOTALL)
        if match:
            resultado = match.group(1)
            # Previne cortes errados se encontrar ":" dentro do próprio texto válido
            if ":" in resultado and len(resultado.split(":")[0]) < 20:
                resultado = resultado.split(":")[0]
            return limpar_texto(resultado)
        return ""

    nome_preso = buscar_campo("Nome", "CPF") or buscar_campo("Nome")
    if not nome_preso: nome_preso = "Não Identificado"

    def processar_foto(index, sufixo):
        if len(imagens_extraidas) > index:
            img_original = imagens_extraidas[index]
            extensao_original = img_original.split('.')[-1].lower()
            
            if extensao_original in ['jpg', 'jpeg', 'png']:
                caminho_antigo = os.path.join(dir_temporario, img_original)
                # Forçamos salvar como jpg para padronizar e comprimir melhor
                novo_nome = f"{id_preso}_{sufixo}.jpg"
                caminho_novo = os.path.join(PASTA_FOTOS, novo_nome)
                
                if USA_PILLOW:
                    try:
                        with Image.open(caminho_antigo) as img:
                            # Converte para RGB (evita erro se for PNG com transparência)
                            if img.mode != 'RGB':
                                img = img.convert('RGB')
                            # Redimensiona se a foto for muito gigante (max 800x800)
                            img.thumbnail((800, 800), Image.Resampling.LANCZOS)
                            # Salva com compressão
                            img.save(caminho_novo, "JPEG", optimize=True, quality=70)
                        return f"./fotos/{novo_nome}"
                    except Exception as e:
                        print(f"Erro ao comprimir foto {sufixo}, copiando original: {e}")
                        # Fallback: se falhar, apenas copia
                        shutil.copy(caminho_antigo, caminho_novo)
                else:
                    # Se não tiver o Pillow instalado, apenas copia
                    shutil.copy(caminho_antigo, caminho_novo)
                    
                return f"./fotos/{novo_nome}"
        return ""

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
        "fotoFrente": processar_foto(1, "frente"),
        "fotoEsquerdo": processar_foto(2, "esq"),
        "fotoDireito": processar_foto(3, "dir")
    }
    
    return dados

def processar_fichas():
    banco_de_dados = []

    if os.path.exists(ARQUIVO_JSON):
        with open(ARQUIVO_JSON, 'r', encoding='utf-8') as f:
            try:
                banco_de_dados = json.load(f)
            except json.JSONDecodeError:
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
                texto = docx2txt.process(caminho_arquivo, temp_dir)
                imagens_geradas = sorted(os.listdir(temp_dir))
                
                dados_extraidos = extrair_dados_do_texto(texto, imagens_geradas, temp_dir, id_unico)
                
                duplicado = False
                for d in banco_de_dados:
                    tem_cpf = dados_extraidos['cpf'] and d.get('cpf') == dados_extraidos['cpf']
                    tem_bo = dados_extraidos['bo'] and d.get('bo') == dados_extraidos['bo']
                    
                    if tem_cpf and tem_bo:
                        duplicado = True
                        break
                
                if not duplicado:
                    banco_de_dados.insert(0, dados_extraidos)
                    processados += 1
                    print(f" ✅ Adicionado: {dados_extraidos['nome']}")
                else:
                    print(f" ⚠️ Ignorado (Duplicado).")

                os.remove(caminho_arquivo)
                
            except Exception as e:
                print(f" ❌ Erro ao processar '{arquivo}': {e}")

    if processados > 0:
        with open(ARQUIVO_JSON, 'w', encoding='utf-8') as f:
            json.dump(banco_de_dados, f, ensure_ascii=False, indent=4)
        print(f"\n🎉 SUCESSO! {processados} ficha(s) adicionada(s).")

if __name__ == "__main__":
    processar_fichas()