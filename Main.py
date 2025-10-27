#!/usr/bin/env python3
"""
FINEP - SISTEMA DE ANÁLISE DE CHAMADAS PÚBLICAS
Sistema modularizado para extração e análise de editais da FINEP
"""

import os
from datetime import datetime

# Importações dos nossos módulos
from core.file_manager import cleanup_old_files
from core.data_processor import DataProcessor
from utils.csv_handler import CSVHandler
from models.schemas import LinkConfig
from config.settings import USE_PLAYWRIGHT

def get_user_links() -> list:
    """Permite ao usuário registrar links para análise"""
    print("\n📋 CONFIGURAÇÃO DE LINKS PARA ANÁLISE")
    print("="*50)
    
    # Links padrão já configurados
    links_default = [
        LinkConfig(
            titulo='Chamada Nordeste',
            url='https://www.finep.gov.br/chamadas-publicas/chamadapublica/759'
        ),
        LinkConfig(
            titulo='FIP Transição Energética', 
            url='https://www.finep.gov.br/chamadas-publicas/chamadapublica/760'
        )
    ]
    
    print(f"🔗 Links padrão já configurados: {len(links_default)}")
    for i, link in enumerate(links_default, 1):
        print(f"   {i}. {link.titulo}")
        print(f"      URL: {link.url}")
    
    print("\n" + "="*50)
    print("OPÇÕES:")
    print("1. Usar apenas os links padrão")
    print("2. Adicionar novos links aos padrão")
    print("3. Usar apenas novos links (ignorar padrão)")
    
    while True:
        try:
            opcao = input("\n👆 Escolha uma opção (1-3): ").strip()
            if opcao in ['1', '2', '3']:
                break
            else:
                print("❌ Opção inválida! Digite 1, 2 ou 3.")
        except KeyboardInterrupt:
            print("\n❌ Operação cancelada pelo usuário")
            return links_default
    
    if opcao == '1':
        print("✅ Usando links padrão")
        return links_default
    
    # Para opções 2 e 3, coletar novos links
    novos_links = []
    
    print(f"\n📝 ADICIONANDO NOVOS LINKS")
    print("💡 Dica: Digite 'fim' quando terminar de adicionar links")
    print("-" * 50)
    
    contador = 1
    while True:
        print(f"\n🔗 LINK {contador}:")
        
        try:
            # Coleta título
            titulo = input("   📋 Título/Nome da chamada: ").strip()
            if titulo.lower() == 'fim':
                break
            
            if not titulo:
                print("   ⚠️ Título não pode estar vazio!")
                continue
            
            # Coleta URL
            url = input("   🌐 URL completa: ").strip()
            if url.lower() == 'fim':
                break
                
            if not url:
                print("   ⚠️ URL não pode estar vazia!")
                continue
                
            # Validação básica da URL
            if not url.startswith(('http://', 'https://')):
                print("   ⚠️ URL deve começar com http:// ou https://")
                continue
            
            # Adiciona o novo link
            novos_links.append(LinkConfig(
                titulo=titulo,
                url=url
            ))
            
            print(f"   ✅ Link {contador} adicionado: {titulo}")
            contador += 1
            
            # Pergunta se quer continuar
            if contador > 10:  # Limite de segurança
                continuar = input("\n   ❓ Adicionar mais links? (s/n): ").lower()
                if continuar not in ['s', 'sim', 'y', 'yes']:
                    break
                    
        except KeyboardInterrupt:
            print("\n❌ Adição de links cancelada")
            break
    
    # Combina links conforme a opção escolhida
    if opcao == '2':
        # Adicionar aos padrão
        links_finais = links_default + novos_links
        print(f"\n✅ Total de links: {len(links_finais)} ({len(links_default)} padrão + {len(novos_links)} novos)")
    else:
        # Usar apenas novos (opção 3)
        links_finais = novos_links
        print(f"\n✅ Total de links: {len(links_finais)} (apenas novos links)")
    
    # Exibe resumo final
    if links_finais:
        print(f"\n📋 LINKS CONFIGURADOS PARA ANÁLISE:")
        print("-" * 50)
        for i, link in enumerate(links_finais, 1):
            print(f"{i}. {link.titulo}")
            print(f"   🔗 {link.url}")
        
        confirmar = input(f"\n✅ Confirma análise de {len(links_finais)} link(s)? (s/n): ").lower()
        if confirmar in ['s', 'sim', 'y', 'yes']:
            return links_finais
        else:
            print("❌ Análise cancelada pelo usuário")
            return []
    else:
        print("⚠️ Nenhum link configurado")
        return links_default

def display_final_summary(resultados: list):
    """Exibe resumo final dos resultados"""
    print("\n" + "="*80)
    print("📊 RESUMO GERAL DOS RESULTADOS")
    print("="*80)
    
    for i, resultado in enumerate(resultados, 1):
        print(f"\n🔸 CHAMADA {i}: {resultado['Nome_da_Chamada']}")
        print(f"   💰 Valor Global: {resultado['Valor_Global_Disponivel']}")
        print(f"   💰 Valor/Projeto: {resultado['Valor_Maximo_Por_Projeto']}")
        print(f"   📅 Prazo: {resultado['Data_Limite_Submissao']}")
        print(f"   🔄 Contrapartida: {resultado['Percentual_Contrapartida']}")
        print(f"   📊 TRL: {resultado['Nivel_TRL_Exigido']}")
        print(f"   📄 PDF: {resultado['URL_PDF_Principal'].split('/')[-1] if resultado['URL_PDF_Principal'] != 'Não encontrado' else 'N/A'}")
        print(f"   ✅ Status: {resultado['Status_Processamento']}")

def main():
    print("🚀 FINEP - SISTEMA DE ANÁLISE DE CHAMADAS PÚBLICAS")
    print("🤖 Versão Modularizada - Manutenção Facilitada")
    print("="*70)
    
    # Verificações iniciais
    try:
        from openai import OpenAI
        from config.settings import OPENAI_API_KEY
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
    
    # Coleta links do usuário
    chamadas = get_user_links()
    
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
        
        print(f"\n🏁 Status Final: {resultado['Status_Processamento']}")
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