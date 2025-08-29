import requests
from bs4 import BeautifulSoup
import csv
import requests
from io import BytesIO
from datetime import datetime
from urllib.parse import urljoin
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
    
    main()