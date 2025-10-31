import requests
from bs4 import BeautifulSoup
from io import BytesIO
from urllib.parse import urljoin
from typing import List, Dict, Optional
import PyPDF2
import re

class WebScraper:
    def __init__(self, use_playwright: bool = True):
        self.use_playwright = use_playwright
    
    def get_page_content(self, url: str) -> Optional[str]:
        """Obtém conteúdo da página usando Playwright ou requests"""
        if self.use_playwright and self._is_playwright_available():
            return self._get_content_with_playwright(url)
        else:
            return self._get_content_with_requests(url)
    
    def _is_playwright_available(self) -> bool:
        try:
            from playwright.sync_api import sync_playwright
            return True
        except ImportError:
            return False
    
    def _get_content_with_playwright(self, url: str) -> Optional[str]:
        """Obtém conteúdo com Playwright"""
        try:
            from playwright.sync_api import sync_playwright
            
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                page.goto(url, timeout=45000, wait_until='networkidle')
                html_content = page.content()
                browser.close()
                print("   ✅ Página carregada com sucesso (Playwright)")
                return html_content
        except Exception as e:
            print(f"   ❌ Erro Playwright: {e}")
            return None
    
    def _get_content_with_requests(self, url: str) -> Optional[str]:
        """Obtém conteúdo com requests"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = requests.get(url, timeout=30, headers=headers)
            response.raise_for_status()
            print("   ✅ Página carregada com sucesso (requests)")
            return response.text
        except Exception as e:
            print(f"   ❌ Erro requests: {e}")
            return None
    
    def find_pdf_links(self, html_content: str, base_url: str) -> List[str]:
        """Busca links de PDF na página"""
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
                # Ordena por relevância
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

    def find_pdf_links_deep(self, html_content: str, base_url: str, max_candidates: int = 6) -> List[str]:
        """Faz uma busca de 1 nível: segue links relevantes e procura PDFs na página de destino."""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            candidates: List[str] = []
            keywords = ['edital', 'chamada', 'regulamento', 'anexo', 'resultado', 'publica', 'seleção', 'proposta']

            for a in soup.find_all('a', href=True):
                href = a.get('href')
                text = (a.get_text(strip=True) or '').lower()
                url = urljoin(base_url, href)
                if any(k in text for k in keywords) or any(k in href.lower() for k in keywords):
                    candidates.append(url)

            # Dedup e limita
            seen = set()
            filtered = []
            for url in candidates:
                if url not in seen:
                    seen.add(url)
                    filtered.append(url)
                if len(filtered) >= max_candidates:
                    break

            if filtered:
                print(f"   🔎 Buscando PDFs em links relacionados ({len(filtered)} candidatos)...")

            for i, url in enumerate(filtered, 1):
                print(f"      ↪️ [{i}/{len(filtered)}] {url}")
                content = self.get_page_content(url)
                if not content:
                    continue
                found = self.find_pdf_links(content, url)
                if found:
                    return found

            return []
        except Exception as e:
            print(f"   ❌ Erro na busca profunda de PDFs: {e}")
            return []
    
    def extract_pdf_text(self, pdf_url: str) -> str:
        """Extrai texto de PDF"""
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