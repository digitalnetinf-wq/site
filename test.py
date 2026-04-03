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

def extrair_dados_do_texto(texto, imagens_extraidas, dir_temporario, id_preso):
    
    # Achata todo o texto para uma linha só. Removemos quebras de página do Word
    # para evitar que os dados se percam nas quebras.
    texto_limpo = re.sub(r'\s+', ' ', texto).strip()

    # LISTA DE BARREIRAS: Atualizada com todos os campos solicitados
    chaves_parada = [
        "Nome", "CPF", "Mãe", "Pai", "RG", "Data de Nascimento", "Alcunha",
        "Facção/Orcrim", "Número do BO", "Artigo", "Estado Civil", "Cônjuge",
        "Profissão", "Naturalidade", "Cidade", "Bairro", "Rua", "Número",
        "Condomínio", "Bloco/Apto", "Data de entrada", "Data de saída",
        "Prisão realizada por", "Presídio/Alvará", "Observações", "FOTOS",
        "ESTADO DA BAHIA", "SECRETARIA DE SEGURANÇA", "Perfil FRENTE", "PERFIL ESQUERDO", "Perfil Direito"
    ]

    def buscar_campo(label_busca):
        # Pega em todas as chaves, mas ignora a própria palavra que estamos a procurar
        barreiras = [c for c in chaves_parada if c.lower() != label_busca.lower()]
        
        # Ordenamos do maior para o menor para evitar conflitos 
        # (ex: "Número do BO" tem de ser detetado antes da palavra "Número" sozinha)
        barreiras.sort(key=len, reverse=True)
        
        # Cria a parede de Regex
        lookahead = "|".join([rf"\b{re.escape(b)}\b" for b in barreiras])
        
        regex_label = re.escape(label_busca)
        # Regra de proteção: Se for procurar a "Rua", a palavra "Número" não pode roubar o "Número do BO"
        if label_busca == "Número":
            regex_label = r"Número(?!\s*do\s*BO)"
            
        # O padrão diz: Acha a etiqueta, os 2 pontos (opcional) e captura TUDO (.*?)
        # de forma preguiçosa até bater numa Barreira (lookahead) ou fim do arquivo ($)
        padrao = rf"\b{regex_label}\b\s*:?\s*(.*?)(?=\s*(?:{lookahead})\s*:?|$)"
        
        match = re.search(padrao, texto_limpo, re.IGNORECASE)
        if match:
            valor = match.group(1).strip()
            return valor.rstrip(':').strip() # Remove pontuação suja no final
        return ""

    nome_preso = buscar_campo("Nome")
    if not nome_preso: nome_preso = "Não Identificado"

    def processar_foto(index, sufixo):
        # Index 0 é o logótipo da polícia no documento Word, por isso começamos a usar o 1, 2 e 3
        if len(imagens_extraidas) > index:
            img_original = imagens_extraidas[index]
            extensao_original = img_original.split('.')[-1].lower()
            
            if extensao_original in ['jpg', 'jpeg', 'png']:
                caminho_antigo = os.path.join(dir_temporario, img_original)
                novo_nome = f"{id_preso}_{sufixo}.jpg"
                caminho_novo = os.path.join(PASTA_FOTOS, novo_nome)
                
                if USA_PILLOW:
                    try:
                        with Image.open(caminho_antigo) as img:
                            if img.mode != 'RGB':
                                img = img.convert('RGB')
                            img.thumbnail((800, 800), Image.Resampling.LANCZOS)
                            img.save(caminho_novo, "JPEG", optimize=True, quality=70)
                        return f"./fotos/{novo_nome}"
                    except Exception as e:
                        print(f"Erro ao comprimir foto {sufixo}: {e}")
                        shutil.copy(caminho_antigo, caminho_novo)
                else:
                    shutil.copy(caminho_antigo, caminho_novo)
                    
                return f"./fotos/{novo_nome}"
        return ""

    # Dicionário Limpo com todos os campos adicionados
    dados = {
        "id": id_preso,
        "nome": nome_preso,
        "cpf": buscar_campo("CPF"),
        "mae": buscar_campo("Mãe"),
        "pai": buscar_campo("Pai"),
        "rg": buscar_campo("RG"),
        "dataNascimento": buscar_campo("Data de Nascimento"),
        "alcunha": buscar_campo("Alcunha"),
        "faccaoOrcrim": buscar_campo("Facção/Orcrim"),
        "bo": buscar_campo("Número do BO"),
        "artigo": buscar_campo("Artigo"),
        "estadoCivil": buscar_campo("Estado Civil"),
        "conjuge": buscar_campo("Cônjuge"),
        "profissao": buscar_campo("Profissão"),
        "naturalidade": buscar_campo("Naturalidade"),
        "cidade": buscar_campo("Cidade"),
        "bairro": buscar_campo("Bairro"),
        "rua": buscar_campo("Rua"),
        "numero": buscar_campo("Número"),
        "condominio": buscar_campo("Condomínio"),
        "blocoApto": buscar_campo("Bloco/Apto"),
        "dataEntrada": buscar_campo("Data de entrada"),
        "dataSaida": buscar_campo("Data de saída"),
        "prisaoRealizadaPor": buscar_campo("Prisão realizada por"),
        "presidioAlvara": buscar_campo("Presídio/Alvará"),
        "observacoes": buscar_campo("Observações"),
        
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
        print(f"\n🎉 SUCESSO! {processados} ficha(s) adicionada(s) corretamente.")

if __name__ == "__main__":
    processar_fichas()