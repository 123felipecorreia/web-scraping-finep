import os
import sys
import re
from typing import Dict, List
import io
import urllib.parse as urlparse

# Optional third-party helpers used for text extraction
try:
    from bs4 import BeautifulSoup
except Exception:
    BeautifulSoup = None

try:
    import trafilatura
except Exception:
    trafilatura = None

try:
    import fitz  # PyMuPDF
except Exception:
    fitz = None

try:
    import docx
except Exception:
    docx = None

# Ensure project root is on sys.path when running this file directly (python ai/pdf_analyzer.py)
_CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(_CURRENT_DIR)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from ai.openai_client import OpenAIClient
from utils.text_processor import split_text_intelligently, safe_json_parse

class PDFAnalyzer:
    def __init__(self):
        self.openai_client = OpenAIClient()

    # ---- small helper utilities (moved here per request) ----
    def _guess_ext(self, url: str) -> str:
        path = urlparse.urlparse(url).path
        ext = os.path.splitext(path)[1].lower()
        return ext

    def _extract_text_from_pdf(self, content: bytes) -> str:
        if fitz is None:
            return ""
        try:
            with fitz.open(stream=content, filetype="pdf") as doc:
                texts = []
                for page in doc:
                    texts.append(page.get_text("text"))
                return "\n".join(texts)
        except Exception:
            return ""

    def _extract_text_from_docx(self, content: bytes) -> str:
        if docx is None:
            return ""
        try:
            mem = io.BytesIO(content)
            d = docx.Document(mem)
            return "\n".join([p.text for p in d.paragraphs])
        except Exception:
            return ""

    def _extract_text_from_html(self, html: str, url: str) -> str:
        if trafilatura is not None:
            try:
                downloaded = trafilatura.extract(html, include_links=False, include_formatting=False, url=url)
                if downloaded and downloaded.strip():
                    return downloaded
            except Exception:
                pass
        if BeautifulSoup is None:
            return html
        soup = BeautifulSoup(html, "lxml")
        return soup.get_text(separator="\n")
    
    def analyze_pdf_with_ai_robust(self, pdf_text: str) -> Dict:
        """Análise de PDF otimizada"""
        if not self.openai_client.is_available():
            return {
                'Valor_Global': "IA não disponível",
                'Valor_Maximo_Por_Projeto': "IA não disponível", 
                'Data_Limite_Submissao': "IA não disponível",
                'Percentual_Contrapartida': "IA não disponível",
                'Nivel_TRL_Exigido': "IA não disponível"
            }
        
        try:
            text_chunks = split_text_intelligently(pdf_text, 6000)
            print(f"   📖 Analisando {len(text_chunks)} seções do PDF...")
            
            all_results = []
            informacoes_encontradas = []
            
            for i, chunk in enumerate(text_chunks, 1):
                print(f"      📄 Seção {i}/{len(text_chunks)}...", end=" ")
                
                prompt = self._create_analysis_prompt(chunk)
                result = self._process_chunk_with_ai(prompt)
                
                if result:
                    all_results.append(result)
                    found_info = self._extract_found_info(result)
                    if found_info:
                        print("✅")
                        for info in found_info:
                            informacoes_encontradas.append(info)
                            print(f"         🎯 {info}")
                    else:
                        print("❌")
                else:
                    print("❌")
            
            self._display_extraction_summary(informacoes_encontradas)
            return self._consolidate_results(all_results)
            
        except Exception as e:
            print(f"\n   ❌ Erro geral na análise: {e}")
            return self._get_error_result(str(e))

    from typing import Tuple

    def is_pdf_edital(self, pdf_text: str, pdf_url: str = "") -> Tuple[bool, float]:
        """Use LLM (when available) to judge whether a PDF text is the official edital/chamada.
        Returns (is_edital: bool, confidence: float 0..1).
        This uses a focused Portuguese prompt that emphasizes distinguishing edital language
        from auxiliary/tutorial pages (e.g., "como acessar", "tutorial", "guia de uso").
        """
        text = (pdf_text or "").strip()
        # heuristic: count positive and negative cues
        keywords_positive = [
            'edital', 'chamada pública', 'chamada', 'objeto', 'submissão', 'proposta', 'cronograma',
            'recursos', 'verba', 'financiamento', 'seleção', 'avaliação', 'proponente', 'inscrição',
            'nº do edital', 'número do edital', 'regulamento', 'concurso'
        ]
        keywords_negative = [
            'tutorial', 'como acessar', 'guia', 'manual', 'passo a passo', 'login', 'acesso', 'tutorial de',
            'como usar', 'instalação', 'suporte técnico', 'erro', 'faq'
        ]

        low_text = text.lower()
        pos_count = sum(1 for k in keywords_positive if k in low_text)
        neg_count = sum(1 for k in keywords_negative if k in low_text)

        # heuristic confidence in [0,1] (pos minus neg normalized)
        heuristic_conf = max(0.0, (pos_count - neg_count) / max(len(keywords_positive), 1))
        # If LLM available, ask for a concise JSON judgment to improve precision
        if self.openai_client.is_available() and len(text) > 200:
            try:
                # Keep prompt explicit and short, in Portuguese.
                prompt = f"""
Classificador de documentos (Português).
Você recebe um trecho de texto extraído de um PDF e a URL. Seu objetivo é decidir se o documento
é o EDITAL/CHAMADA OFICIAL que contém regras, valores, elegibilidade e prazos para submissão de propostas.
Não considere como edital documentos que sejam tutoriais, guias de uso, manuais de sistema, ou instruções de login.

Responda SOMENTE com um JSON válido com as chaves: {{"is_edital": true|false, "confidence": numero_entre_0_e_1}}

EXEMPLOS (siga o formato exatamente):

Exemplo positivo (deve resultar is_edital=true):
[EXEMPLO_POSITIVO]
Objeto: Selecionar propostas para fomento à pesquisa. Valor Global: R$ 2.000.000. Prazo de inscrição: 2025-03-31.
Critérios de elegibilidade: universidades e empresas de base tecnológica.
[/EXEMPLO_POSITIVO]

Resposta esperada:
{"is_edital": true, "confidence": 0.95}

Exemplo negativo (tutorial/manual — deve resultar is_edital=false):
[EXEMPLO_NEGATIVO]
Tutorial de preenchimento: Como acessar o sistema, passo a passo para anexar documentos e enviar sua proposta.
Inclui instruções de login e capturas de tela.
[/EXEMPLO_NEGATIVO]

Resposta esperada:
{"is_edital": false, "confidence": 0.98}

URL: {pdf_url}

TEXTO (trecho):
{text[:8000]}
"""

                resp = self.openai_client.client.chat.completions.create(
                    model="gpt-4o-mini" if hasattr(self.openai_client.client, 'chat') else "gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": "Classifique estritamente como JSON com as chaves solicitadas."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.0,
                    max_tokens=120,
                )
                raw = resp.choices[0].message.content.strip()
                parsed = safe_json_parse(raw)
                if isinstance(parsed, dict) and 'is_edital' in parsed:
                    is_ed = bool(parsed.get('is_edital'))
                    conf = float(parsed.get('confidence') or 0.0)
                    # combine LLM confidence and heuristic
                    combined = (heuristic_conf + conf) / 2.0
                    return is_ed, max(0.0, min(1.0, combined))
            except Exception:
                pass

        # Fallback: treat heuristic_conf > 0.2 as positive
        return (heuristic_conf > 0.2), float(heuristic_conf)
    
    def _create_analysis_prompt(self, chunk: str) -> str:
        """Cria prompt para análise do PDF"""
        return f"""
        MISSÃO ESPECIALIZADA: Seu objetivo é identificar e extrair informações completas e contextualizadas sobre oportunidades de fomento à pesquisa disponíveis em sites oficiais de agências, fundações e programas de financiamento público ou privado.

        Ao processar as páginas e arquivos (incluindo documentos em PDF), concentre-se em detectar, interpretar e consolidar os seguintes elementos:

        Valor Global – Identifique o montante total de recursos destinados à chamada pública, edital ou programa.

        Valor Máximo do Projeto – Determine o valor máximo financiável por projeto ou proposta individual.

        Data Limite – Extraia a data final para submissão de propostas, incluindo eventuais prorrogações ou reaberturas.

        Contrapartida – Identifique se há exigência de contrapartida financeira, institucional ou em bens/serviços, e descreva o percentual ou valor estimado quando disponível.

        Índice de TRL (Technology Readiness Level) – Localize, quando mencionado, o nível de maturidade tecnológica exigido ou estimado para os projetos. Caso não esteja explicitamente informado, infira um TRL aproximado com base na descrição do tipo de pesquisa (ex: pesquisa básica, aplicada, protótipo, validação em ambiente operacional etc.).

        Se qualquer uma das informações acima não estiver claramente explícita, aplique análise semântica contextual para inferir os valores ou categorias mais prováveis, sem sair do escopo técnico e sem extrapolar o conteúdo original.
        Não invente dados nem utilize fontes externas além do material disponível na própria página ou documento analisado.

        TEXTO PARA ANÁLISE:
        {chunk}

        RESPONDA APENAS neste JSON exato:
        {{"Valor_Global": "valor ou Não encontrado", "Valor_Maximo_Por_Projeto": "valor ou Não encontrado", "Data_Limite_Submissao": "data ou Não encontrado", "Percentual_Contrapartida": "percentual ou Não encontrado", "Nivel_TRL_Exigido": "TRL ou Não encontrado"}}
        """
    
    def _process_chunk_with_ai(self, prompt: str) -> Dict:
        """Processa um chunk com IA"""
        try:
            response = self.openai_client.client.chat.completions.create(
                model="gpt-4.0-turbo",
                messages=[
                    {"role": "system", "content": "Retorne APENAS JSON válido."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=150,
                temperature=0.05
            )
            
            ai_response = response.choices[0].message.content.strip()
            return self._parse_ai_response(ai_response)
            
        except Exception:
            return {}
    
    def _parse_ai_response(self, ai_response: str) -> Dict:
        """Parse da resposta da IA"""
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
        
        return result
    
    def _extract_found_info(self, result: Dict) -> List[str]:
        """Extrai informações encontradas para display"""
        found_info = []
        for key, value in result.items():
            if value != "Não encontrado":
                found_info.append(f"{key}: {value}")
        return found_info
    
    def _display_extraction_summary(self, informacoes_encontradas: List[str]):
        """Exibe resumo da extração"""
        print(f"\n   📊 INFORMAÇÕES EXTRAÍDAS DO PDF:")
        if informacoes_encontradas:
            for info in set(informacoes_encontradas):
                print(f"      ✅ {info}")
        else:
            print("      ⚠️ Nenhuma informação específica extraída")
    
    def _consolidate_results(self, all_results: List[Dict]) -> Dict:
        """Consolida resultados de todos os chunks"""
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
            return self._get_empty_result()
    
    def _get_empty_result(self) -> Dict:
        return {
            'Valor_Global': "Não extraído",
            'Valor_Maximo_Por_Projeto': "Não extraído",
            'Data_Limite_Submissao': "Não extraído",
            'Percentual_Contrapartida': "Não extraído",
            'Nivel_TRL_Exigido': "Não extraído"
        }
    
    def _get_error_result(self, error_msg: str) -> Dict:
        return {
            'Valor_Global': f"Erro: {error_msg[:50]}",
            'Valor_Maximo_Por_Projeto': "Erro na análise",
            'Data_Limite_Submissao': "Erro na análise",
            'Percentual_Contrapartida': "Erro na análise",
            'Nivel_TRL_Exigido': "Erro na análise"
        }