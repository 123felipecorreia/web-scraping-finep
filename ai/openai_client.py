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
    SYSTEM_PROMPT = """You are a precise research assistant that extracts funding-call (edital/chamada) information from noisy web or document text. Return strictly valid JSON when asked and follow the schema instructions exactly."""
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
