import os

# Domínio base para os links
DOMINIO = "https://dirpinfsa.com.br"
# Caminho base onde o script está sendo executado
BASE = os.path.dirname(os.path.abspath(__file__))

# Template HTML com design minimalista "Dark"
TEMPLATE = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{cidade} :: DIRPINFSA</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600&display=swap');
        body {{
            font-family: 'Inter', sans-serif;
            background-color: #000000;
        }}
        .fade-in {{
            animation: fadeIn 0.6s ease-out;
        }}
        @keyframes fadeIn {{
            from {{ opacity: 0; transform: translateY(10px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}
    </style>
</head>
<body class="flex flex-col items-center min-h-screen p-6 sm:p-12">

    <div class="max-w-2xl w-full bg-[#0a0a0a] p-8 sm:p-12 rounded-[2.5rem] shadow-2xl border border-[#1a1a1a] fade-in">
        <!-- Cabeçalho -->
        <div class="mb-10">
            <h1 class="text-3xl font-semibold text-white tracking-tight">{cidade}</h1>
            <p class="text-sm text-slate-500 mt-2 font-medium uppercase tracking-[0.1em]">Lista de Sites Autorizados</p>
        </div>

        <!-- Grade de Links -->
        <div class="grid gap-3">
            {links}
        </div>

        <!-- Rodapé -->
        <div class="mt-12 pt-6 border-t border-[#151515] flex justify-between items-center text-[10px] text-slate-700 font-bold uppercase tracking-widest">
            <span>Diretoria de Tecnologia</span>
            <span>Acesso Restrito</span>
        </div>
    </div>

</body>
</html>
"""

# Loop pelas pastas de cidades
for cidade in os.listdir(BASE):
    pasta = os.path.join(BASE, cidade)

    # Pula se não for diretório ou se for pasta oculta
    if not os.path.isdir(pasta) or cidade.startswith("."):
        continue

    # Lista arquivos HTML (exceto o index.html que será gerado)
    sites = [
        f for f in os.listdir(pasta)
        if f.endswith(".html") and f != "index.html"
    ]

    if not sites:
        continue

    links_html = ""
    for site in sorted(sites):
        nome = site.replace(".html", "").replace("_", " ").upper()
        url = f"{DOMINIO}/{cidade}/{site}"
        
        # Estilo do link como um botão minimalista
        links_html += f"""
            <a href="{url}" 
               class="block w-full p-4 bg-[#111] border border-[#222] text-white rounded-2xl hover:bg-white hover:text-black transition-all active:scale-[0.98] font-medium text-sm flex justify-between items-center group">
                {nome}
                <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 opacity-0 group-hover:opacity-100 transition-opacity" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
                </svg>
            </a>"""

    # Formata o conteúdo final
    conteudo = TEMPLATE.format(
        cidade=cidade.upper(),
        links=links_html
    )

    # Salva o arquivo index.html na pasta da cidade
    with open(os.path.join(pasta, "index.html"), "w", encoding="utf-8") as f:
        f.write(conteudo)

    print(f"[OK] {cidade}/index.html gerado com tema minimalista")