from typing import List, Dict
from models.schemas import ChamadaPublica, LinkConfig
from core.web_scraper import WebScraper
from ai.openai_client import OpenAIClient
from ai.pdf_analyzer import PDFAnalyzer

class DataProcessor:
    def __init__(self, use_playwright: bool = True):
        self.web_scraper = WebScraper(use_playwright)
        self.openai_client = OpenAIClient()
        self.pdf_analyzer = PDFAnalyzer()
    
    def process_call(self, url: str, titulo_inicial: str) -> Dict:
        """Processa uma chamada específica"""
        print(f"\n🔍 PROCESSANDO: {titulo_inicial}")
        print(f"🔗 URL: {url}")
        print("-" * 60)
        
        resultado = ChamadaPublica(
            id=titulo_inicial,
            url_original=url
        )
        
        try:
            # Passo 1: Acessa página
            print("🌐 Acessando página web...")
            html_content = self.web_scraper.get_page_content(url)
            
            if not html_content:
                resultado.status_processamento = 'Erro - Página inacessível'
                print("   ❌ Falha no carregamento da página")
                return resultado.__dict__
            
            # Passo 2: Extrai título
            print("\n🤖 Analisando conteúdo do site...")
            site_analysis = self.openai_client.analyze_website_content(html_content, url)
            if site_analysis and site_analysis.get('titulo') != 'Não encontrado':
                resultado.nome_chamada = site_analysis['titulo']
            
            # Passo 3: Busca PDFs
            print("\n🔍 Buscando documentos PDF...")
            pdf_urls = self.web_scraper.find_pdf_links(html_content, url)
            if not pdf_urls:
                resultado.status_processamento = 'Concluído - Sem PDFs relevantes'
                print("   ⚠️ Nenhum PDF relevante encontrado")
                return resultado.__dict__
            
            # Passo 4: Analisa PDF principal
            main_pdf = pdf_urls[0]
            resultado.url_pdf_principal = main_pdf
            
            print(f"\n📋 Analisando PDF principal:")
            print(f"   🔗 {main_pdf.split('/')[-1]}")
            
            pdf_text = self.web_scraper.extract_pdf_text(main_pdf)
            if not pdf_text:
                resultado.status_processamento = 'Erro - PDF não legível'
                print("   ❌ Não foi possível ler o PDF")
                return resultado.__dict__
            
            # Passo 5: Análise com IA
            print(f"\n🤖 ANÁLISE INTELIGENTE DO PDF:")
            pdf_data = self.pdf_analyzer.analyze_pdf_with_ai_robust(pdf_text)
            
            resultado.valor_global = pdf_data['Valor_Global']
            resultado.valor_maximo_projeto = pdf_data['Valor_Maximo_Por_Projeto']
            resultado.data_limite_submissao = pdf_data['Data_Limite_Submissao']
            resultado.percentual_contrapartida = pdf_data['Percentual_Contrapartida']
            resultado.nivel_trl_exigido = pdf_data['Nivel_TRL_Exigido']
            
            resultado.status_processamento = 'Concluído com sucesso'
            print(f"\n✅ PROCESSAMENTO CONCLUÍDO")
            
            return resultado.__dict__
            
        except Exception as e:
            resultado.status_processamento = f'Erro - {str(e)[:100]}'
            print(f"\n❌ Erro no processamento: {e}")
            return resultado.__dict__