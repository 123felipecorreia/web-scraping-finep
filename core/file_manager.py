import os
import glob
from typing import List

def cleanup_old_files() -> int:
    """Remove planilhas antigas do projeto"""
    try:
        patterns = [
            'FINEP_Chamadas_Publicas_*.csv',
            'finep_*.csv', 
            'chamadas_*.csv'
        ]
        
        files_removed = 0
        for pattern in patterns:
            files = glob.glob(pattern)
            for file in files:
                try:
                    os.remove(file)
                    files_removed += 1
                    print(f"   🗑️ Removido: {file}")
                except Exception as e:
                    print(f"   ⚠️ Não foi possível remover {file}: {e}")
        
        return files_removed
        
    except Exception as e:
        print(f"⚠️ Erro na limpeza de arquivos: {e}")
        return 0