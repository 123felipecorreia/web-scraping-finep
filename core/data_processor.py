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
        
        def _to_output_dict(chamada: ChamadaPublica) -> Dict:
            """Converte ChamadaPublica (dataclass) para dicionário no formato esperado pela UI/CSV."""
            return {
                'ID': chamada.id,
                'Nome_da_Chamada': chamada.nome_chamada,
                'URL_Original': chamada.url_original,
                'Valor_Global_Disponivel': chamada.valor_global,
                'Valor_Maximo_Por_Projeto': chamada.valor_maximo_projeto,
                'Data_Limite_Submissao': chamada.data_limite_submissao,
                'Percentual_Contrapartida': chamada.percentual_contrapartida,
                'Nivel_TRL_Exigido': chamada.nivel_trl_exigido,
                'URL_PDF_Principal': chamada.url_pdf_principal,
                'Status_Processamento': chamada.status_processamento,
                'Data_Coleta': chamada.data_coleta
            }

        try:
            # Passo 1: Acessa página
            print("🌐 Acessando página web...")
            html_content = self.web_scraper.get_page_content(url)
            
            if not html_content:
                resultado.status_processamento = 'Erro - Página inacessível'
                print("   ❌ Falha no carregamento da página")
                return _to_output_dict(resultado)
            
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
                return _to_output_dict(resultado)
            
            # Passo 4: Determina qual PDF é realmente o edital (amostra e pontuação)
            print("\n🔎 Identificando qual PDF é o edital da chamada...")
            selected_pdf = None
            best_conf = 0.0
            MIN_CONF = 0.50

            # Primeiro passe: classificar os PDFs diretos na página
            for candidate in pdf_urls:
                print(f"   ↪️ Amostrando PDF candidato: {candidate}")
                pdf_text = self.web_scraper.extract_pdf_text(candidate)
                if not pdf_text:
                    print("      ⚠️ Falha ao extrair texto deste PDF (pulando)")
                    continue
                is_edital, conf = self.pdf_analyzer.is_pdf_edital(pdf_text, candidate)
                print(f"      ➤ is_edital={is_edital}, confidence={conf:.2f}")
                if is_edital and conf >= MIN_CONF and conf > best_conf:
                    best_conf = conf
                    selected_pdf = candidate

            # Se nada com confiança suficiente foi encontrado, faça busca profunda em links relacionados e repita
            if not selected_pdf:
                print("   ℹ️ Nenhum PDF com confiança suficiente; executando busca profunda por candidatos relacionados...")
                deep_candidates = self.web_scraper.find_pdf_links_deep(html_content, url, max_candidates=6)
                for candidate in deep_candidates:
                    print(f"   ↪️ Amostrando (deep) PDF candidato: {candidate}")
                    pdf_text = self.web_scraper.extract_pdf_text(candidate)
                    if not pdf_text:
                        continue
                    is_edital, conf = self.pdf_analyzer.is_pdf_edital(pdf_text, candidate)
                    print(f"      ➤ is_edital={is_edital}, confidence={conf:.2f}")
                    if is_edital and conf >= MIN_CONF and conf > best_conf:
                        best_conf = conf
                        selected_pdf = candidate

            if not selected_pdf:
                # fallback para primeiro encontrado, mas marca no status
                selected_pdf = pdf_urls[0]
                resultado.status_processamento = 'Concluído - PDF escolhido por fallback'
                print("   ⚠️ Nenhum PDF claramente identificado como edital; usando fallback (primeiro PDF)")
            else:
                resultado.status_processamento = f'Concluído - PDF selecionado (conf {best_conf:.2f})'

            main_pdf = selected_pdf
            resultado.url_pdf_principal = main_pdf
            
            print(f"\n📋 Analisando PDF principal:")
            print(f"   🔗 {main_pdf.split('/')[-1]}")
            
            pdf_text = self.web_scraper.extract_pdf_text(main_pdf)
            if not pdf_text:
                resultado.status_processamento = 'Erro - PDF não legível'
                print("   ❌ Não foi possível ler o PDF")
                return _to_output_dict(resultado)
            
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
            return _to_output_dict(resultado)
            
        except Exception as e:
            resultado.status_processamento = f'Erro - {str(e)[:100]}'
            print(f"\n❌ Erro no processamento: {e}")
            return _to_output_dict(resultado)