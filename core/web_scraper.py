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
        """Obtém conteúdo com Playwright com retry"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                from playwright.sync_api import sync_playwright
                
                with sync_playwright() as p:
                    browser = p.chromium.launch(
                        headless=True,
                        args=['--disable-blink-features=AutomationControlled']
                    )
                    context = browser.new_context(
                        user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                        viewport={'width': 1920, 'height': 1080}
                    )
                    page = context.new_page()
                    
                    # Timeout aumentado e wait_until mais flexível
                    page.goto(url, timeout=60000, wait_until='domcontentloaded')
                    page.wait_for_timeout(2000)  # Aguarda carregamento adicional
                    
                    html_content = page.content()
                    browser.close()
                    print("   ✅ Página carregada com sucesso (Playwright)")
                    return html_content
            except Exception as e:
                if attempt < max_retries - 1:
                    print(f"   ⚠️ Tentativa {attempt + 1} falhou, tentando novamente...")
                    continue
                else:
                    print(f"   ❌ Erro Playwright após {max_retries} tentativas: {e}")
                    return None
        return None
    
    def _get_content_with_requests(self, url: str) -> Optional[str]:
        """Obtém conteúdo com requests com retry"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                    'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
                    'Accept-Encoding': 'gzip, deflate',
                    'Connection': 'keep-alive',
                    'Upgrade-Insecure-Requests': '1'
                }
                response = requests.get(url, timeout=45, headers=headers, allow_redirects=True, verify=True)
                response.raise_for_status()
                print("   ✅ Página carregada com sucesso (requests)")
                return response.text
            except Exception as e:
                if attempt < max_retries - 1:
                    print(f"   ⚠️ Tentativa {attempt + 1} falhou, tentando novamente...")
                    import time
                    time.sleep(2)
                    continue
                else:
                    print(f"   ❌ Erro requests após {max_retries} tentativas: {e}")
                    return None
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

    def collect_all_pdfs(self, start_url: str, max_pages: int = 200, max_depth: int = 3) -> List[str]:
        """Percorre o site (mesmo domínio) começando em start_url e coleta TODOS os links .pdf encontrados.
        Limita por número de páginas e profundidade para evitar varreduras infinitas.
        Retorna lista deduplicada de URLs absolutos para arquivos PDF.
        """
        try:
            from urllib.parse import urlparse

            parsed = urlparse(start_url)
            base_netloc = parsed.netloc.lower()
            if base_netloc.startswith('www.'):
                base_netloc = base_netloc[4:]

            visited_pages = set()
            found_pdfs = []
            queue = [(start_url, 0)]
            pages_seen = 0

            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }

            while queue and pages_seen < max_pages:
                url, depth = queue.pop(0)
                if url in visited_pages:
                    continue
                visited_pages.add(url)

                if depth > max_depth:
                    continue

                try:
                    resp = requests.get(url, timeout=10, headers=headers)
                    resp.raise_for_status()
                    html = resp.text
                except Exception:
                    continue

                pages_seen += 1
                print(f"   🌐 [{pages_seen}] Varredura: {url} (depth {depth})")

                soup = BeautifulSoup(html, 'html.parser')

                # coletar PDFs nesta página
                for a_tag in soup.find_all('a', href=True):
                    href = a_tag.get('href')
                    if not href:
                        continue
                    full = urljoin(url, href)
                    if '.pdf' in full.lower():
                        if full not in found_pdfs:
                            found_pdfs.append(full)

                # enfileirar links internos para seguir
                if depth < max_depth:
                    for a_tag in soup.find_all('a', href=True):
                        href = a_tag.get('href')
                        if not href:
                            continue
                        full = urljoin(url, href)
                        # simplificar netloc check
                        try:
                            p = urlparse(full)
                            netloc = p.netloc.lower()
                            if netloc.startswith('www.'):
                                netloc = netloc[4:]
                        except Exception:
                            continue

                        # seguir apenas se permanecer no mesmo domínio
                        if netloc.endswith(base_netloc) and full not in visited_pages:
                            # evitar adicionar arquivos binários e anchors
                            path = p.path.lower()
                            if any(path.endswith(ext) for ext in ['.pdf', '.jpg', '.png', '.zip', '.exe']):
                                continue
                            if full.startswith('#'):
                                continue
                            queue.append((full, depth + 1))

            print(f"   📎 Total de PDFs coletados no domínio: {len(found_pdfs)}")
            return found_pdfs
        except Exception as e:
            print(f"   ❌ Erro na coleta de PDFs do site: {e}")
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