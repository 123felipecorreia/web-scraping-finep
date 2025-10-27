import csv
import os
from typing import List, Dict
from utils.text_processor import clean_csv_data

class CSVHandler:
    @staticmethod
    def save_to_csv(resultados: List[Dict], filename: str) -> bool:
        """Salva resultados em CSV com formatação adequada"""
        try:
            fieldnames = [
                'ID',
                'Nome_da_Chamada',
                'Valor_Global_Disponivel',
                'Valor_Maximo_Por_Projeto', 
                'Data_Limite_Submissao',
                'Percentual_Contrapartida',
                'Nivel_TRL_Exigido',
                'URL_PDF_Principal',
                'URL_Original',
                'Status_Processamento',
                'Data_Coleta'
            ]
            
            # Limpa os dados antes de salvar
            cleaned_resultados = CSVHandler._clean_results(resultados, fieldnames)
            
            # Salva com configurações específicas para CSV
            with open(filename, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.DictWriter(
                    f, 
                    fieldnames=fieldnames,
                    delimiter=',',
                    quotechar='"',
                    quoting=csv.QUOTE_ALL
                )
                writer.writeheader()
                writer.writerows(cleaned_resultados)
            
            print(f"💾 PLANILHA SALVA: {filename}")
            print(f"📊 {len(cleaned_resultados)} registros salvos com {len(fieldnames)} colunas")
            
            # Verifica se o arquivo foi criado corretamente
            if os.path.exists(filename):
                file_size = os.path.getsize(filename)
                print(f"📁 Tamanho do arquivo: {file_size:,} bytes")
                return True
            else:
                print("❌ Erro: arquivo não foi criado")
                return False
                
        except Exception as e:
            print(f"❌ Erro ao salvar CSV: {e}")
            return False
    
    @staticmethod
    def _clean_results(resultados: List[Dict], fieldnames: List[str]) -> List[Dict]:
        """Limpa os resultados para CSV"""
        cleaned_resultados = []
        for resultado in resultados:
            cleaned_resultado = {}
            for field in fieldnames:
                raw_value = resultado.get(field, 'N/A')
                cleaned_resultado[field] = clean_csv_data(str(raw_value))
            cleaned_resultados.append(cleaned_resultado)
        return cleaned_resultados
    
    @staticmethod
    def create_excel_version(resultados: List[Dict], csv_filename: str) -> None:
        """Cria versão Excel opcional"""
        try:
            import xlsxwriter
            
            excel_filename = csv_filename.replace('.csv', '.xlsx')
            
            workbook = xlsxwriter.Workbook(excel_filename)
            worksheet = workbook.add_worksheet('Chamadas FINEP')
            
            # Formatos
            header_format = workbook.add_format({
                'bold': True,
                'bg_color': '#4F81BD',
                'font_color': 'white',
                'border': 1
            })
            
            cell_format = workbook.add_format({
                'border': 1,
                'text_wrap': True,
                'valign': 'top'
            })
            
            # Headers
            headers = [
                'ID', 'Nome da Chamada', 'Valor Global', 'Valor Máximo/Projeto',
                'Data Limite', 'Contrapartida (%)', 'Nível TRL', 'PDF Principal',
                'URL Original', 'Status', 'Data Coleta'
            ]
            
            for col, header in enumerate(headers):
                worksheet.write(0, col, header, header_format)
                worksheet.set_column(col, col, 20)
            
            # Dados
            for row, resultado in enumerate(resultados, 1):
                values = [
                    resultado.get('ID', ''),
                    resultado.get('Nome_da_Chamada', ''),
                    resultado.get('Valor_Global_Disponivel', ''),
                    resultado.get('Valor_Maximo_Por_Projeto', ''),
                    resultado.get('Data_Limite_Submissao', ''),
                    resultado.get('Percentual_Contrapartida', ''),
                    resultado.get('Nivel_TRL_Exigido', ''),
                    resultado.get('URL_PDF_Principal', ''),
                    resultado.get('URL_Original', ''),
                    resultado.get('Status_Processamento', ''),
                    resultado.get('Data_Coleta', '')
                ]
                
                for col, value in enumerate(values):
                    clean_value = clean_csv_data(str(value))
                    worksheet.write(row, col, clean_value, cell_format)
            
            workbook.close()
            print(f"📊 Versão Excel criada: {excel_filename}")
            
        except ImportError:
            print("ℹ️ xlsxwriter não disponível - apenas CSV gerado")
        except Exception as e:
            print(f"⚠️ Erro ao criar Excel: {e}")