import os

# Configurações gerais
USE_PLAYWRIGHT = True
PDF_DOWNLOAD_FOLDER = "pdfs"
os.makedirs(PDF_DOWNLOAD_FOLDER, exist_ok=True)

# API Keys - IMPORTANTE: Substitua pela sua chave válida
OPENAI_API_KEY = "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"  # Deixe vazio por segurança - configure via variável de ambiente ou substitua por chave válida

# Configurações de análise
MAX_TEXT_LENGTH = 8000
PDF_CHUNK_SIZE = 6000
REQUEST_TIMEOUT = 60