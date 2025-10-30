#!/usr/bin/env python3
"""
FINEP - SISTEMA DE ANÁLISE DE CHAMADAS PÚBLICAS
Sistema modularizado para extração e análise de editais da FINEP
"""

import os
import argparse
from datetime import datetime

# Importações dos nossos módulos
from core.file_manager import cleanup_old_files
from core.data_processor import DataProcessor
from utils.csv_handler import CSVHandler
from models.schemas import LinkConfig
from config.settings import USE_PLAYWRIGHT  # Corrigido: Config com C maiúsculo

# Pasta padrão onde o usuário pode colocar a planilha de links
# usar pasta 'Links' na raiz do projeto
# LINKS_FOLDER = os.path.join(os.path.dirname(__file__), 'Links')

# OU caminho absoluto no seu Windows (exemplo)
LINKS_FOLDER = r"C:\Users\fmcorreia.SISTEMAFIRJAN\Desktop\web-scraping-finep\Links\Sites_de_fomento.xlsx"
os.makedirs(LINKS_FOLDER, exist_ok=True)


def _find_links_file(search_path: str = None) -> str:
    """Procura automaticamente por um arquivo de links.
    Se um caminho for fornecido, valida e retorna. Caso contrário, busca na pasta LINKS_FOLDER.
    Prioriza: links.xlsx, links.xls, links.csv; retorna caminho ou string vazia.
    """
    import glob
    base = search_path or LINKS_FOLDER
    # If a file path was provided and it exists, return it (if file)
    if search_path:
        if os.path.exists(search_path):
            # if it's a directory, search inside it
            if os.path.isdir(search_path):
                base = search_path
            else:
                return search_path
        else:
            return ""
    # Also check for a folder named 'Links' (case-insensitive) at project root
    project_root = os.path.dirname(__file__)
    for candidate in os.listdir(project_root):
        if candidate.lower() == 'links' and os.path.isdir(os.path.join(project_root, candidate)):
            # prefer user-provided folder LINKS_FOLDER, but allow 'Links' if it exists
            if base == LINKS_FOLDER:
                base = os.path.join(project_root, candidate)
            break
    patterns = [
        os.path.join(base, "meuarquivo.xlsx"),
        os.path.join(base, "meus_links.xlsx"),
        os.path.join(base, "*.xlsx"),
        os.path.join(base, "*.csv"),
    ]
    candidates = []
    for pattern in patterns:
        candidates.extend(glob.glob(pattern))
    return candidates[0] if candidates else ""


def _read_links_from_file(path: str) -> list:
    """Lê uma planilha (Excel ou CSV) e retorna lista de LinkConfig.
    Procura automaticamente colunas com 'link'/'url' e 'titulo'/'title'.
    """
    links = []
    try:
        import pandas as pd
    except Exception:
        pd = None

    def _normalize_header(h: str) -> str:
        return h.strip().lower() if isinstance(h, str) else ""

    if not path:
        return links

    try:
        if path.lower().endswith('.csv'):
            if pd:
                df = pd.read_csv(path)
            else:
                import csv as _csv
                with open(path, newline='', encoding='utf-8') as f:
                    reader = _csv.reader(f)
                    rows = list(reader)
                if not rows:
                    return links
                headers = rows[0]
                data_rows = rows[1:]
                # find url column
                url_idx = None
                title_idx = None
                for i, h in enumerate(headers):
                    lh = _normalize_header(h)
                    if 'link' in lh or 'url' in lh or 'site' in lh:
                        url_idx = i
                    if 'title' in lh or 'titulo' in lh or 'nome' in lh:
                        title_idx = i
                for r in data_rows:
                    if url_idx is None:
                        # try every cell
                        url = next((c for c in r if isinstance(c, str) and c.startswith('http')), '')
                    else:
                        url = r[url_idx] if url_idx < len(r) else ''
                    title = r[title_idx] if title_idx and title_idx < len(r) else url
                    if url and str(url).strip():
                        links.append(LinkConfig(titulo=str(title).strip(), url=str(url).strip()))
                return links
        else:
            # Excel
            if pd:
                df = pd.read_excel(path)
            else:
                # openpyxl could be used, but require pandas simplifies; return empty if not available
                return links

        # If we have a DataFrame, try to locate columns
        if pd is not None:
            cols = list(df.columns)
            url_col = None
            title_col = None
            for c in cols:
                lc = _normalize_header(c)
                if any(k in lc for k in ('link', 'url', 'site', 'website')) and url_col is None:
                    url_col = c
                if any(k in lc for k in ('titulo', 'title', 'nome', 'name')) and title_col is None:
                    title_col = c
            if url_col is None and cols:
                # fallback: first column that looks like url
                for c in cols:
                    sample = df[c].dropna().astype(str).head(10).tolist()
                    if any(s.startswith('http') for s in sample):
                        url_col = c
                        break
            for _, row in df.iterrows():
                url = str(row[url_col]).strip() if url_col in df.columns else ''
                title = str(row[title_col]).strip() if (title_col in df.columns) else url
                if url and url.lower().startswith('http'):
                    links.append(LinkConfig(titulo=title or url, url=url))
    except Exception as e:
        print(f"⚠️ Erro ao ler arquivo de links '{path}': {e}")

    return links


def get_user_links(links_path: str = None) -> list:
    """Lê links para análise a partir de uma planilha no diretório do projeto.
    Procura automaticamente arquivos 'links.*'. Se não encontrar, informa o usuário e retorna lista vazia.
    """
    print("\n📋 CARREGANDO LINKS A PARTIR DE PLANILHA")
    print("="*50)
    path = _find_links_file(links_path)
    if not path:
        print(f"⚠️ Nenhum arquivo 'links.xlsx' ou 'links.csv' encontrado. Coloque o arquivo na pasta: {LINKS_FOLDER} ou use --links <caminho>.")
        return []

    print(f"🔗 Lendo links do arquivo: {path}")
    links = _read_links_from_file(path)
    if not links:
        print("⚠️ Nenhum link válido encontrado no arquivo.")
    else:
        print(f"✅ {len(links)} links carregados para análise")
    return links

def display_final_summary(resultados: list):
    """Exibe resumo final dos resultados"""
    print("\n" + "="*80)
    print("📊 RESUMO GERAL DOS RESULTADOS")
    print("="*80)
    
    for i, resultado in enumerate(resultados, 1):
        # Corrigido: usar snake_case das chaves do schema
        print(f"\n🔸 CHAMADA {i}: {resultado.get('nome_chamada', 'N/A')}")
        print(f"   💰 Valor Global: {resultado.get('valor_global', 'N/A')}")
        print(f"   💰 Valor/Projeto: {resultado.get('valor_maximo_projeto', 'N/A')}")
        print(f"   📅 Prazo: {resultado.get('data_limite_submissao', 'N/A')}")
        print(f"   🔄 Contrapartida: {resultado.get('percentual_contrapartida', 'N/A')}")
        print(f"   📊 TRL: {resultado.get('nivel_trl_exigido', 'N/A')}")
        print(f"   📄 PDF: {resultado.get('url_pdf_principal', 'N/A').split('/')[-1] if resultado.get('url_pdf_principal') != 'Não encontrado' else 'N/A'}")
        print(f"   ✅ Status: {resultado.get('status_processamento', 'N/A')}")

def main():
    print("🚀 FINEP - SISTEMA DE ANÁLISE DE CHAMADAS PÚBLICAS")
    print("🤖 Versão Modularizada - Manutenção Facilitada")
    print("="*70)
    # CLI: permite informar um arquivo de links alternativo
    parser = argparse.ArgumentParser(description='Analisador de Chamadas Públicas - FINEP')
    parser.add_argument('--links', '-l', help='Caminho para arquivo de links (xlsx ou csv) ou pasta contendo o arquivo')
    args = parser.parse_args()
    
    # Verificações iniciais
    try:
        from openai import OpenAI
        from config.settings import OPENAI_API_KEY  # Corrigido: Config com C maiúsculo
        if not OPENAI_API_KEY:
            print("❌ ERRO: OpenAI API Key não configurada")
            return
    except ImportError:
        print("❌ ERRO: OpenAI não disponível")
        return
    
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("❌ ERRO: Playwright não disponível") 
        return
        
    print("✅ Sistema operacional")
    
    # Limpeza de arquivos antigos
    print("\n🧹 Limpando arquivos antigos...")
    files_removed = cleanup_old_files()
    if files_removed > 0:
        print(f"✅ {files_removed} arquivo(s) antigo(s) removido(s)")
    else:
        print("ℹ️ Nenhum arquivo antigo encontrado")
    
    # Coleta links do arquivo (ou via --links)
    chamadas = get_user_links(args.links)
    
    if not chamadas:
        print("❌ Nenhum link para analisar. Encerrando...")
        return
    
    # Processa cada chamada
    resultados = []
    processor = DataProcessor(use_playwright=USE_PLAYWRIGHT)
    
    for i, chamada in enumerate(chamadas, 1):
        print(f"\n{'='*80}")
        print(f"📋 ANÁLISE {i}/{len(chamadas)}")
        print('='*80)
        
        resultado = processor.process_call(chamada.url, chamada.titulo)
        resultados.append(resultado)
        
        # Corrigido: usar snake_case e .get() para evitar KeyError
        print(f"\n🏁 Status Final: {resultado.get('status_processamento', 'Status não disponível')}")
        print('='*80)
    
    # Exibe resumo
    display_final_summary(resultados)
    
    # Salva resultados
    print(f"\n💾 SALVANDO RESULTADOS...")
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    csv_filename = f"FINEP_Chamadas_Publicas_{timestamp}.csv"
    
    if CSVHandler.save_to_csv(resultados, csv_filename):
        print("\n📋 ESTRUTURA DA PLANILHA:")
        print("   • Cada informação em coluna separada")
        print("   • Dados limpos e formatados") 
        print("   • Encoding UTF-8 com BOM para Excel")
        print("   • Todos os campos entre aspas para proteção")
        
        # Tenta criar versão Excel também
        CSVHandler.create_excel_version(resultados, csv_filename)
        
        print("\n🎉 ANÁLISE CONCLUÍDA COM SUCESSO!")
        print("📁 Código modularizado - Manutenção facilitada! 🚀")
    else:
        print("\n❌ Erro ao salvar - verifique permissões de arquivo")

if __name__ == '__main__':
    main()