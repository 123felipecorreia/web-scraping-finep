import os
import sys
import re
from typing import Dict, List

# Ensure project root is on sys.path when running this file directly (python ai/pdf_analyzer.py)
_CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(_CURRENT_DIR)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from ai.openai_client import OpenAIClient
from utils.text_processor import split_text_intelligently, safe_json_parse

class PDFAnalyzer:
    def __init__(self):
        self.openai_client = OpenAIClient()
    
    def analyze_pdf_with_ai_robust(self, pdf_text: str) -> Dict:
        """Análise de PDF otimizada"""
        if not self.openai_client.is_available():
            return {
                'Valor_Global': "IA não disponível",
                'Valor_Maximo_Por_Projeto': "IA não disponível", 
                'Data_Limite_Submissao': "IA não disponível",
                'Percentual_Contrapartida': "IA não disponível",
                'Nivel_TRL_Exigido': "IA não disponível"
            }
        
        try:
            text_chunks = split_text_intelligently(pdf_text, 6000)
            print(f"   📖 Analisando {len(text_chunks)} seções do PDF...")
            
            all_results = []
            informacoes_encontradas = []
            
            for i, chunk in enumerate(text_chunks, 1):
                print(f"      📄 Seção {i}/{len(text_chunks)}...", end=" ")
                
                prompt = self._create_analysis_prompt(chunk)
                result = self._process_chunk_with_ai(prompt)
                
                if result:
                    all_results.append(result)
                    found_info = self._extract_found_info(result)
                    if found_info:
                        print("✅")
                        for info in found_info:
                            informacoes_encontradas.append(info)
                            print(f"         🎯 {info}")
                    else:
                        print("❌")
                else:
                    print("❌")
            
            self._display_extraction_summary(informacoes_encontradas)
            return self._consolidate_results(all_results)
            
        except Exception as e:
            print(f"\n   ❌ Erro geral na análise: {e}")
            return self._get_error_result(str(e))
    
    def _create_analysis_prompt(self, chunk: str) -> str:
        """Cria prompt para análise do PDF"""
        return f"""
        MISSÃO ESPECIALIZADA: Seu objetivo é identificar e extrair informações completas e contextualizadas sobre oportunidades de fomento à pesquisa disponíveis em sites oficiais de agências, fundações e programas de financiamento público ou privado.

        Ao processar as páginas e arquivos (incluindo documentos em PDF), concentre-se em detectar, interpretar e consolidar os seguintes elementos:

        Valor Global – Identifique o montante total de recursos destinados à chamada pública, edital ou programa.

        Valor Máximo do Projeto – Determine o valor máximo financiável por projeto ou proposta individual.

        Data Limite – Extraia a data final para submissão de propostas, incluindo eventuais prorrogações ou reaberturas.

        Contrapartida – Identifique se há exigência de contrapartida financeira, institucional ou em bens/serviços, e descreva o percentual ou valor estimado quando disponível.

        Índice de TRL (Technology Readiness Level) – Localize, quando mencionado, o nível de maturidade tecnológica exigido ou estimado para os projetos. Caso não esteja explicitamente informado, infira um TRL aproximado com base na descrição do tipo de pesquisa (ex: pesquisa básica, aplicada, protótipo, validação em ambiente operacional etc.).

        Se qualquer uma das informações acima não estiver claramente explícita, aplique análise semântica contextual para inferir os valores ou categorias mais prováveis, sem sair do escopo técnico e sem extrapolar o conteúdo original.
        Não invente dados nem utilize fontes externas além do material disponível na própria página ou documento analisado.

        TEXTO PARA ANÁLISE:
        {chunk}

        RESPONDA APENAS neste JSON exato:
        {{"Valor_Global": "valor ou Não encontrado", "Valor_Maximo_Por_Projeto": "valor ou Não encontrado", "Data_Limite_Submissao": "data ou Não encontrado", "Percentual_Contrapartida": "percentual ou Não encontrado", "Nivel_TRL_Exigido": "TRL ou Não encontrado"}}
        """
    
    def _process_chunk_with_ai(self, prompt: str) -> Dict:
        """Processa um chunk com IA"""
        try:
            response = self.openai_client.client.chat.completions.create(
                model="gpt-4.0-turbo",
                messages=[
                    {"role": "system", "content": "Retorne APENAS JSON válido."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=150,
                temperature=0.05
            )
            
            ai_response = response.choices[0].message.content.strip()
            return self._parse_ai_response(ai_response)
            
        except Exception:
            return {}
    
    def _parse_ai_response(self, ai_response: str) -> Dict:
        """Parse da resposta da IA"""
        result = {}
        patterns = {
            'Valor_Global': r'"?Valor_Global"?\s*:\s*"([^"]*)"',
            'Valor_Maximo_Por_Projeto': r'"?Valor_Maximo_Por_Projeto"?\s*:\s*"([^"]*)"',
            'Data_Limite_Submissao': r'"?Data_Limite_Submissao"?\s*:\s*"([^"]*)"',
            'Percentual_Contrapartida': r'"?Percentual_Contrapartida"?\s*:\s*"([^"]*)"',
            'Nivel_TRL_Exigido': r'"?Nivel_TRL_Exigido"?\s*:\s*"([^"]*)"'
        }
        
        for key, pattern in patterns.items():
            match = re.search(pattern, ai_response, re.IGNORECASE)
            if match:
                result[key] = match.group(1)
            else:
                result[key] = "Não encontrado"
        
        return result
    
    def _extract_found_info(self, result: Dict) -> List[str]:
        """Extrai informações encontradas para display"""
        found_info = []
        for key, value in result.items():
            if value != "Não encontrado":
                found_info.append(f"{key}: {value}")
        return found_info
    
    def _display_extraction_summary(self, informacoes_encontradas: List[str]):
        """Exibe resumo da extração"""
        print(f"\n   📊 INFORMAÇÕES EXTRAÍDAS DO PDF:")
        if informacoes_encontradas:
            for info in set(informacoes_encontradas):
                print(f"      ✅ {info}")
        else:
            print("      ⚠️ Nenhuma informação específica extraída")
    
    def _consolidate_results(self, all_results: List[Dict]) -> Dict:
        """Consolida resultados de todos os chunks"""
        if all_results:
            consolidated = {
                'Valor_Global': "Não encontrado",
                'Valor_Maximo_Por_Projeto': "Não encontrado",
                'Data_Limite_Submissao': "Não encontrado",
                'Percentual_Contrapartida': "Não encontrado",
                'Nivel_TRL_Exigido': "Não encontrado"
            }
            
            for key in consolidated.keys():
                for result in all_results:
                    if key in result and result[key] != "Não encontrado":
                        consolidated[key] = result[key]
                        break
            
            print(f"\n   🎯 RESULTADO CONSOLIDADO:")
            for key, value in consolidated.items():
                status = "✅" if value != "Não encontrado" else "❌"
                print(f"      {status} {key}: {value}")
            
            return consolidated
        else:
            print(f"\n   ⚠️ Nenhum resultado consolidado obtido")
            return self._get_empty_result()
    
    def _get_empty_result(self) -> Dict:
        return {
            'Valor_Global': "Não extraído",
            'Valor_Maximo_Por_Projeto': "Não extraído",
            'Data_Limite_Submissao': "Não extraído",
            'Percentual_Contrapartida': "Não extraído",
            'Nivel_TRL_Exigido': "Não extraído"
        }
    
    def _get_error_result(self, error_msg: str) -> Dict:
        return {
            'Valor_Global': f"Erro: {error_msg[:50]}",
            'Valor_Maximo_Por_Projeto': "Erro na análise",
            'Data_Limite_Submissao': "Erro na análise",
            'Percentual_Contrapartida': "Erro na análise",
            'Nivel_TRL_Exigido': "Erro na análise"
        }