import csv
import os
from typing import List, Dict
from utils.text_processor import clean_csv_data

class CSVHandler:
    @staticmethod
    def save_to_csv(resultados: List[Dict], filename: str) -> bool:
        """Salva resultados em CSV com formatação adequada"""
        try:
            # Mapeamento correto dos campos do schema para CSV
            field_mapping = {
                'id': 'ID',
                'nome_chamada': 'Nome_da_Chamada',
                'valor_global': 'Valor_Global_Disponivel',
                'valor_maximo_projeto': 'Valor_Maximo_Por_Projeto',
                'data_limite_submissao': 'Data_Limite_Submissao',
                'percentual_contrapartida': 'Percentual_Contrapartida',
                'nivel_trl_exigido': 'Nivel_TRL_Exigido',
                'url_pdf_principal': 'URL_PDF_Principal',
                'url_original': 'URL_Original',
                'status_processamento': 'Status_Processamento',
                'data_coleta': 'Data_Coleta'
            }
            
            fieldnames = list(field_mapping.values())
            
            # Converte os resultados para o formato CSV
            csv_resultados = CSVHandler._convert_to_csv_format(resultados, field_mapping)
            
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
                writer.writerows(csv_resultados)
            
            print(f"💾 PLANILHA SALVA: {filename}")
            print(f"📊 {len(csv_resultados)} registros salvos com {len(fieldnames)} colunas")
            
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
    def _convert_to_csv_format(resultados: List[Dict], field_mapping: Dict[str, str]) -> List[Dict]:
        """Converte resultados do schema para formato CSV"""
        csv_resultados = []
        
        for resultado in resultados:
            csv_resultado = {}
            
            # Mapeia cada campo do schema para o nome correto no CSV
            for schema_field, csv_field in field_mapping.items():
                # Pega o valor do resultado usando a chave do schema
                raw_value = resultado.get(schema_field, 'Não encontrado')
                # Limpa e coloca no formato CSV
                csv_resultado[csv_field] = clean_csv_data(str(raw_value))
            
            csv_resultados.append(csv_resultado)
        
        return csv_resultados
    
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
            
            # Dados - usar mapeamento correto
            field_mapping = {
                'id': 0,
                'nome_chamada': 1,
                'valor_global': 2,
                'valor_maximo_projeto': 3,
                'data_limite_submissao': 4,
                'percentual_contrapartida': 5,
                'nivel_trl_exigido': 6,
                'url_pdf_principal': 7,
                'url_original': 8,
                'status_processamento': 9,
                'data_coleta': 10
            }
            
            for row, resultado in enumerate(resultados, 1):
                for schema_field, col in field_mapping.items():
                    value = resultado.get(schema_field, 'Não encontrado')
                    clean_value = clean_csv_data(str(value))
                    worksheet.write(row, col, clean_value, cell_format)
            
            workbook.close()
            print(f"📊 Versão Excel criada: {excel_filename}")
            
        except ImportError:
            print("ℹ️ xlsxwriter não disponível - apenas CSV gerado")
        except Exception as e:
            print(f"⚠️ Erro ao criar Excel: {e}")