from dataclasses import dataclass
from typing import Optional
from datetime import datetime

@dataclass
class ChamadaPublica:
    id: str
    nome_chamada: str = "Não identificado"
    url_original: str = ""
    valor_global: str = "Não encontrado"
    valor_maximo_projeto: str = "Não encontrado"
    data_limite_submissao: str = "Não encontrado"
    percentual_contrapartida: str = "Não encontrado"
    nivel_trl_exigido: str = "Não encontrado"
    url_pdf_principal: str = "Não encontrado"
    status_processamento: str = "Iniciando"
    data_coleta: str = ""
    
    def __post_init__(self):
        if not self.data_coleta:
            self.data_coleta = datetime.now().strftime('%d/%m/%Y %H:%M')

@dataclass
class LinkConfig:
    titulo: str
    url: str