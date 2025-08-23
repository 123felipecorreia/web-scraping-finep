<<<<<<< HEAD
import requests
from bs4 import BeautifulSoup
=======
import os
import re
>>>>>>> eef6faa96b27bc865b0eae3b3b4823edde9d22c3
import csv
import requests
from io import BytesIO
from datetime import datetime
from urllib.parse import urljoin
<<<<<<< HEAD
from playwright.sync_api import sync_playwright
import re
import io
import PyPDF2
import os

# Configurações
USE_PLAYWRIGHT = True
PDF_DOWNLOAD_FOLDER = "pdfs"
os.makedirs(PDF_DOWNLOAD_FOLDER, exist_ok=True)

def extract_finep_pdf_data(pdf_url: str) -> dict:
    """Extrai dados específicos dos PDFs da FINEP"""
    try:
        print(f"Processando PDF: {pdf_url}")
        response = requests.get(pdf_url, timeout=20)
        pdf_file = io.BytesIO(response.content)
        
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        full_text = ""
        
        # Complemento: Remove o limite de 10 páginas para ler o PDF inteiro.
        # Garante que dados em páginas posteriores não sejam perdidos.
        for page in pdf_reader.pages:
            text = page.extract_text()
            if text:
                full_text += text + "\n"
        
        # Padrões específicos para editais FINEP (EXPANDIDOS PARA MAIOR COMPATIBILIDADE)
        patterns = {
            'Valor_Global': [
                # Complemento: Adiciona novas variações de termos.
                r"recursos\s*financeiros.*?(R\$\s*[\d.,]+(?:\s*(?:mil|milh[oõ]es|bilh[oõ]es))?)",
                r"valor\s*global.*?(R\$\s*[\d.,]+(?:\s*(?:mil|milh[oõ]es|bilh[oõ]es))?)",
                r"valor\s*total.*?(R\$\s*[\d.,]+(?:\s*(?:mil|milh[oõ]es|bilh[oõ]es))?)",
                r"investimento\s*total.*?(R\$\s*[\d.,]+(?:\s*(?:mil|milh[oõ]es|bilh[oõ]es))?)",
                r"recursos\s*totais.*?(R\$\s*[\d.,]+(?:\s*(?:mil|milh[oõ]es|bilh[oõ]es))?)" # Nova variação
            ],
            'Valor_Projeto': [
                # Complemento: Adiciona novas variações de termos.
                r"valor\s*de\s*cada\s*proposta.*?(R\$\s*[\d.,]+(?:\s*(?:mil|milh[oõ]es|bilh[oõ]es))?)",
                r"valor\s*máximo\s*por\s*projeto.*?(R\$\s*[\d.,]+(?:\s*(?:mil|milh[oõ]es|bilh[oõ]es))?)",
                r"valor\s*por\s*proposta.*?(R\$\s*[\d.,]+(?:\s*(?:mil|milh[oõ]es|bilh[oõ]es))?)",
                r"limite\s*por\s*projeto.*?(R\$\s*[\d.,]+(?:\s*(?:mil|milh[oõ]es|bilh[oõ]es))?)",
                r"apoio\s*financeiro\s*por\s*proposta.*?(R\$\s*[\d.,]+(?:\s*(?:mil|milh[oõ]es|bilh[oõ]es))?)" # Nova variação
            ],
            'Prazo_Submissao': [
                # Complemento: Adiciona novas variações de termos e formatos de data.
                r"período\s*de\s*submissão.*?(?:até|a)\s*(\d{1,2}[/.]\d{1,2}[/.]\d{4})", # Padrão com "período" e aceita . ou /
                r"submissão\s*das\s*propostas\s*até.*?(\d{1,2}\s*de\s*\w+\s*de\s*\d{4})",
                r"envio\s*de\s*propostas\s*até.*?(\d{1,2}[/.]\d{1,2}[/.]\d{4})", # Aceita . ou /
                r"prazo\s*para\s*submissão.*?(\d{1,2}[/.]\d{1,2}[/.]\d{4})", # Aceita . ou /
                r"data\s*limite.*?submissão.*?(\d{1,2}[/.]\d{1,2}[/.]\d{4})", # Aceita . ou /
                r"encerramento.*?(\d{1,2}[/.]\d{1,2}[/.]\d{4})", # Aceita . ou /
                r"cronograma\s*de\s*submissão.*?(\d{1,2}[/.]\d{1,2}[/.]\d{4})" # Aceita . ou /
            ],
            'Contrapartida': [
                r"contrapartida.*?(\d+%)",
                r"contra\s*parte.*?(\d+%)",
                r"recursos.*?proponente.*?(\d+%)"
            ],
            'Escala_TRL': [
                r"nível\s*de\s*maturidade\s*tecnológica.*?TRL\s*(\d+)", # Variação comum
                r"TRL.*?(\d+\s*[aà-]\s*\d+)", # Agora aceita "a", "à" ou "-"
                r"Technology\s*Readiness\s*Level.*?(\d+)",
                r"escala\s*de\s*maturidade.*?(\d+)"
            ]
        }
        
        extracted = {}
        for key, pattern_list in patterns.items():
            last_match = None # Complemento: Variável para guardar a última correspondência
            for pattern in pattern_list:
                # Complemento: Usamos re.findall para pegar TODAS as correspondências
                matches = re.findall(pattern, full_text, re.IGNORECASE | re.DOTALL)
                if matches:
                    # Complemento: Guardamos a última correspondência encontrada
                    last_match = matches[-1]
            
            # Complemento: Atribuímos o valor da última correspondência, se houver
            if last_match:
                extracted[key] = last_match.strip()
            else:
                extracted[key] = "Não encontrado"
        
        return extracted
        
    except Exception as e:
        print(f"Erro ao processar PDF: {str(e)}")
        return {key: "Erro na extração" for key in ['Valor_Global', 'Valor_Projeto', 'Prazo_Submissao', 'Contrapartida', 'Escala_TRL']}
=======
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
>>>>>>> eef6faa96b27bc865b0eae3b3b4823edde9d22c3

def fetch_call_details(url: str) -> dict:
    """Obtém detalhes completos incluindo dados de PDF"""
    # Complemento: A chave 'Titulo' foi removida deste dicionário inicial
    # para evitar que o título original seja sobrescrito.
    details = {
        'Link_PDF': '',
        'Resumo_Site': '',
        'Valor_Global': 'N/D',
        'Valor_Projeto': 'N/D', 
        'Prazo_Submissao': 'N/D',
        'Contrapartida': 'N/D',
        'Escala_TRL': 'N/D',
        'Fonte_Dados': 'Site'
    }
    
    try:
        if USE_PLAYWRIGHT:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                page.goto(url, timeout=25000)
                
                # Complemento: A busca pelo título foi removida daqui.
                # A função agora foca apenas nos detalhes adicionais.
                
                # Tenta encontrar resumo
                resumo_selectors = ['.resumo', '.abstract', '.content-text', 'p:first-of-type']
                for selector in resumo_selectors:
                    if page.query_selector(selector):
                        details['Resumo_Site'] = page.inner_text(selector)[:300] + "..."
                        break
                
                # Busca por PDFs (padrões comuns da FINEP)
                pdf_selectors = [
                    'a[href*=".pdf"]',
                    'a:has-text("edital")',
                    'a:has-text("pdf")',
                    'a:has-text("download")'
                ]
                
                for selector in pdf_selectors:
                    pdf_elements = page.query_selector_all(selector)
                    for element in pdf_elements:
                        href = element.get_attribute('href')
                        if href and '.pdf' in href.lower():
                            details['Link_PDF'] = urljoin(url, href)
                            break
                    if details['Link_PDF']:
                        break
                
                browser.close()
        
        # Extrai dados do PDF se encontrado
        if details['Link_PDF']:
            pdf_data = extract_finep_pdf_data(details['Link_PDF'])
            details.update(pdf_data)
            details['Fonte_Dados'] = 'PDF'
        
        return details
        
    except Exception as e:
        print(f"Erro ao processar {url}: {str(e)}")
        return details

<<<<<<< HEAD
# Complemento: Nova função para classificar o TRL com base na descrição fornecida.
def classify_trl(trl_string: str) -> str:
    """Classifica o nível de TRL com base em uma string extraída."""
    
    trl_map = {
        '1': "TRL 1 - Princípios Básicos Observados",
        '2': "TRL 2 - Conceito Tecnológico Formulado",
        '3': "TRL 3 - Prova de Conceito Experimental",
        '4': "TRL 4 - Validação em Ambiente de Laboratório",
        '5': "TRL 5 - Validação em Ambiente Relevante",
        '6': "TRL 6 - Demonstração em Ambiente Relevante",
        '7': "TRL 7 - Demonstração em Ambiente Operacional",
        '8': "TRL 8 - Sistema Completo Qualificado",
        '9': "TRL 9 - Sistema Comprovado em Operação Real"
    }

    if not trl_string or "Não encontrado" in trl_string:
        return "Classificação não aplicável"

    # Extrai o primeiro número da string (ex: de "3 a 5", pega "3")
    match = re.search(r'\d+', trl_string)
    if match:
        trl_level = match.group(0)
        return trl_map.get(trl_level, "Nível de TRL não classificado")
    
    return "Classificação não aplicável"

def main():
    FINE_PUBLIC_CALLS_URL = "https://www.finep.gov.br/chamadas-publicas"
    
    print("🚀 Iniciando coleta completa com extração de PDFs...")
    
    # Sua função existente para buscar chamadas
    public_calls = [
        {
            'Titulo': 'Chamada Nordeste',
            'Link': 'https://www.finep.gov.br/chamadas-publicas/chamadapublica/759',
            'Data_Coleta': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'Metodo': 'Playwright'
        },
        {
            'Titulo': 'FIP Transição Energética e Descarbonização', 
            'Link': 'https://www.finep.gov.br/chamadas-publicas/chamadapublica/760',
            'Data_Coleta': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'Metodo': 'Playwright'
        }
    ]
    
    print(f"📋 {len(public_calls)} chamadas encontradas")
    
    # Coleta detalhes e PDFs
    for i, call in enumerate(public_calls, 1):
        print(f"\n🔍 Processando {i}/{len(public_calls)}: {call['Titulo']}")
        details = fetch_call_details(call['Link'])
        call.update(details)
        # Complemento: Adiciona a descrição do TRL ao dicionário da chamada.
        call['TRL_Descricao'] = classify_trl(call.get('Escala_TRL', 'Não encontrado'))
    
    # Exibe resultados
    print("\n" + "="*80)
    print("📊 RESULTADOS DA COLETA")
    print("="*80)
    
    for i, call in enumerate(public_calls, 1):
        print(f"\n{i}. {call['Titulo']}")
        print(f"   🔗 Link: {call['Link']}")
        print(f"   📄 PDF: {call.get('Link_PDF', 'Nenhum PDF encontrado')}")
        print(f"   💰 Valor Global: {call['Valor_Global']}")
        print(f"   💰 Valor por Projeto: {call['Valor_Projeto']}")
        print(f"   ⏰ Prazo Submissão: {call['Prazo_Submissao']}")
        print(f"   🔄 Contrapartida: {call['Contrapartida']}")
        # Complemento: Exibe o TRL numérico e sua descrição.
        print(f"   📊 TRL: {call['Escala_TRL']} ({call['TRL_Descricao']})")
        print(f"   📝 Fonte: {call['Fonte_Dados']}")
        print("-" * 60)
    
    # Salva CSV
    try:
        # Complemento: Garante que a nova coluna 'TRL_Descricao' seja incluída no CSV.
        all_keys = set().union(*(d.keys() for d in public_calls))
        with open('chamadas_detalhadas.csv', 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.DictWriter(f, fieldnames=sorted(list(all_keys)))
            writer.writeheader()
            writer.writerows(public_calls)
        print("\n✅ Dados salvos em 'chamadas_detalhadas.csv'")
    except Exception as e:
        print(f"\n❌ Erro ao salvar CSV: {str(e)}")

if __name__ == '__main__':
    # Instala dependências se necessário
    try:
        import PyPDF2
    except ImportError:
        import subprocess
        subprocess.run(['pip', 'install', 'PyPDF2'])
    
=======
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
>>>>>>> eef6faa96b27bc865b0eae3b3b4823edde9d22c3
    main()