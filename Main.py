import os
import csv
import requests
from bs4 import BeautifulSoup
from io import BytesIO
from datetime import datetime
from urllib.parse import urljoin
import json
import re
import glob

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sync_playwright = None
try:
    import PyPDF2
except ImportError:
    PyPDF2 = None
try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

# Configurações
USE_PLAYWRIGHT = True
PDF_DOWNLOAD_FOLDER = "pdfs"
os.makedirs(PDF_DOWNLOAD_FOLDER, exist_ok=True)

# Configuração da OpenAI
OPENAI_API_KEY = "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"

def cleanup_old_files():
    """Remove planilhas antigas do projeto"""
    try:
        # Padrões de arquivos para remover
        patterns = [
            'FINEP_Chamadas_Publicas_*.csv',
            'finep_*.csv',
            'chamadas_*.csv'
        ]
        
        files_removed = 0
        for pattern in patterns:
            files = glob.glob(pattern)
            for file in files:
                try:
                    os.remove(file)
                    files_removed += 1
                    print(f"   🗑️ Removido: {file}")
                except Exception as e:
                    print(f"   ⚠️ Não foi possível remover {file}: {e}")
        
        if files_removed > 0:
            print(f"✅ {files_removed} arquivo(s) antigo(s) removido(s)")
        else:
            print("ℹ️ Nenhum arquivo antigo encontrado")
            
    except Exception as e:
        print(f"⚠️ Erro na limpeza de arquivos: {e}")

def safe_json_parse(text: str, debug=False) -> dict:
    """Parse JSON com tratamento robusto de erros"""
    if debug:
        print(f"🔍 Tentativa de parse JSON: {text[:200]}...")
    
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        pass
    
    try:
        json_match = re.search(r'\{.*\}', text, re.DOTALL)
        if json_match:
            json_text = json_match.group(0)
            return json.loads(json_text)
    except json.JSONDecodeError:
        pass
    
    try:
        result = {}
        patterns = {
            'Valor_Global': r'"?Valor_Global"?\s*:\s*"([^"]*)"',
            'Valor_Projeto': r'"?Valor_Projeto"?\s*:\s*"([^"]*)"',
            'Prazo_Submissao': r'"?Prazo_Submissao"?\s*:\s*"([^"]*)"',
            'Contrapartida': r'"?Contrapartida"?\s*:\s*"([^"]*)"',
            'Escala_TRL': r'"?Escala_TRL"?\s*:\s*"([^"]*)"'
        }
        
        for key, pattern in patterns.items():
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                result[key] = match.group(1)
            else:
                result[key] = "Não encontrado"
        
        if any(v != "Não encontrado" for v in result.values()):
            return result
            
    except Exception as e:
        pass
    
    return {
        'Valor_Global': "Não encontrado",
        'Valor_Projeto': "Não encontrado",
        'Prazo_Submissao': "Não encontrado",
        'Contrapartida': "Não encontrado",
        'Escala_TRL': "Não encontrado"
    }

def split_text_intelligently(text: str, max_length: int = 8000) -> list:
    """Divide texto em chunks"""
    if len(text) <= max_length:
        return [text]
    
    sections = text.split('\n\n')
    chunks = []
    current_chunk = ""
    
    for section in sections:
        if len(current_chunk + section) < max_length:
            current_chunk += section + "\n\n"
        else:
            if current_chunk:
                chunks.append(current_chunk.strip())
            current_chunk = section + "\n\n"
    
    if current_chunk:
        chunks.append(current_chunk.strip())
    
    return chunks if chunks else [text[:max_length]]

def analyze_website_content_with_ai(html_content: str, url: str) -> dict:
    """Analisa conteúdo do site"""
    if not OpenAI or not OPENAI_API_KEY:
        return {}
    
    try:
        client = OpenAI(api_key=OPENAI_API_KEY)
        
        soup = BeautifulSoup(html_content, 'html.parser')
        for script in soup(["script", "style"]):
            script.decompose()
            
        text_content = soup.get_text(separator=' ', strip=True)
        text_sample = text_content[:6000] if len(text_content) > 6000 else text_content
        
        prompt = f"""
        Analise esta página da FINEP:
        
        {text_sample}
        
        Extraia apenas o título da chamada pública. Responda EXATAMENTE assim:
        {{"titulo": "título encontrado ou Não encontrado"}}
        """
        
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Retorne apenas JSON válido."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=100,
            temperature=0.1
        )
        
        result = safe_json_parse(response.choices[0].message.content.strip())
        if result and 'titulo' in result:
            titulo = result['titulo']
            if titulo != "Não encontrado":
                print(f"   📋 Título extraído: {titulo}")
            else:
                print("   ⚠️ Título não identificado no site")
            return result
        
        return {}
        
    except Exception as e:
        print(f"   ❌ Erro na análise do site: {e}")
        return {}

def find_pdf_links_simple(html_content: str, base_url: str) -> list:
    """Busca PDFs"""
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        pdf_links = []
        
        for a_tag in soup.find_all('a', href=True):
            href = a_tag.get('href')
            if href and '.pdf' in href.lower():
                full_url = urljoin(base_url, href)
                text = a_tag.get_text(strip=True)
                pdf_links.append({
                    'url': full_url,
                    'text': text
                })
        
        if pdf_links:
            def priority_score(link):
                text_lower = link['text'].lower()
                keywords = ['edital', 'chamada', 'regulamento']
                return sum(1 for k in keywords if k in text_lower)
            
            pdf_links.sort(key=priority_score, reverse=True)
            
            print(f"   📎 {len(pdf_links)} PDFs encontrados:")
            for i, link in enumerate(pdf_links[:3], 1):
                print(f"      {i}. {link['text'][:50]}...")
            
            return [link['url'] for link in pdf_links[:2]]  # Só os 2 principais
        
        print("   ⚠️ Nenhum PDF encontrado")
        return []
        
    except Exception as e:
        print(f"   ❌ Erro na busca de PDFs: {e}")
        return []

def analyze_pdf_with_ai_robust(pdf_text: str) -> dict:
    """Análise de PDF otimizada"""
    if not OpenAI or not OPENAI_API_KEY:
        return {
            'Valor_Global': "IA não disponível",
            'Valor_Maximo_Por_Projeto': "IA não disponível",
            'Data_Limite_Submissao': "IA não disponível",
            'Percentual_Contrapartida': "IA não disponível",
            'Nivel_TRL_Exigido': "IA não disponível"
        }
    
    try:
        client = OpenAI(api_key=OPENAI_API_KEY)
        
        text_chunks = split_text_intelligently(pdf_text, 6000)
        print(f"   📖 Analisando {len(text_chunks)} seções do PDF...")
        
        all_results = []
        informacoes_encontradas = []  # Para mostrar o progresso
        
        for i, chunk in enumerate(text_chunks, 1):
            print(f"      📄 Seção {i}/{len(text_chunks)}...", end=" ")
            
            prompt = f"""
            Analise este trecho de edital FINEP e encontre as informações específicas:
            
            {chunk}
            
            Procure por:
            1. VALOR GLOBAL: Total de recursos da chamada (ex: R$ 10 milhões, R$ 500.000.000,00)
            2. VALOR MÁXIMO POR PROJETO: Limite por proposta individual
            3. DATA LIMITE: Prazo final para submissão (formato DD/MM/AAAA ou DD.MM.AAAA)
            4. CONTRAPARTIDA: Percentual que o proponente deve investir (ex: 8%, 1%)
            5. TRL: Nível de maturidade tecnológica exigido
            
            RESPONDA APENAS neste JSON exato:
            {{"Valor_Global": "valor ou Não encontrado", "Valor_Maximo_Por_Projeto": "valor ou Não encontrado", "Data_Limite_Submissao": "data ou Não encontrado", "Percentual_Contrapartida": "percentual ou Não encontrado", "Nivel_TRL_Exigido": "TRL ou Não encontrado"}}
            """

            try:
                response = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": "Retorne APENAS JSON válido."},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=150,
                    temperature=0.05
                )
                
                ai_response = response.choices[0].message.content.strip()
                
                # Parse personalizado para os novos campos
                result = {}
                patterns = {
                    'Valor_Global': r'"?Valor_Global"?\s*:\s*"([^"]*)"',
                    'Valor_Maximo_Por_Projeto': r'"?Valor_Maximo_Por_Projeto"?\s*:\s*"([^"]*)"',
                    'Data_Limite_Submissao': r'"?Data_Limite_Submissao"?\s*:\s*"([^"]*)"',
                    'Percentual_Contrapartida': r'"?Percentual_Contrapartida"?\s*:\s*"([^"]*)"',
                    'Nivel_TRL_Exigido': r'"?Nivel_TRL_Exigido"?\s*:\s*"([^"]*)"'
                }
                
                for key, pattern in patterns.items():
                    match = re.search(pattern, ai_response, re.IGNORECASE)
                    if match:
                        result[key] = match.group(1)
                    else:
                        result[key] = "Não encontrado"
                
                # Mostra informações encontradas nesta seção
                found_info = []
                for key, value in result.items():
                    if value != "Não encontrado":
                        found_info.append(f"{key}: {value}")
                
                if found_info:
                    all_results.append(result)
                    print("✅")
                    for info in found_info:
                        informacoes_encontradas.append(info)
                        print(f"         🎯 {info}")
                else:
                    print("❌")
                    
            except Exception as e:
                print(f"❌ ({str(e)[:30]})")
                continue
        
        print(f"\n   📊 INFORMAÇÕES EXTRAÍDAS DO PDF:")
        if informacoes_encontradas:
            for info in set(informacoes_encontradas):  # Remove duplicatas
                print(f"      ✅ {info}")
        else:
            print("      ⚠️ Nenhuma informação específica extraída")
        
        # Consolida resultados
        if all_results:
            consolidated = {
                'Valor_Global': "Não encontrado",
                'Valor_Maximo_Por_Projeto': "Não encontrado",
                'Data_Limite_Submissao': "Não encontrado",
                'Percentual_Contrapartida': "Não encontrado",
                'Nivel_TRL_Exigido': "Não encontrado"
            }
            
            for key in consolidated.keys():
                for result in all_results:
                    if key in result and result[key] != "Não encontrado":
                        consolidated[key] = result[key]
                        break
            
            print(f"\n   🎯 RESULTADO CONSOLIDADO:")
            for key, value in consolidated.items():
                status = "✅" if value != "Não encontrado" else "❌"
                print(f"      {status} {key}: {value}")
            
            return consolidated
        else:
            print(f"\n   ⚠️ Nenhum resultado consolidado obtido")
            return {
                'Valor_Global': "Não extraído",
                'Valor_Maximo_Por_Projeto': "Não extraído",
                'Data_Limite_Submissao': "Não extraído",
                'Percentual_Contrapartida': "Não extraído",
                'Nivel_TRL_Exigido': "Não extraído"
            }
            
    except Exception as e:
        print(f"\n   ❌ Erro geral na análise: {e}")
        return {
            'Valor_Global': f"Erro: {str(e)[:50]}",
            'Valor_Maximo_Por_Projeto': "Erro na análise",
            'Data_Limite_Submissao': "Erro na análise",
            'Percentual_Contrapartida': "Erro na análise", 
            'Nivel_TRL_Exigido': "Erro na análise"
        }

def extract_pdf_text(pdf_url: str) -> str:
    """Extrai texto do PDF"""
    try:
        print(f"   📥 Baixando PDF...")
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(pdf_url, timeout=60, headers=headers)
        response.raise_for_status()
        
        pdf_file = BytesIO(response.content)
        
        if not PyPDF2:
            print("   ❌ PyPDF2 não disponível")
            return ""
        
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        num_pages = len(pdf_reader.pages)
        
        print(f"   📖 Extraindo texto de {num_pages} páginas...")
        
        full_text = ""
        successful_pages = 0
        
        for page_num, page in enumerate(pdf_reader.pages, 1):
            try:
                text = page.extract_text()
                if text and text.strip():
                    text = re.sub(r'\s+', ' ', text.strip())
                    full_text += f"\n{text}"
                    successful_pages += 1
                    
                    if page_num % 10 == 0:
                        print(f"      📄 {page_num} páginas processadas...")
            except:
                continue
        
        print(f"   ✅ Texto extraído: {successful_pages}/{num_pages} páginas ({len(full_text):,} caracteres)")
        return full_text
        
    except Exception as e:
        print(f"   ❌ Erro na extração: {e}")
        return ""

def process_call(url: str, titulo_inicial: str) -> dict:
    """Processa uma chamada específica"""
    print(f"\n🔍 PROCESSANDO: {titulo_inicial}")
    print(f"🔗 URL: {url}")
    print("-" * 60)
    
    result = {
        'ID': titulo_inicial,
        'Nome_da_Chamada': 'Não identificado',
        'URL_Original': url,
        'Valor_Global_Disponivel': 'Não encontrado',
        'Valor_Maximo_Por_Projeto': 'Não encontrado',
        'Data_Limite_Submissao': 'Não encontrado',
        'Percentual_Contrapartida': 'Não encontrado',
        'Nivel_TRL_Exigido': 'Não encontrado',
        'URL_PDF_Principal': 'Não encontrado',
        'Status_Processamento': 'Iniciando',
        'Data_Coleta': datetime.now().strftime('%d/%m/%Y %H:%M')
    }
    
    try:
        # Passo 1: Acessa página
        print("🌐 Acessando página web...")
        html_content = ""
        if USE_PLAYWRIGHT and sync_playwright:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                page.goto(url, timeout=45000, wait_until='networkidle')
                html_content = page.content()
                browser.close()
                print("   ✅ Página carregada com sucesso")
        
        if not html_content:
            result['Status_Processamento'] = 'Erro - Página inacessível'
            print("   ❌ Falha no carregamento da página")
            return result
        
        # Passo 2: Extrai título
        print("\n🤖 Analisando conteúdo do site...")
        site_analysis = analyze_website_content_with_ai(html_content, url)
        if site_analysis and site_analysis.get('titulo') != 'Não encontrado':
            result['Nome_da_Chamada'] = site_analysis['titulo']
        
        # Passo 3: Busca PDFs
        print("\n🔍 Buscando documentos PDF...")
        pdf_urls = find_pdf_links_simple(html_content, url)
        if not pdf_urls:
            result['Status_Processamento'] = 'Concluído - Sem PDFs relevantes'
            print("   ⚠️ Nenhum PDF relevante encontrado")
            return result
        
        # Passo 4: Analisa PDF principal
        main_pdf = pdf_urls[0]
        result['URL_PDF_Principal'] = main_pdf
        
        print(f"\n📋 Analisando PDF principal:")
        print(f"   🔗 {main_pdf.split('/')[-1]}")
        
        pdf_text = extract_pdf_text(main_pdf)
        if not pdf_text:
            result['Status_Processamento'] = 'Erro - PDF não legível'
            print("   ❌ Não foi possível ler o PDF")
            return result
        
        # Passo 5: Análise com IA
        print(f"\n🤖 ANÁLISE INTELIGENTE DO PDF:")
        pdf_data = analyze_pdf_with_ai_robust(pdf_text)
        
        result['Valor_Global_Disponivel'] = pdf_data['Valor_Global']
        result['Valor_Maximo_Por_Projeto'] = pdf_data['Valor_Maximo_Por_Projeto']
        result['Data_Limite_Submissao'] = pdf_data['Data_Limite_Submissao']
        result['Percentual_Contrapartida'] = pdf_data['Percentual_Contrapartida']
        result['Nivel_TRL_Exigido'] = pdf_data['Nivel_TRL_Exigido']
        
        result['Status_Processamento'] = 'Concluído com sucesso'
        
        print(f"\n✅ PROCESSAMENTO CONCLUÍDO")
        
        return result
        
    except Exception as e:
        result['Status_Processamento'] = f'Erro - {str(e)[:100]}'
        print(f"\n❌ Erro no processamento: {e}")
        return result

def clean_csv_data(value: str) -> str:
    """Limpa dados para CSV removendo caracteres problemáticos"""
    if not isinstance(value, str):
        return str(value)
    
    # Remove quebras de linha e tabs
    value = value.replace('\n', ' ').replace('\r', ' ').replace('\t', ' ')
    
    # Remove vírgulas extras que podem quebrar o CSV
    value = re.sub(r',+', ',', value)
    
    # Remove espaços extras
    value = re.sub(r'\s+', ' ', value).strip()
    
    # Limita o tamanho para evitar células muito grandes
    if len(value) > 500:
        value = value[:497] + "..."
    
    return value

def save_to_csv(resultados: list, filename: str) -> bool:
    """Salva resultados em CSV com formatação adequada"""
    try:
        # Ordem específica das colunas
        fieldnames = [
            'ID',
            'Nome_da_Chamada',
            'Valor_Global_Disponivel',
            'Valor_Maximo_Por_Projeto', 
            'Data_Limite_Submissao',
            'Percentual_Contrapartida',
            'Nivel_TRL_Exigido',
            'URL_PDF_Principal',
            'URL_Original',
            'Status_Processamento',
            'Data_Coleta'
        ]
        
        # Limpa os dados antes de salvar
        cleaned_resultados = []
        for resultado in resultados:
            cleaned_resultado = {}
            for field in fieldnames:
                raw_value = resultado.get(field, 'N/A')
                cleaned_resultado[field] = clean_csv_data(str(raw_value))
            cleaned_resultados.append(cleaned_resultado)
        
        # Salva com configurações específicas para CSV
        with open(filename, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.DictWriter(
                f, 
                fieldnames=fieldnames,
                delimiter=',',           # Vírgula como separador
                quotechar='"',          # Aspas duplas para campos com vírgulas
                quoting=csv.QUOTE_ALL   # Força aspas em todos os campos
            )
            writer.writeheader()
            writer.writerows(cleaned_resultados)
        
        print(f"💾 PLANILHA SALVA: {filename}")
        print(f"📊 {len(cleaned_resultados)} registros salvos com {len(fieldnames)} colunas")
        
        # Verifica se o arquivo foi criado corretamente
        if os.path.exists(filename):
            file_size = os.path.getsize(filename)
            print(f"📁 Tamanho do arquivo: {file_size:,} bytes")
            return True
        else:
            print("❌ Erro: arquivo não foi criado")
            return False
            
    except Exception as e:
        print(f"❌ Erro ao salvar CSV: {e}")
        return False

def create_excel_version(resultados: list, csv_filename: str) -> None:
    """Cria versão Excel opcional (se xlsxwriter disponível)"""
    try:
        import xlsxwriter
        
        excel_filename = csv_filename.replace('.csv', '.xlsx')
        
        workbook = xlsxwriter.Workbook(excel_filename)
        worksheet = workbook.add_worksheet('Chamadas FINEP')
        
        # Formatos
        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#4F81BD',
            'font_color': 'white',
            'border': 1
        })
        
        cell_format = workbook.add_format({
            'border': 1,
            'text_wrap': True,
            'valign': 'top'
        })
        
        # Headers
        headers = [
            'ID', 'Nome da Chamada', 'Valor Global', 'Valor Máximo/Projeto',
            'Data Limite', 'Contrapartida (%)', 'Nível TRL', 'PDF Principal',
            'URL Original', 'Status', 'Data Coleta'
        ]
        
        for col, header in enumerate(headers):
            worksheet.write(0, col, header, header_format)
            worksheet.set_column(col, col, 20)  # Largura da coluna
        
        # Dados
        for row, resultado in enumerate(resultados, 1):
            values = [
                resultado.get('ID', ''),
                resultado.get('Nome_da_Chamada', ''),
                resultado.get('Valor_Global_Disponivel', ''),
                resultado.get('Valor_Maximo_Por_Projeto', ''),
                resultado.get('Data_Limite_Submissao', ''),
                resultado.get('Percentual_Contrapartida', ''),
                resultado.get('Nivel_TRL_Exigido', ''),
                resultado.get('URL_PDF_Principal', ''),
                resultado.get('URL_Original', ''),
                resultado.get('Status_Processamento', ''),
                resultado.get('Data_Coleta', '')
            ]
            
            for col, value in enumerate(values):
                clean_value = clean_csv_data(str(value))
                worksheet.write(row, col, clean_value, cell_format)
        
        workbook.close()
        print(f"📊 Versão Excel criada: {excel_filename}")
        
    except ImportError:
        print("ℹ️ xlsxwriter não disponível - apenas CSV gerado")
    except Exception as e:
        print(f"⚠️ Erro ao criar Excel: {e}")

def get_user_links() -> list:
    """Permite ao usuário registrar links para análise"""
    print("\n📋 CONFIGURAÇÃO DE LINKS PARA ANÁLISE")
    print("="*50)
    
    # Links padrão já configurados
    links_default = [
        {
            'titulo': 'Chamada Nordeste',
            'url': 'https://www.finep.gov.br/chamadas-publicas/chamadapublica/759'
        },
        {
            'titulo': 'FIP Transição Energética', 
            'url': 'https://www.finep.gov.br/chamadas-publicas/chamadapublica/760'
        }
    ]
    
    print(f"🔗 Links padrão já configurados: {len(links_default)}")
    for i, link in enumerate(links_default, 1):
        print(f"   {i}. {link['titulo']}")
        print(f"      URL: {link['url']}")
    
    print("\n" + "="*50)
    print("OPÇÕES:")
    print("1. Usar apenas os links padrão")
    print("2. Adicionar novos links aos padrão")
    print("3. Usar apenas novos links (ignorar padrão)")
    
    while True:
        try:
            opcao = input("\n👆 Escolha uma opção (1-3): ").strip()
            if opcao in ['1', '2', '3']:
                break
            else:
                print("❌ Opção inválida! Digite 1, 2 ou 3.")
        except KeyboardInterrupt:
            print("\n❌ Operação cancelada pelo usuário")
            return links_default
    
    if opcao == '1':
        print("✅ Usando links padrão")
        return links_default
    
    # Para opções 2 e 3, coletar novos links
    novos_links = []
    
    print(f"\n📝 ADICIONANDO NOVOS LINKS")
    print("💡 Dica: Digite 'fim' quando terminar de adicionar links")
    print("-" * 50)
    
    contador = 1
    while True:
        print(f"\n🔗 LINK {contador}:")
        
        try:
            # Coleta título
            titulo = input("   📋 Título/Nome da chamada: ").strip()
            if titulo.lower() == 'fim':
                break
            
            if not titulo:
                print("   ⚠️ Título não pode estar vazio!")
                continue
            
            # Coleta URL
            url = input("   🌐 URL completa: ").strip()
            if url.lower() == 'fim':
                break
                
            if not url:
                print("   ⚠️ URL não pode estar vazia!")
                continue
                
            # Validação básica da URL
            if not url.startswith(('http://', 'https://')):
                print("   ⚠️ URL deve começar com http:// ou https://")
                continue
            
            # Adiciona o novo link
            novos_links.append({
                'titulo': titulo,
                'url': url
            })
            
            print(f"   ✅ Link {contador} adicionado: {titulo}")
            contador += 1
            
            # Pergunta se quer continuar
            if contador > 10:  # Limite de segurança
                continuar = input("\n   ❓ Adicionar mais links? (s/n): ").lower()
                if continuar not in ['s', 'sim', 'y', 'yes']:
                    break
                    
        except KeyboardInterrupt:
            print("\n❌ Adição de links cancelada")
            break
    
    # Combina links conforme a opção escolhida
    if opcao == '2':
        # Adicionar aos padrão
        links_finais = links_default + novos_links
        print(f"\n✅ Total de links: {len(links_finais)} ({len(links_default)} padrão + {len(novos_links)} novos)")
    else:
        # Usar apenas novos (opção 3)
        links_finais = novos_links
        print(f"\n✅ Total de links: {len(links_finais)} (apenas novos links)")
    
    # Exibe resumo final
    if links_finais:
        print(f"\n📋 LINKS CONFIGURADOS PARA ANÁLISE:")
        print("-" * 50)
        for i, link in enumerate(links_finais, 1):
            print(f"{i}. {link['titulo']}")
            print(f"   🔗 {link['url']}")
        
        confirmar = input(f"\n✅ Confirma análise de {len(links_finais)} link(s)? (s/n): ").lower()
        if confirmar in ['s', 'sim', 'y', 'yes']:
            return links_finais
        else:
            print("❌ Análise cancelada pelo usuário")
            return []
    else:
        print("⚠️ Nenhum link configurado")
        return links_default

def main():
    print("🚀 FINEP - SISTEMA DE ANÁLISE DE CHAMADAS PÚBLICAS")
    print("🤖 Versão com Configuração Interativa de Links")
    print("="*70)
    
    # Verificações
    if not OpenAI or not OPENAI_API_KEY:
        print("❌ ERRO: OpenAI não configurada")
        return
    
    if not sync_playwright:
        print("❌ ERRO: Playwright não disponível") 
        return
        
    print("✅ Sistema operacional")
    
    # Limpeza de arquivos antigos
    print("\n🧹 Limpando arquivos antigos...")
    cleanup_old_files()
    
    # Coleta links do usuário
    chamadas = get_user_links()
    
    if not chamadas:
        print("❌ Nenhum link para analisar. Encerrando...")
        return
    
    resultados = []
    
    # Processa cada chamada
    for i, chamada in enumerate(chamadas, 1):
        print(f"\n{'='*80}")
        print(f"📋 ANÁLISE {i}/{len(chamadas)}")
        print('='*80)
        
        resultado = process_call(chamada['url'], chamada['titulo'])
        resultados.append(resultado)
        
        print(f"\n🏁 Status Final: {resultado['Status_Processamento']}")
        print('='*80)
    
    # Exibe resumo consolidado
    print("\n" + "="*80)
    print("📊 RESUMO GERAL DOS RESULTADOS")
    print("="*80)
    
    for i, resultado in enumerate(resultados, 1):
        print(f"\n🔸 CHAMADA {i}: {resultado['Nome_da_Chamada']}")
        print(f"   💰 Valor Global: {resultado['Valor_Global_Disponivel']}")
        print(f"   💰 Valor/Projeto: {resultado['Valor_Maximo_Por_Projeto']}")
        print(f"   📅 Prazo: {resultado['Data_Limite_Submissao']}")
        print(f"   🔄 Contrapartida: {resultado['Percentual_Contrapartida']}")
        print(f"   📊 TRL: {resultado['Nivel_TRL_Exigido']}")
        print(f"   📄 PDF: {resultado['URL_PDF_Principal'].split('/')[-1] if resultado['URL_PDF_Principal'] != 'Não encontrado' else 'N/A'}")
        print(f"   ✅ Status: {resultado['Status_Processamento']}")
    
    # Salva arquivos com método corrigido
    print(f"\n💾 SALVANDO RESULTADOS...")
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    csv_filename = f"FINEP_Chamadas_Publicas_{timestamp}.csv"
    
    # Salva CSV corrigido
    if save_to_csv(resultados, csv_filename):
        print("\n📋 ESTRUTURA DA PLANILHA:")
        print("   • Cada informação em coluna separada")
        print("   • Dados limpos e formatados")
        print("   • Encoding UTF-8 com BOM para Excel")
        print("   • Todos os campos entre aspas para proteção")
        
        # Tenta criar versão Excel também
        create_excel_version(resultados, csv_filename)
        
        print("\n🎉 ANÁLISE CONCLUÍDA COM SUCESSO!")
        print("📁 Pasta de projeto mantida limpa")
        print("📊 Planilhas prontas para uso no Excel/LibreOffice")
    else:
        print("\n❌ Erro ao salvar - verifique permissões de arquivo")

if __name__ == '__main__':
    main()