from openai import OpenAI
from config.settings import OPENAI_API_KEY
from utils.text_processor import safe_json_parse
from typing import Dict, Optional, List, Tuple, Set
import os
import json
from dataclasses import dataclass, asdict

# Only need BeautifulSoup here for simple website text extraction
try:
    from bs4 import BeautifulSoup
except Exception:
    BeautifulSoup = None

# (Optional extraction helpers moved to ai/pdf_analyzer.py)


@dataclass
class FundingRecord:
    source_url: str
    resolved_url: str
    is_funding_call: bool
    confidence: float
    title: Optional[str] = None
    sponsor: Optional[str] = None
    program_name: Optional[str] = None
    country_or_region: Optional[str] = None
    eligibility: Optional[str] = None
    thematic_areas: Optional[str] = None
    total_budget: Optional[str] = None
    award_ceiling: Optional[str] = None
    award_floor: Optional[str] = None
    cost_sharing: Optional[str] = None
    currency: Optional[str] = None
    open_date: Optional[str] = None
    close_date: Optional[str] = None
    multiple_deadlines: Optional[str] = None
    duration: Optional[str] = None
    contact: Optional[str] = None
    application_link: Optional[str] = None
    attachments: Optional[str] = None
    language: Optional[str] = None
    raw_excerpt: Optional[str] = None


class OpenAIClient:
    def __init__(self):
        self.client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

    # ---- Prompt templates ----
    SYSTEM_PROMPT = """
Você é um assistente de pesquisa preciso e focado em extração de informações de chamadas públicas / editais a partir de texto ruidoso de sites ou de documentos (PDFs, DOCX, HTML).

Objetivo principal:
- Priorize identificar o PDF QUE É O EDITAL/CHAMADA OFICIAL relacionado à página alvo. Para isso, procure explicitamente por anexos/links cujo NOME DE ARQUIVO contenha termos que tipicamente indicam um edital (veja exemplos abaixo).

Como proceder na busca e classificação de PDFs:
1) Antes de decidir, examine os nomes dos arquivos (filenames) e URLs dos PDFs anexados. Dê peso alto a arquivos cujo nome contenha tokens como: "edital", "edital-", "edital_", "edital_n", "edital nº", "edital_no", "chamada", "editalde", "editalde", "editalnumero", "aviso-de-edital", "aviso_edital", "termo-de-abertura", "termo_abertura", "regulamento", "instrucoes-submissao", "instruções-submissão", "anexo-edital", "anexo" (quando combinado com 'edital' no contexto), ou variações linguísticas próximas.
2) Exclua ou atribua baixa prioridade a arquivos cujo nome ou conteúdo indiquem claramente serem tutoriais, guias de uso, manuais de acesso, instruções de login ou páginas de suporte (ex.: "tutorial", "guia", "manual", "como acessar", "passo a passo", "login").
3) Verifique se o PDF contém seções típicas de um edital: títulos/headers como "Objeto", "Objetivo", "Prazos", "Submissão", "Cronograma", "Recursos", "Forma de Seleção", "Critérios de Avaliação", "Elegibilidade", "Valor Global", "Valor por projeto". A presença de várias dessas seções deve aumentar muito a confiança de que o PDF é o edital.
4) Se várias formas de nomeação forem possíveis, combine sinais de filename + presença dessas seções no texto para produzir uma classificação robusta.

Resposta e formato:
- Ao ser solicitado a julgar/classificar retornará apenas JSON estritamente válido com as chaves solicitadas (por exemplo {"is_edital": true, "confidence": 0.0-1.0}) — sem texto adicional.
- Para extrações posteriores (quando for solicitado que extraia campos do edital), respeite o esquema indicado e não invente valores; deixe campos como null ou "Não encontrado" quando não puder inferir com segurança.

Brevidade e idioma:
- Prefira Português ao formular instruções de classificação quando o texto/URL estiver em Português; use inglês apenas quando o material alvo estiver em inglês.

Exemplos de tokens de arquivo que devem aumentar a pontuação: "edital", "chamada", "nº edital", "aviso de abertura", "regulamento", "termo de referência", "anexo edital". Exemplos que devem reduzir a pontuação: "tutorial", "guia", "manual", "como acessar", "suporte técnico".

Use essas regras como critério primário para localizar e priorizar o PDF que será enviado ao analisador (`ai/pdf_analyzer.py`) para extração detalhada.
"""
    # (kept only the primary system prompt here; other selection/extraction helpers were removed per request)
    def is_available(self) -> bool:
        return self.client is not None

    # (extraction helpers were moved to ai/pdf_analyzer.py)

    # ---- Existing simple site analyzer retained ----
    def analyze_website_content(self, html_content: str, url: str) -> Dict:
        """Analisa conteúdo do site usando OpenAI (retorna dict com 'titulo' key when found)"""
        if not self.is_available():
            return {}

        try:
            if BeautifulSoup is None:
                # best-effort fallback
                text_content = html_content[:6000]
            else:
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

            response = self.client.chat.completions.create(
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

    # Note: crawler and PDF-classification helpers removed per user request.
