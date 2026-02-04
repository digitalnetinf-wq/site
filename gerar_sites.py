import os

DOMINIO = "https://dirpinfsa.com.br"
BASE = os.path.dirname(os.path.abspath(__file__))

TEMPLATE = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<title>{cidade} :: DIRPINFSA</title>
<script src="https://cdn.tailwindcss.com"></script>
</head>

<body class="bg-black text-green-400 font-mono min-h-screen p-10">

<h1 class="text-3xl mb-6 tracking-widest">{cidade}</h1>
<p class="mb-10 text-green-600">LISTA DE SITES AUTORIZADOS</p>

<div class="grid gap-4 max-w-xl">
{links}
</div>

</body>
</html>
"""

for cidade in os.listdir(BASE):
    pasta = os.path.join(BASE, cidade)

    if not os.path.isdir(pasta):
        continue
    if cidade.startswith("."):
        continue

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
        links_html += f"""
<a href="{url}"
 class="block border border-green-500 p-4 hover:bg-green-500 hover:text-black transition">
 {nome}
</a>
"""

    conteudo = TEMPLATE.format(
        cidade=cidade.upper(),
        links=links_html
    )

    with open(os.path.join(pasta, "index.html"), "w", encoding="utf-8") as f:
        f.write(conteudo)

    print(f"[OK] {cidade}/index.html gerado")
