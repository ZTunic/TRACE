import json
import csv
from datetime import datetime
import pycountry
import numpy as np


def getHofstedeCulturalDispersion(contributors_data, json_file_path, owner, repo):
    # Apro il file JSON contenente i paesi e i relativi valori delle 6 dimensioni di Hofstede.
    with open(json_file_path, "r", encoding="utf-8") as file:
        countries_data = json.load(file)

    # Estraggo i contributors.
    contributors = contributors_data["contributors"]

    # Inizializzo un dizionario contenente 6 liste. Ogni lista corrisponde ad una specifica dimensione di Hofstede e sarà utilizzata per memorizzare
    # il valore associato a quella dimensione di ogni contributor.
    hofstede_values_lists = {
        "pdi": [],
        "idv": [],
        "mas": [],
        "uai": [],
        "lto": [],
        "ivr": []
    }
    # Inizializzo una lista che conterrà i paesi predetti di ogni contributor da utilizzare per l'export in formato CSV.
    contributors_country = []
    for contributor in contributors:
        country_iso = None
        # Estraggo L'ISO 3166-1 alpha-2 del paese predetto dal Tool TRACE.
        if contributor.get("prediction"):
            country_iso = contributor["prediction"]["estimatedCountry"]
        contributors_country.append(country_iso)
        if country_iso is not None and pycountry.countries.get(alpha_2=country_iso) is not None:
            # Utilizzo l'ISO precedentemente ottenuto per ottenere il nome del paese.
            country = pycountry.countries.get(alpha_2=country_iso).name.title()
            if country in countries_data:
                # Ottengo i valori delle 6 dimensioni del paese del contributor.
                country_dimensions = countries_data[country]
                # Memorizzo i valori all'interno delle liste.
                for dim_name, dim_list in hofstede_values_lists.items():
                    if country_dimensions[dim_name] is not None:
                        dim_list.append(country_dimensions[dim_name])

    # Calcolo la deviazione standard per ogni dimensione.
    # Aggiungere un controllo sul numero di valori presenti nelle liste da confrontare con il numero totale di contributor
    # (se per una data lista mancano i valori di almeno il 25% dei contributor totali, allora si esclude la dimensione corrispondente dall'analisi).
    dimensions_std = {}
    for dim_name, dim_list in hofstede_values_lists.items():
        if dim_list:
            dimensions_std[f"{dim_name}_std"] = round(np.std(dim_list), 2)
        else:
            dimensions_std[f"{dim_name}_std"] = None

    contributors_data["culturalDispersion"]["hofstedeDispersion"] = dimensions_std
    # Aggiorno il file CSV con i nuovi dati.
    updateCSV(contributors_country, dimensions_std, owner, repo)

    return dimensions_std


def updateCSV(contributors_country, dimensions_std, owner, repo):
    # Inizializzo una lista contenente i nomi delle colonne del file CSV.
    column_names = ["repo_title", "repo_owner", "date", "repo_link", "contributors_country"]
    # Aggiungo alle colonne già definite quelle relative alla dispersione culturale.
    column_names.extend(dimensions_std.keys())

    # Creo la lista che conterrà i dati della repo analizzata.
    repo_info = [repo, owner, datetime.now().strftime("%d/%m/%Y"), f"https://github.com/{owner}/{repo}", contributors_country]
    repo_info.extend(dimensions_std.values())

    # Scrivo i dati nel file CSV.
    with open("tested_repos.csv", mode='a', newline='') as csv_file:
        writer = csv.writer(csv_file, delimiter=";")
        # Se il file è vuoto (ed è quindi appena stato creato) aggiungo la riga che contiene i nomi delle colonne.
        if csv_file.tell() == 0:
            writer.writerow(column_names)
        writer.writerow(repo_info)
