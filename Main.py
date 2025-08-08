import requests
import re
from bs4 import BeautifulSoup
import csv
from datetime import datetime
from urllib.parse import urljoin
from playwright.sync_api import sync_playwright
from io import BytesIO
import os
import PyPDF2

USE_PLAYWRIGHT = False  # Constantes em maiúsculo
PDF_DOWNLOAD_FOLDER = 'pdf_downloads'  # Pasta para downloads de PDFs
os.makedirs(PDF_DOWNLOAD_FOLDER, exist_ok=True)  # Cria a pasta se não existir


def extract_text_from_pdf(pdf_url: str) -> str:
    """Extrai texto de um PDF a partir de uma URL"""
    try:
        response = requests.get(pdf_url, timeout=15)
        response.raise_for_status()
        
        with BytesIO(response.content) as pdf_file:
            reader = PyPDF2.PdfReader(pdf_file)
            text = "\n".join([page.extract_text() for page in reader.pages])
            return text
    except Exception as e:
        print(f"Erro ao extrair texto do PDF {pdf_url}: {e}")
        return ""
    
def find_pdf_links(html: str, base_url: str) -> list:
    """Encontra todos os links para PDFs em uma página HTML"""
    soup = BeautifulSoup(html, 'html.parser')
    pdf_links = []
    
    for link in soup.find_all('a', href=True):
        href = link['href'].lower()
        if href.endswith('.pdf'):
            full_url = urljoin(base_url, link['href'])
            pdf_links.append(full_url)
    
    return pdf_links

def fix_special_characters(text: str) -> str:
    """Corrige caracteres especiais em textos extraídos de sites brasileiros."""
    try:
        return text.encode('latin-1').decode('utf-8')
    except (UnicodeEncodeError, UnicodeDecodeError):
        try:
            return text.encode('utf-8').decode('utf-8')
        except UnicodeDecodeError:
            return text.encode('utf-8', errors='replace').decode('utf-8')

def fetch_with_playwright(url: str) -> str | None:
    """Obtém o HTML renderizado usando Playwright."""
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(url, timeout=15000)
            page.wait_for_load_state('networkidle')

            #Rolamento da página para carregar conteúdo dinâsmico
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            page.wait_for_timeout(2000)  # Espera 2 segundos para garantir que o conteúdo dinâmico seja carregado
            html = page.content()
            screenchot_path = f"screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            page.screenshot(path=screenchot_path, full_page=True)
            browser.close()


            return html, {"screenshot_path": screenchot_path}
    except Exception as e:
        print(f"Erro ao renderizar a página com Playwright: {e}")
        return None
    
def extract_additional_details (html: str, base_url: str) -> dict:
    """Extrai detalhes adicionais de uma chamada pública, como descrição e data de publicação.
    """
    soup = BeautifulSoup(html, 'html.parser')
    details = {
        'Linha_Tematica': 'Não informado',
        'Publico_Alvo': 'Não informado',
        'Prazo_Cadastro': 'Não informado',
        'Prazo_Submissao': 'Não informado',
        'Prazo_Execucao': 'Não informado',
        'Valor_Global': 'Não informado',
        'Valor_Projeto': 'Não informado',
        'Escala_TRL': 'Não informado',
        'Contrapartida': 'Não informado',
        'Observacoes': 'Não informado',
        'Resumo': 'Não informado',
        'Modalidade': 'Não informado',
        'Link_Completo': base_url,
        'PDFs_Encontrados': 0,
        'Conteudo_PDF': 'Nenhum PDF encontrado'
    }
    # Primeiro busca por PDFs na página
    pdf_links = find_pdf_links(html, base_url)
    details['PDFs_Encontrados'] = len(pdf_links)
    
    if pdf_links:
        pdf_contents = []
        for pdf_url in pdf_links[:2]:  # Limita a 2 PDFs para não sobrecarregar
            pdf_text = extract_text_from_pdf(pdf_url)
            if pdf_text:
                pdf_contents.append(f"PDF: {pdf_url}\nConteúdo:\n{pdf_text[:1000]}...")  # Limita a 1000 caracteres
        
        if pdf_contents:
            details['Conteudo_PDFs'] = "\n\n".join(pdf_contents)

    #Mapeamento de campos para padrões de busca
    field_mapping = {
        'Linha_Tematica': r'linha\s*tem[áa]tica|área\s*tem[áa]tica',
        'Publico_Alvo': r'público[\-\s]alvo|destinatários',
        'Prazo_Cadastro': r'prazo\s*para\s*cadastro|registro',
        'Prazo_Submissao': r'prazo\s*para\s*submiss[ãa]o|envio',
        'Prazo_Execucao': r'prazo\s*para\s*execu[çc][ãa]o|implementa[çc][ãa]o',
        'Valor_Global': r'valor\s*global|investimento\s*total',
        'Valor_Projeto': r'valor\s*por\s*projeto|financiamento\s*individual',
        'Escala_TRL': r'escala\s*trl|technology\s*readiness\s*level',
        'Contrapartida': r'contrapartida|contra\s*parte',
        'Observacoes': r'observa[çc][õo]es|notas',
        'Resumo': r'resumo|objetivo\s*geral',
        'Modalidade': r'modalidade|tipo\s*de\s*chamada'
    }

    for field, pattern in field_mapping.items ():
        element = soup.find(string=re.compile(pattern, re.IGNORECASE))
        if element:
            # Pega o próximo elemento que provavelmente contém o valor
            value = element.find_next(string = True)
            details [field] = fix_special_characters (value.strip()) if value else 'Encontrado, mas sem valor específico'

    #Tratamento para valores financeiros
    money_fields = ['Valor_Global', 'Valor_Projeto']
    for field in money_fields:
        if field in details:
            match = re.search(r'R\$\s*([\d.,]+)', details[field])
            details [field] = match.group(0) if match else details [field]

    return details

def fetch_call_details(url: str) -> dict:
    "Obtenção de detalhes adicionais de uma chamada pública."

    if USE_PLAYWRIGHT:
        html, metadata = fetch_with_playwright(url)

    else:
        try:
            response = requests.get(url, timeout=15)
            response.encoding = 'iso-8859-1'
            html = response.text
            metadata = {}
        except Exception as e:
            print(f"Erro ao obter dados com requests: {e}")
            return {}
    if not html:
        print(f"Erro ao obter HTML da URL: {url}")
        return {}
    details = extract_additional_details(html, url)
    details.update (metadata)
    return details


def fetch_public_calls(url: str) -> list[dict]:
    """
    Busca e retorna uma lista de chamadas públicas disponíveis na página fornecida.
    """
    html = fetch_with_playwright(url) if USE_PLAYWRIGHT else None

    if html:
        soup = BeautifulSoup(html, 'html.parser')
        method = 'Playwright'
    else:
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7'
            }
            response = requests.get(url, headers=headers, timeout=15)
            response.encoding = 'iso-8859-1'
            soup = BeautifulSoup(response.text, 'html.parser')
            method = 'Requests'
        except Exception as e:
            print(f"Erro ao obter dados com requests: {e}")
            return []

    containers = soup.select('.item-chamada, .chamada-item, article, div.card') or \
                 soup.find_all(['div', 'section'], class_=True)

    calls = []
    seen_links = set()
    for container in containers:
        title_tag = container.find(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
        if not title_tag:
            continue

        title = fix_special_characters(title_tag.get_text(strip=True))
        link_tag = container.find('a', href=True)
        if link_tag:
            link = urljoin(url, link_tag['href'])
        else:
            link = ''

        # Filtro para remover links genéricos e duplicados
        if (link and link not in seen_links and
            not link.endswith(('acessibilidade', 'chamadas-publicas')) and
            '/chamadapublica/' in link):
            call_data = {
                'Titulo': title,
                'Link': link,
                'Data_Coleta': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'Metodo': 'Playwright' if USE_PLAYWRIGHT else 'Requests'
            }

            # Obtenção de detalhes adicionais
            details = fetch_call_details(link)
            call_data.update(details)

            calls.append(call_data)
            seen_links.add(link)

            #Limita a 3 chamadas para teste
            if len(calls) >= 3:
                break

    return calls

def main():
    FINE_PUBLIC_CALLS_URL = 'https://www.finep.gov.br/chamadas-publicas'
    print("Iniciando coleta de Chamadas Públicas da FINEP...")

    #configuração Inicial

    import os
    os.makedirs('screenshots', exist_ok=True)

    public_calls = fetch_public_calls(FINE_PUBLIC_CALLS_URL)

    if public_calls:
        print("Chamadas Públicas Disponíveis:")
        print(f"Total de Chamadas Encontradas: {len(public_calls)}\n")
        print(f"Campos coletados por chamada: {len(public_calls[0].keys())}\n")

        #Exibe preview dos dados coletados
        for i, call in enumerate(public_calls, 1):
            print(f"{i}. {call['Titulo']}")
            print(f" Link: {call['Link']} (Método: {call['Metodo']})")
            print(f"PDFs encontrados: {call['PDFs_Encontrados']}")

        #Salvando os dados em CSV

        try:
            with open('chamadas_publicas.csv', 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.DictWriter(f, fieldnames=public_calls[0].keys())
                writer.writeheader()
                writer.writerows(public_calls)
            print("\n✅ Dados salvos em 'chamadas_publicas.csv'")
        except Exception as e:
            print(f"\n⚠️ Erro ao salvar CSV: {str(e)}")
    else:
        print("Nenhuma chamada pública encontrada.")

if __name__ == '__main__':
    try:
        import playwright
    except ImportError:
        import subprocess
        import sys
        subprocess.check_call([sys.executable, "-m", "pip", "install", "playwright"])
        subprocess.check_call(["playwright", "install"])
        subprocess.check_call(["playwright", "install-deps"])
    main()