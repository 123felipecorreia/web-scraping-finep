import requests
from bs4 import BeautifulSoup
import csv
from datetime import datetime
from urllib.parse import urljoin
from playwright.sync_api import sync_playwright

USE_PLAYWRIGHT = False  # Constantes em maiúsculo

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
            html = page.content()
            browser.close()
            return html
    except Exception as e:
        print(f"Erro ao renderizar a página com Playwright: {e}")
        return None

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
            calls.append({
                'Titulo': title,
                'Link': link,
                'Data_Coleta': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'Metodo': method
            })
            seen_links.add(link)

    return calls

def main():
    FINE_PUBLIC_CALLS_URL = 'https://www.finep.gov.br/chamadas-publicas'
    print("Iniciando coleta de Chamadas Públicas da FINEP...")

    public_calls = fetch_public_calls(FINE_PUBLIC_CALLS_URL)

    if public_calls:
        print("Chamadas Públicas Disponíveis:")
        for i, call in enumerate(public_calls, 1):
            print(f"{i}. {call['Titulo']}")
            print(f" Link: {call['Link']} (Método: {call['Metodo']})")

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