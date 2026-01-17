import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# OpenAI API Key
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

from openai import OpenAI
from utils.text_processor import safe_json_parse
from typing import Dict, Optional

class OpenAIClient:
    def __init__(self):
        self.client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None
    
    def is_available(self) -> bool:
        return self.client is not None
    
    def analyze_website_content(self, html_content: str, url: str) -> Dict:
        """Analisa conteúdo do site usando OpenAI"""
        if not self.is_available():
            return {}
        
        try:
            from bs4 import BeautifulSoup
            
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
                model="gpt-4.0-turbo",
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