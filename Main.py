import os
import re
import csv
import requests
from io import BytesIO
from datetime import datetime
from urllib.parse import urljoin
from bs4 import BeautifulSoup

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sync_playwright = None
try:
    import PyPDF2
except ImportError:
    PyPDF2 = None

USE_PLAYWRIGHT = False
PDF_DOWNLOAD_FOLDER = 'pdf_downloads'
os.makedirs(PDF_DOWNLOAD_FOLDER, exist_ok=True)

def extract_text_from_pdf(pdf_url: str) -> str:
    """Extrai texto de um PDF a partir de uma URL."""
    if not PyPDF2:
        print("PyPDF2 não está instalado.")
        return ""
    try:
        response = requests.get(pdf_url, timeout=15)
        response.raise_for_status()
        with BytesIO(response.content) as pdf_file:
            reader = PyPDF2.PdfReader(pdf_file)
            text = "\n".join([page.extract_text() or "" for page in reader.pages])
            return text
    except Exception as e:
        print(f"Erro ao extrair texto do PDF {pdf_url}: {e}")
        return ""

def find_pdf_links(html: str, base_url: str) -> list:
    """Encontra todos os links para PDFs em uma página HTML."""
    soup = BeautifulSoup(html, 'html.parser')
    pdf_links = []
    for link in soup.find_all('a', href=True):
        href = link['href'].lower()
        if href.endswith('.pdf'):
            full_url = urljoin(base_url, link['href'])
            pdf_links.append(full_url)
    return pdf_links

def extract_info_from_pdf_text(text: str) -> dict:
    """Extrai informações específicas do texto de PDFs."""
    info = {
        'Valor_Global_PDF': 'Informação não encontrada',
        'Prazo_Submissao_PDF': 'Informação não encontrada',
        'Contato_PDF': 'Informação não encontrada'
    }
    valor_match = re.search(r'(valor\s*total|investimento\s*total|recursos\s*disponíveis)[:\s]*R\$\s*([\d.,]+)', text, re.IGNORECASE)
    if valor_match:
        info['Valor_Global_PDF'] = f"R$ {valor_match.group(2)}"
    prazo_match = re.search(r'(prazo\s*para\s*submiss[ãa]o|envio\s*de\s*propostas)[:\s]*(\d{2}/\d{2}/\d{4})', text, re.IGNORECASE)
    if prazo_match:
        info['Prazo_Submissao_PDF'] = prazo_match.group(2)
    contato_match = re.search(r'(contato|dúvidas|informações)[:\s]*([^\n]+@[^\n]+|\(?\d{2,}\)?[\s-]?\d{4,5}[\s-]?\d{4})', text, re.IGNORECASE)
    if contato_match:
        info['Contato_PDF'] = contato_match.group(2).strip()
    return info

def fix_special_characters(text: str) -> str:
    """Corrige caracteres especiais em textos extraídos de sites brasileiros."""
    try:
        return text.encode('latin1').decode('utf-8')
    except Exception:
        return text

def fetch_with_playwright(url: str):
    """Obtém o HTML renderizado usando Playwright."""
    if not sync_playwright:
        print("Playwright não está instalado.")
        return None, {}
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(url, timeout=15000)
            page.wait_for_load_state('networkidle')
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            page.wait_for_timeout(2000)
            html = page.content()
            screenshot_path = f"screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            page.screenshot(path=screenshot_path, full_page=True)
            browser.close()
            return html, {"screenshot_path": screenshot_path}
    except Exception as e:
        print(f"Erro ao renderizar a página com Playwright: {e}")
        return None, {}

def extract_additional_details(html: str, base_url: str) -> dict:
    """Extrai detalhes adicionais de uma chamada pública."""
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
        'Conteudo_PDFs': 'Nenhum PDF encontrado'
    }
    pdf_links = find_pdf_links(html, base_url)
    details['PDFs_Encontrados'] = len(pdf_links)
    if pdf_links:
        pdf_contents = []
        for pdf_url in pdf_links[:2]:
            pdf_text = extract_text_from_pdf(pdf_url)
            if pdf_text:
                pdf_contents.append(f"PDF: {pdf_url}\nConteúdo:\n{pdf_text[:1000]}...")
                pdf_info = extract_info_from_pdf_text(pdf_text)
                details.update(pdf_info)
        if pdf_contents:
            details['Conteudo_PDFs'] = "\n\n".join(pdf_contents)
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
    for field, pattern in field_mapping.items():
        element = soup.find(string=re.compile(pattern, re.IGNORECASE))
        if element:
            next_value = element.find_next(string=True)
            if next_value and next_value != element:
                details[field] = fix_special_characters(next_value.strip())
            else:
                details[field] = fix_special_characters(element.strip())
    for field in ['Valor_Global', 'Valor_Projeto']:
        if field in details:
            match = re.search(r'R\$\s*([\d.,]+)', details[field])
            if match:
                details[field] = match.group(0)
    return details

def fetch_call_details(url: str) -> dict:
    """Obtenção de detalhes adicionais de uma chamada pública."""
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
    details.update(metadata)
    return details

def fetch_public_calls(url: str) -> list:
    """Busca e retorna uma lista de chamadas públicas disponíveis na página fornecida."""
    if USE_PLAYWRIGHT:
        html, _ = fetch_with_playwright(url)
    else:
        html = None
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
        link = urljoin(url, link_tag['href']) if link_tag else ''
        if (link and link not in seen_links and
            not link.endswith(('acessibilidade', 'chamadas-publicas')) and
            '/chamadapublica/' in link):
            call_data = {
                'Titulo': title,
                'Link': link,
                'Data_Coleta': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'Metodo': method
            }
            details = fetch_call_details(link)
            call_data.update(details)
            calls.append(call_data)
            seen_links.add(link)
            if len(calls) >= 3:
                break
    return calls

def main():
    FINE_PUBLIC_CALLS_URL = 'https://www.finep.gov.br/chamadas-publicas'
    print("Iniciando coleta de Chamadas Públicas da FINEP...")
    os.makedirs('screenshots', exist_ok=True)
    public_calls = fetch_public_calls(FINE_PUBLIC_CALLS_URL)
    if public_calls:
        print("Chamadas Públicas Disponíveis:")
        print(f"Total de Chamadas Encontradas: {len(public_calls)}\n")
        print(f"Campos coletados por chamada: {len(public_calls[0].keys())}\n")
        for i, call in enumerate(public_calls, 1):
            print(f"{i}. {call['Titulo']}")
            print(f" Link: {call['Link']} (Método: {call['Metodo']})")
            print(f"PDFs encontrados: {call['PDFs_Encontrados']}")
            print(f"   Linha Temática: {call['Linha_Tematica']}")
            print(f"   Público-Alvo: {call['Publico_Alvo']}")
            print(f"   Prazo Submissão (site): {call['Prazo_Submissao']}")
            print(f"   Prazo Submissão (PDF): {call.get('Prazo_Submissao_PDF', 'N/A')}")
            print(f"   Valor Global (site): {call['Valor_Global']}")
            print(f"   Valor Global (PDF): {call.get('Valor_Global_PDF', 'N/A')}")
            print(f"   Modalidade: {call['Modalidade']}")
            print(f"   Contato (PDF): {call.get('Contato_PDF', 'N/A')}")
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
    main()