import requests
from bs4 import BeautifulSoup
import csv
from datetime import datetime
from urllib.parse import urljoin


def fix_special_characters (text: str) -> str:
    #Correção dos caracteres especiais

    try:
        # Codificação via latin-1 (iso-8859-1), padrão de sites brasileiros
        return text.encode('latin-1').decode('utf-8')
    except (UnicodeEncodeError, UnicodeDecodeError):

        try:
            return text.encode('utf-8').decode('utf-8')
        except UnicodeDecodeError:
            return text.encode ('utf-8', errors = 'replace').decode ('utf-8')

    
    

    

def fetch_public_calls(url: str) -> list[dict]:
    """
    Fetch and return titles of public calls from FINEP website.
    
    Args:
        url: URL of the public calls page
        
    Returns:
        List of public call titles
    """
    try:
        # Configura headers tpara simular a requisição do navegador
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7'
        }
        
        # Faz a requisição com timeout e tratamento de erros
        response = requests.get(url, headers=headers, timeout=15)
        response.encoding = 'iso-8859-1' # Ensure correct encoding
        
        
        # Parseia  o conteúdo HTML
        soup = BeautifulSoup(response.text, 'html.parser')

        containers = soup.select('.item-chamada, .chamada-item, article, div.card') or \
                   soup.find_all(['div', 'section'], class_=True)

        
        
        # Extrai e limpa os títulos com tratamento especial para caracteres
        calls = []
        seen_links = set()
        for container in containers:
            title_tag = container.find(['h1','h2','h3', 'h4', 'h5', 'h6'])
            if not title_tag:
                continue
            
            #correção do link
            title = fix_special_characters (title_tag.get_text (strip = True))
            link_tag = container.find ('a', href = True)
            link = urljoin (url,link_tag ['href']) if link_tag else ''

            
            

            if link_tag:
                link = link_tag ['href'] if link_tag ['href'] .startswith ('http') else f"{url.rstrip('/')}/{link_tag['href'].lstrip('/')}"

            else:
                link = '' \
                ''
            #Filtro para remover link generico
            if (link not in seen_links and not link.endswith (('acessibilidade', 'chamadas-publicas')) and '/chamadapublica/'in link):            
                calls.append({
                    'Titulo': title,
                    'Link': link,
                    'Data_Coleta': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                })
                seen_links.add(link)

        return calls


    except requests.exceptions.RequestException as e:
        print(f"Erro ao obter dados {e}")
        return []

def main():
    # Constants should be in uppercase
    FINE_PUBLIC_CALLS_URL = 'https://www.finep.gov.br/chamadas-publicas'

    print("Iniciando coleta de Chamadas Públicas da FINEP...")
    
    public_calls = fetch_public_calls(FINE_PUBLIC_CALLS_URL)
    
    if public_calls:
        print("Chamadas Públicas Disponíveis:")
        for i, call in enumerate(public_calls, 1):
            print(f"{i}. {call}")
            if call ['Link']:
                print (f" Link: {call ['Link']}")
    else:
        print("Sem chamadas públicas Disponíveis ou erro.")

    # Save to CSV

    try:
        with open('chamadas_publicas.csv', 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.DictWriter(f, fieldnames=public_calls[0].keys())
            writer.writeheader()
            writer.writerows(public_calls)
        print("\n✅ Dados salvos em 'chamadas_publicas.csv'")
    except Exception as e:
        print(f"\n⚠️ Erro ao salvar CSV: {str(e)}")

if __name__ == '__main__':
    main()