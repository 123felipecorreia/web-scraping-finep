import re
import json
from typing import Dict, List

def safe_json_parse(text: str, debug: bool = False) -> Dict:
    """Parse JSON com tratamento robusto de erros"""
    if debug:
        print(f"🔍 Tentativa de parse JSON: {text[:200]}...")
    
    # Tenta parse direto
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        pass
    
    # Tenta extrair JSON do texto
    try:
        json_match = re.search(r'\{.*\}', text, re.DOTALL)
        if json_match:
            json_text = json_match.group(0)
            return json.loads(json_text)
    except json.JSONDecodeError:
        pass
    
    # Fallback: regex para campos específicos
    try:
        result = {}
        patterns = {
            'Valor_Global': r'"?Valor_Global"?\s*:\s*"([^"]*)"',
            'Valor_Projeto': r'"?Valor_Projeto"?\s*:\s*"([^"]*)"',
            'Prazo_Submissao': r'"?Prazo_Submissao"?\s*:\s*"([^"]*)"',
            'Contrapartida': r'"?Contrapartida"?\s*:\s*"([^"]*)"',
            'Escala_TRL': r'"?Escala_TRL"?\s*:\s*"([^"]*)"'
        }
        
        for key, pattern in patterns.items():
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                result[key] = match.group(1)
            else:
                result[key] = "Não encontrado"
        
        if any(v != "Não encontrado" for v in result.values()):
            return result
            
    except Exception:
        pass
    
    return {
        'Valor_Global': "Não encontrado",
        'Valor_Projeto': "Não encontrado", 
        'Prazo_Submissao': "Não encontrado",
        'Contrapartida': "Não encontrado",
        'Escala_TRL': "Não encontrado"
    }

def split_text_intelligently(text: str, max_length: int = 8000) -> List[str]:
    """Divide texto em chunks inteligentes"""
    if len(text) <= max_length:
        return [text]
    
    sections = text.split('\n\n')
    chunks = []
    current_chunk = ""
    
    for section in sections:
        if len(current_chunk + section) < max_length:
            current_chunk += section + "\n\n"
        else:
            if current_chunk:
                chunks.append(current_chunk.strip())
            current_chunk = section + "\n\n"
    
    if current_chunk:
        chunks.append(current_chunk.strip())
    
    return chunks if chunks else [text[:max_length]]

def clean_csv_data(value: str) -> str:
    """Limpa dados para CSV removendo caracteres problemáticos"""
    if not isinstance(value, str):
        return str(value)
    
    # Remove quebras de linha e tabs
    value = value.replace('\n', ' ').replace('\r', ' ').replace('\t', ' ')
    
    # Remove vírgulas extras que podem quebrar o CSV
    value = re.sub(r',+', ',', value)
    
    # Remove espaços extras
    value = re.sub(r'\s+', ' ', value).strip()
    
    # Limita o tamanho para evitar células muito grandes
    if len(value) > 500:
        value = value[:497] + "..."
    
    return value