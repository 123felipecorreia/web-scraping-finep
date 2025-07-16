import requests
from bs4 import BeautifulSoup

url = 'https://www.finep.gov.br/chamadas-publicas'

response = requests.get(url)
soup = BeautifulSoup(response.content, 'html.parser')

#Exemplo: pegar títulos de chamadas públicas
chamadas = soup.find_all('h3')  # Ajustar conforme estrutura real do site
for chamada in chamadas:
    print(chamada.text.strip())
