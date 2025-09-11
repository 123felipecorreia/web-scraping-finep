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
try:
    import openai
except ImportError:
    openai = None

# Configurações
USE_PLAYWRIGHT = True
USE_AI_ANALYSIS = True  # Nova configuração para análise com IA
PDF_DOWNLOAD_FOLDER = "pdfs"
os.makedirs(PDF_DOWNLOAD_FOLDER, exist_ok=True)

# Configuração da OpenAI (substitua pela sua chave)
# Para obter a chave: https://platform.openai.com/api-keys
OPENAI_API_KEY = "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"
# Nota: A configuração do cliente OpenAI agora é feita dentro da função analyze_pdf_with_ai()

def analyze_pdf_with_ai(pdf_text: str) -> dict:
    """Usa IA para extrair informações específicas do texto do PDF"""
    if not openai or OPENAI_API_KEY == "sua-chave-openai-aqui":
        print("⚠️ OpenAI não configurada. Usando análise por regex como fallback.")
        return extract_finep_pdf_data_fallback(pdf_text)
    
    try:
        # Correção: Nova sintaxe para OpenAI >= 1.0.0
        from openai import OpenAI
        client = OpenAI(api_key=OPENAI_API_KEY)
        
        # Prompt específico para análise de editais da FINEP
        prompt = f"""
        Analise o seguinte texto de um edital da FINEP e extraia as seguintes informações:

        1. Valor Global do edital (procure por valor total, recursos disponíveis, investimento)
        2. Valor máximo por projeto/proposta
        3. Prazo de submissão das propostas (data limite)
        4. Percentual de contrapartida exigida
        5. Nível TRL (Technology Readiness Level) exigido

        Texto do edital:
        {pdf_text[:4000]}  # Limita para não exceder tokens da API

        Responda EXATAMENTE no formato JSON abaixo, sem texto adicional:
        {{
            "Valor_Global": "valor encontrado ou 'Não encontrado'",
            "Valor_Projeto": "valor encontrado ou 'Não encontrado'", 
            "Prazo_Submissao": "data encontrada ou 'Não encontrado'",
            "Contrapartida": "percentual encontrado ou 'Não encontrado'",
            "Escala_TRL": "nível TRL encontrado ou 'Não encontrado'"
        }}
        """

        # Nova sintaxe da OpenAI API v1.0+
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",  # Modelo mais econômico
            messages=[
                {"role": "system", "content": "Você é um especialista em análise de editais de fomento tecnológico."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=200,
            temperature=0.1  # Baixa temperatura para respostas mais determinísticas
        )
        
        result_text = response.choices[0].message.content.strip()
        
        # Tenta fazer parse do JSON retornado pela IA
        import json
        try:
            result = json.loads(result_text)
            print("✅ Análise de IA concluída com sucesso")
            return result
        except json.JSONDecodeError:
            print("⚠️ Erro no formato JSON da IA. Usando fallback.")
            return extract_finep_pdf_data_fallback(pdf_text)
            
    except Exception as e:
        print(f"⚠️ Erro na análise de IA: {e}. Usando fallback.")
        return extract_finep_pdf_data_fallback(pdf_text)

def extract_finep_pdf_data_fallback(pdf_text: str) -> dict:
    """Método de fallback usando regex (versão original aprimorada)"""
    patterns = {
        'Valor_Global': [
            r"recursos\s*financeiros.*?(R\$\s*[\d.,]+(?:\s*(?:mil|milh[oõ]es|bilh[oõ]es))?)",
            r"valor\s*global.*?(R\$\s*[\d.,]+(?:\s*(?:mil|milh[oõ]es|bilh[oõ]es))?)",
            r"valor\s*total.*?(R\$\s*[\d.,]+(?:\s*(?:mil|milh[oõ]es|bilh[oõ]es))?)",
            r"investimento\s*total.*?(R\$\s*[\d.,]+(?:\s*(?:mil|milh[oõ]es|bilh[oõ]es))?)",
            r"recursos\s*totais.*?(R\$\s*[\d.,]+(?:\s*(?:mil|milh[oõ]es|bilh[oõ]es))?)"
        ],
        'Valor_Projeto': [
            r"valor\s*de\s*cada\s*proposta.*?(R\$\s*[\d.,]+(?:\s*(?:mil|milh[oõ]es|bilh[oõ]es))?)",
            r"valor\s*máximo\s*por\s*projeto.*?(R\$\s*[\d.,]+(?:\s*(?:mil|milh[oõ]es|bilh[oõ]es))?)",
            r"valor\s*por\s*proposta.*?(R\$\s*[\d.,]+(?:\s*(?:mil|milh[oõ]es|bilh[oõ]es))?)",
            r"limite\s*por\s*projeto.*?(R\$\s*[\d.,]+(?:\s*(?:mil|milh[oõ]es|bilh[oõ]es))?)",
            r"apoio\s*financeiro\s*por\s*proposta.*?(R\$\s*[\d.,]+(?:\s*(?:mil|milh[oõ]es|bilh[oõ]es))?)"
        ],
        'Prazo_Submissao': [
            r"período\s*de\s*submissão.*?(?:até|a)\s*(\d{1,2}[/.]\d{1,2}[/.]\d{4})",
            r"submissão\s*das\s*propostas\s*até.*?(\d{1,2}\s*de\s*\w+\s*de\s*\d{4})",
            r"envio\s*de\s*propostas\s*até.*?(\d{1,2}[/.]\d{1,2}[/.]\d{4})",
            r"prazo\s*para\s*submissão.*?(\d{1,2}[/.]\d{1,2}[/.]\d{4})",
            r"data\s*limite.*?submissão.*?(\d{1,2}[/.]\d{1,2}[/.]\d{4})",
            r"encerramento.*?(\d{1,2}[/.]\d{1,2}[/.]\d{4})",
            r"cronograma\s*de\s*submissão.*?(\d{1,2}[/.]\d{1,2}[/.]\d{4})"
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
        last_match = None
        for pattern in pattern_list:
            matches = re.findall(pattern, pdf_text, re.IGNORECASE | re.DOTALL)
            if matches:
                last_match = matches[-1]
        
        if last_match:
            extracted[key] = last_match.strip()
        else:
            extracted[key] = "Não encontrado"
    
    return extracted

def extract_finep_pdf_data(pdf_url: str) -> dict:
    """Extrai dados específicos dos PDFs da FINEP usando IA ou regex"""
    try:
        print(f"📄 Processando PDF: {pdf_url}")
        response = requests.get(pdf_url, timeout=20)
        pdf_file = BytesIO(response.content)
        
        if not PyPDF2:
            print("PyPDF2 não está instalado.")
            return {key: "Erro na extração" for key in ['Valor_Global', 'Valor_Projeto', 'Prazo_Submissao', 'Contrapartida', 'Escala_TRL']}
        
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        full_text = ""
        
        # Lê o PDF completo
        for page in pdf_reader.pages:
            text = page.extract_text()
            if text:
                full_text += text + "\n"
        
        # Escolhe o método de análise baseado na configuração
        if USE_AI_ANALYSIS:
            print("🤖 Iniciando análise com IA...")
            return analyze_pdf_with_ai(full_text)
        else:
            print("🔍 Usando análise por regex...")
            return extract_finep_pdf_data_fallback(full_text)
        
    except Exception as e:
        print(f"❌ Erro ao processar PDF: {str(e)}")
        return {key: "Erro na extração" for key in ['Valor_Global', 'Valor_Projeto', 'Prazo_Submissao', 'Contrapartida', 'Escala_TRL']}

def fetch_call_details(url: str) -> dict:
    """Obtém detalhes completos incluindo dados de PDF"""
    details = {
        'Link_PDF': '',
        'Resumo_Site': '',
        'Valor_Global': 'N/D',
        'Valor_Projeto': 'N/D', 
        'Prazo_Submissao': 'N/D',
        'Contrapartida': 'N/D',
        'Escala_TRL': 'N/D',
        'Fonte_Dados': 'Site',
        'Metodo_Analise': 'N/A'  # Novo campo para indicar o método usado
    }
    
    try:
        if USE_PLAYWRIGHT and sync_playwright:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                page.goto(url, timeout=25000)
                
                # Tenta encontrar resumo
                resumo_selectors = ['.resumo', '.abstract', '.content-text', 'p:first-of-type']
                for selector in resumo_selectors:
                    if page.query_selector(selector):
                        details['Resumo_Site'] = page.inner_text(selector)[:300] + "..."
                        break
                
                # Busca por PDFs
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
            details['Metodo_Analise'] = 'IA' if USE_AI_ANALYSIS else 'Regex'
        
        return details
        
    except Exception as e:
        print(f"❌ Erro ao processar {url}: {str(e)}")
        return details

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

    match = re.search(r'\d+', trl_string)
    if match:
        trl_level = match.group(0)
        return trl_map.get(trl_level, "Nível de TRL não classificado")
    
    return "Classificação não aplicável"

def main():
    print("🚀 Iniciando coleta avançada com análise de IA...")
    print(f"🤖 Análise com IA: {'Ativada' if USE_AI_ANALYSIS and openai else 'Desativada (usando regex)'}")
    
    # Lista de chamadas para teste
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
        print(f"   📊 TRL: {call['Escala_TRL']} ({call['TRL_Descricao']})")
        print(f"   🤖 Método: {call['Metodo_Analise']}")
        print(f"   📝 Fonte: {call['Fonte_Dados']}")
        print("-" * 60)
    
    # Salva CSV
    try:
        all_keys = set().union(*(d.keys() for d in public_calls))
        with open('chamadas_detalhadas_ia.csv', 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.DictWriter(f, fieldnames=sorted(list(all_keys)))
            writer.writeheader()
            writer.writerows(public_calls)
        print("\n✅ Dados salvos em 'chamadas_detalhadas_ia.csv'")
    except Exception as e:
        print(f"\n❌ Erro ao salvar CSV: {str(e)}")

if __name__ == '__main__':
    # Verifica e instala dependências se necessário
    try:
        import PyPDF2
    except ImportError:
        print("Instalando PyPDF2...")
        import subprocess
        subprocess.run(['pip', 'install', 'PyPDF2'])

    try:
        import openai
    except ImportError:
        print("Instalando OpenAI...")
        import subprocess
        subprocess.run(['pip', 'install', 'openai'])
    
    main()