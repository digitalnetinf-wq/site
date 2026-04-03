import json
import os
import re
import docx2txt
import tempfile
import uuid
import unicodedata
import shutil

try:
    from PIL import Image
    USA_PILLOW = True
except ImportError:
    USA_PILLOW = False
    print("\n⚠️  Aviso: Biblioteca 'Pillow' não instalada.")
    print("⚠️  Sem ela, o sistema NÃO CONSEGUE filtrar ícones/logos pequenos (ex: o logo da polícia no topo da ficha).")
    print("⚠️  Isso pode fazer com que um ícone seja salvo como a 'foto de frente'.")
    print("Para corrigir, rode no terminal: py -m pip install Pillow\n")

# Configurações de Pastas
PASTA_FICHAS = './fichas_docx'
PASTA_FOTOS = './fotos'
ARQUIVO_JSON = './dados.json'

os.makedirs(PASTA_FICHAS, exist_ok=True)
os.makedirs(PASTA_FOTOS, exist_ok=True)

def limpar_texto_base(texto):
    if not texto: return ""
    texto = unicodedata.normalize("NFKC", texto)
    texto = re.sub(r'\s+', ' ', texto)
    return texto.strip()

def extrair_dados_do_texto(texto, imagens_extraidas, dir_temporario, id_preso):
    texto_limpo = limpar_texto_base(texto)
    
    mapa_chaves = {
        "Número do BO": "bo",
        "Prisão realizada por": "prisaoRealizadaPor",
        "Data de Nascimento": "dataNascimento",
        "Facção/Orcrim": "faccaoOrcrim",
        "Presídio/Alvará": "presidioAlvara",
        "Estado Civil": "estadoCivil",
        "Data de entrada": "dataEntrada",
        "Data de saída": "dataSaida",
        "Bloco/Apto": "blocoApto",
        "Observações": "observacoes",
        "Naturalidade": "naturalidade",
        "Profissão": "profissao",
        "Condomínio": "condominio",
        "Cônjuge": "conjuge",
        "Alcunha": "alcunha",
        "Bairro": "bairro",
        "Cidade": "cidade",
        "Número": "numero", 
        "Artigo": "artigo",
        "FOTOS": "fotos_ignorar", 
        "Nome": "nome",
        "Mãe": "mae",
        "Pai": "pai",
        "CPF": "cpf",
        "RG": "rg",
        "Rua": "rua"
    }

    posicoes_encontradas = []
    
    for rotulo, chave_json in mapa_chaves.items():
        if rotulo == "Número":
            padrao = r'\bNúmero\b(?!\s*do\s*BO)\s*:?'
        else:
            padrao = rf'\b{re.escape(rotulo)}\b\s*:?'
            
        for match in re.finditer(padrao, texto_limpo, re.IGNORECASE):
            posicoes_encontradas.append({
                'chave_json': chave_json,
                'inicio': match.start(),
                'fim': match.end()
            })

    posicoes_encontradas.sort(key=lambda x: x['inicio'])

    dados_finais = {v: "" for v in mapa_chaves.values() if v != "fotos_ignorar"}
    dados_finais["id"] = id_preso

    for i in range(len(posicoes_encontradas)):
        item_atual = posicoes_encontradas[i]
        chave_atual = item_atual['chave_json']
        inicio_valor = item_atual['fim']
        
        if i + 1 < len(posicoes_encontradas):
            fim_valor = posicoes_encontradas[i + 1]['inicio']
        else:
            fim_valor = len(texto_limpo)
            
        valor_extraido = texto_limpo[inicio_valor:fim_valor].strip()
        valor_extraido = re.sub(r'^[:\-\.,]+|[:\-\.,]+$', '', valor_extraido).strip()
        
        if chave_atual == "cpf" and valor_extraido:
            valor_extraido = re.sub(r'[^0-9.-]', '', valor_extraido)
            
        if chave_atual != "fotos_ignorar":
            if not dados_finais[chave_atual]: 
                dados_finais[chave_atual] = valor_extraido

    # --- PROCESSAMENTO DE FOTOS COM INTELIGÊNCIA ---
    fotos_validas = []
    
    # Lista todas as imagens extraídas e ordena pelo nome (image1, image2...)
    imagens_ordenadas = sorted([f for f in os.listdir(dir_temporario) if f.lower().endswith(('.png', '.jpg', '.jpeg'))])

    if USA_PILLOW:
        # 1. Filtro de Tamanho (ignora imagens pequenas como ícones)
        for img_nome in imagens_ordenadas:
            caminho_img = os.path.join(dir_temporario, img_nome)
            try:
                with Image.open(caminho_img) as img:
                    largura, altura = img.size
                    # Ícones de cabeçalho geralmente são menores que 300x300.
                    # Fotos de presos (perfil) geralmente são maiores.
                    if largura >= 300 and altura >= 300:
                        fotos_validas.append(img_nome)
            except Exception:
                continue
    else:
        # Se não houver Pillow, pega todas as imagens
        fotos_validas = imagens_ordenadas

    # 2. Lógica de "Pular o Ícone": Se houver muitas imagens válidas,
    # assume-se que a primeira é o ícone da polícia e as próximas três são as fotos.
    total_fotos_validas = len(fotos_validas)
    fotos_para_processar = []
    
    # Se houver mais de 3 fotos válidas, pulamos a primeira
    if total_fotos_validas > 3:
        # Assume que o ícone é a primeira imagem válida (image1...)
        print(f" ℹ️  Detectadas {total_fotos_validas} imagens válidas. Pulando a primeira (provavelmente o ícone) e pegando as próximas três.")
        fotos_para_processar = fotos_validas[1:4] # Pega os índices 1, 2 e 3 (pula o 0)
    else:
        # Se houver 3 ou menos, pega todas as que foram encontradas
        print(f" ℹ️  Detectadas {total_fotos_validas} imagens válidas. Pegando todas.")
        fotos_para_processar = fotos_validas[:3] # Pega até 3 primeiras

    # 3. Salva as fotos corretas
    def salvar_foto(index, sufixo):
        if index < len(fotos_para_processar):
            nome_original = fotos_para_processar[index]
            novo_nome = f"{id_preso}_{sufixo}.jpg"
            caminho_origem = os.path.join(dir_temporario, nome_original)
            caminho_destino = os.path.join(PASTA_FOTOS, novo_nome)
            
            if USA_PILLOW:
                try:
                    with Image.open(caminho_origem) as img:
                        img = img.convert('RGB')
                        # Redimensiona para um tamanho padrão e comprime
                        img.thumbnail((800, 800), Image.Resampling.LANCZOS)
                        img.save(caminho_destino, "JPEG", optimize=True, quality=75)
                    return f"./fotos/{novo_nome}"
                except Exception as e:
                    print(f" ❌ Erro ao processar foto {sufixo}: {e}")
            else:
                # Sem Pillow, apenas copia o arquivo original
                shutil.copy(caminho_origem, caminho_destino)
                return f"./fotos/{novo_nome}"
        return ""

    dados_finais["fotoFrente"] = salvar_foto(0, "frente")
    dados_finais["fotoEsquerdo"] = salvar_foto(1, "esq")
    dados_finais["fotoDireito"] = salvar_foto(2, "dir")
    dados_finais.pop("fotos_ignorar", None)

    return dados_finais

def processar_fichas():
    print("🔍 Iniciando o sistema de extração...")
    banco_de_dados = []

    if os.path.exists(ARQUIVO_JSON):
        with open(ARQUIVO_JSON, 'r', encoding='utf-8') as f:
            try:
                banco_de_dados = json.load(f)
            except json.JSONDecodeError:
                banco_de_dados = []

    arquivos_docx = [f for f in os.listdir(PASTA_FICHAS) if f.endswith('.docx') and not f.startswith('~')]

    if not arquivos_docx:
        print("☕ Nenhuma ficha nova (.docx) foi encontrada na pasta 'fichas_docx'. Coloque algum arquivo lá e rode novamente.")
        return

    processados = 0
    
    for arquivo in arquivos_docx:
        caminho_arquivo = os.path.join(PASTA_FICHAS, arquivo)
        print(f"\n📄 Lendo arquivo: {arquivo}...")

        id_unico = uuid.uuid4().hex[:8]

        with tempfile.TemporaryDirectory() as temp_dir:
            try:
                # docx2txt extrai imagens para o diretório temporário
                texto = docx2txt.process(caminho_arquivo, temp_dir)
                
                # Envia o ID temporário para a função de extração
                dados_extraidos = extrair_dados_do_texto(texto, [], temp_dir, id_unico)
                
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
                    print(f" ✅ Adicionado com sucesso: {dados_extraidos['nome']}")
                else:
                    print(f" ⚠️ Ficha ignorada (Já existe no sistema).")

                # Deleta o docx original após processar
                os.remove(caminho_arquivo)
                
            except Exception as e:
                print(f" ❌ Erro ao processar '{arquivo}': {e}")

    if processados > 0:
        with open(ARQUIVO_JSON, 'w', encoding='utf-8') as f:
            json.dump(banco_de_dados, f, ensure_ascii=False, indent=4)
        print(f"\n🎉 SUCESSO! {processados} ficha(s) processada(s) e salva(s) no dados.json.")

if __name__ == "__main__":
    processar_fichas()