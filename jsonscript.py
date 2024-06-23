import json
import requests
from bs4 import BeautifulSoup

# Converto i nomi delle dimensioni di Hofstede utilizzati nella pagina HTML in nomi più brevi.
DIM_NAMES_CONVERSIONS = {
    "power-distance": "pdi",
    "individualism": "idv",
    "motivation": "mas",
    "uncertainty-avoidance": "uai",
    "long-term-orientation": "lto",
    "indulgence": "ivr"
}

url = "https://www.hofstede-insights.com/country-comparison-tool"
# Effettuo la richiesta HTTP.
response = requests.get(url)

# Verifico che la richiesta sia andata a buon fine.
if response.status_code == 200:
    soup = BeautifulSoup(response.text, "html.parser")
else:
    print("Request Error. Status code:", response.status_code)
    exit(1)

countries_dimensions = {}
# Estraggo solo i div che riguardano i paesi di cui ottenere i valori delle 6 dimensioni di Hofstede.
countries_div = soup.find_all("div", class_="c-overview", attrs={"data-country": True})
# (Ogni div corrisponde ad uno specifico paese).
for div in countries_div:
    # Ottengo il nome del paese.
    country = div.get("data-country").title()
    country_dimensions = {}
    for element in div.find_all("span")[:6]:
        dim_name = element.get("class")[0]
        if element.text.strip() == "":
            dim_value = None
        else:
            dim_value = int(element.text.strip())
        country_dimensions[DIM_NAMES_CONVERSIONS[dim_name]] = dim_value
        countries_dimensions[country] = country_dimensions

# Creo il file JSON con all'interno tutti i paesi analizzati e i rispettivi valori delle dimensioni di Hofstede.
with open('hofstede.json', 'w', encoding='utf-8') as file:
    json.dump(countries_dimensions, file, ensure_ascii=False, indent=2)
