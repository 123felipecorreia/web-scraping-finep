import os

# Configurações gerais
USE_PLAYWRIGHT = True
PDF_DOWNLOAD_FOLDER = "pdfs"
os.makedirs(PDF_DOWNLOAD_FOLDER, exist_ok=True)

# API Keys
OPENAI_API_KEY = "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"

# Configurações de análise
MAX_TEXT_LENGTH = 8000
PDF_CHUNK_SIZE = 6000
REQUEST_TIMEOUT = 60