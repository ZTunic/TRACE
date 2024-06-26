import time

import requests
from flask import jsonify
import json
import math
import pycountry
import numpy as np
from datetime import date, datetime

# from modules.cvToCountry import predictFromCV
from modules.locationToCountry import predictFromLocation
from modules.usernameToCountry import predictFromUsername
from modules.commitsToCountry import predictFromCommits
from modules.nameToCountry import predictFromName
from modules.hofstedeDispersion import getHofstedeCulturalDispersion

# WEIGHT of prediction for final resul, from 0.1 to 0.5
WEIGHT_NAME = 0.25
WEIGHT_USERNAME = 0.17
WEIGHT_PDFS = 0.21
WEIGHT_COMMITS = 0.16
# English is international language and commits in english aren't weighted
WEIGHT_COMMITS_EN = 0
WEIGHT_LOCATION = 0.21

# N/A limit percent to alert the noise in the info --- if update NA_LIMIT_PERCENT here, update also in Alert message in front-end (RepositoryInfo.js - MUI Alert Component)
NA_LIMIT_PERCENT = 0.3




#################################################
################## GITHUB CALL ##################
#################################################

######### get User info call GitHub API #########
def getUserGIT(username, GITHUB_API_TOKEN):
    url = f"https://api.github.com/users/{username}"
    headers = {}
    if(GITHUB_API_TOKEN == ""):
        headers = {
            "Accept": "application/vnd.github.v3+json",
        }
    else:
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "Authorization": f"token {GITHUB_API_TOKEN}"
        }

    try:
        # Do GET request to GitHub API
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        return data
    except requests.exceptions.RequestException as e:
        # If an error occured during api call
        errorFullMessage = e.args[0]
        errorCode = errorFullMessage.split(" ")[0]
        errorMessage = " ".join(errorFullMessage.split(" ")[1:])

        print(f"[GITHUB API] Error GitHub accessing user info: {e}")
        return jsonify({
            "error": errorMessage,
            "status": errorCode
        }), errorCode

################ get Readme link ################
def getRepoReadmeGIT(owner, repo, GITHUB_API_TOKEN):
    url = f"https://api.github.com/repos/{owner}/{repo}/readme"
    headers = {}
    if(GITHUB_API_TOKEN == ""):
        headers = {
            "Accept": "application/vnd.github.v3+json",
        }
    else:
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "Authorization": f"token {GITHUB_API_TOKEN}"
        }

    try:
        # Do GET request to GitHub API
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        return jsonify(data)
    except requests.exceptions.RequestException as e:
        # If an error occurred during the API call
        errorFullMessage = str(e.args[0]) if e.args else "Unknown error"

        if " " in errorFullMessage:
            errorCode = errorFullMessage.split(" ")[0]
            errorMessage = " ".join(errorFullMessage.split(" ")[1:])
        else:
            errorCode = "Unknown"
            errorMessage = errorFullMessage

        print(f"[GITHUB API] Error GitHub accessing repo info: {e}")
        return jsonify({
            "error": errorMessage,
            "status": errorCode
        }), 500

############## get Repository info ##############
def getRepoInfoGIT(owner, repo, GITHUB_API_TOKEN):
    url = f"https://api.github.com/repos/{owner}/{repo}"
    headers = {}
    if(GITHUB_API_TOKEN == ""):
        headers = {
            "Accept": "application/vnd.github.v3+json",
        }
    else:
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "Authorization": f"token {GITHUB_API_TOKEN}"
        }

    try:
        # Do GET request to GitHub API
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        return jsonify(data)
    except requests.exceptions.RequestException as e:
        # If an error occurred during the API call
        errorFullMessage = str(e.args[0]) if e.args else "Unknown error"

        if " " in errorFullMessage:
            errorCode = errorFullMessage.split(" ")[0]
            errorMessage = " ".join(errorFullMessage.split(" ")[1:])
        else:
            errorCode = "Unknown"
            errorMessage = errorFullMessage

        print(f"[GITHUB API] Error GitHub accessing repo info: {e}")
        return jsonify({
            "error": errorMessage,
            "status": errorCode
        }), 500

def getRepoContributors_Predicts(owner, repo, GITHUB_API_TOKEN, GOOGLE_API_KEY):
    page = 1
    flag = True
    minute_consecutive_requests = 0
    contributors = []
    culturalDispersion = {}

    # Recupero le informazioni sulle richieste giornaliere dal file JSON.
    with open("rpd_info.json", "r") as file:
        rpd_info = json.load(file)

    first_dr_date = rpd_info.get("first_dr_date", None)
    day_consecutive_requests = rpd_info.get("requests_counter", 0)

    if first_dr_date is None:
        first_dr_date = date.today()
    else:
        first_dr_date = datetime.strptime(first_dr_date, "%Y-%m-%d").date()

    while flag == True:

        url = f"https://api.github.com/repos/{owner}/{repo}/contributors?per_page=100&page={page}"
        headers = {}
        if(GITHUB_API_TOKEN == ""):
            headers = {
                "Accept": "application/vnd.github.v3+json",
            }
        else:
            headers = {
                "Accept": "application/vnd.github.v3+json",
                "Authorization": f"token {GITHUB_API_TOKEN}"
            }

        try:
            # Do GET request to GitHub API
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()

        except requests.exceptions.RequestException as e:
            # If an error occured during api call
            errorFullMessage = e.args[0]
            errorCode = errorFullMessage.split(" ")[0]
            errorMessage = " ".join(errorFullMessage.split(" ")[1:])

            print(f"[GITHUB API] Error GitHub accessing repo's contribur info: {e}")
            return jsonify({
                "error": errorMessage,
                "status": errorCode
            }), errorCode

        # Find all contributors info
        count = 0
        for record in data:
            count += 1
            user = getUserGIT(record['login'], GITHUB_API_TOKEN)

            if(not isinstance(user, dict) and user[0]['status'] == "403"):
                # If an error occured
                return jsonify(user[0]), user[0]['status']
            else:
                print('\n#################################')
                print(user['login'])
                print('#################################')
                contributors.append(user)

                #########################################
                ############### MODULO CV ###############
                #########################################

                ### (Modulo disattivato) ###

                # # Search CV in contributor's portfolio
                # url = user['blog']
                # pdfsPredict = predictFromCV(user['blog'], user['login'])

                #########################################
                ############ MODULO USERNAME ############
                #########################################
                username = user['login']

                # Se è passato almeno 1 giorno dalla prima delle 120 richieste
                if (date.today() - first_dr_date).days >= 1:
                    day_consecutive_requests = 0
                    first_dr_date = date.today()

                # Controllo sul numero di richieste al giorno
                if day_consecutive_requests == 120:
                    print("Raggiunto il limite di richieste giornaliere.")
                    break

                if minute_consecutive_requests > 0:
                    if time.time() - first_request_timestamp > 60:
                        minute_consecutive_requests = 0

                # Controllo sul numero di richieste al minuto.
                if minute_consecutive_requests == 3:
                    minute_consecutive_requests = 0
                    wait_time = 120
                    print("Raggiunto il limite massimo di richieste. Attendi", int(wait_time), "secondi.")
                    time.sleep(wait_time)

                if minute_consecutive_requests == 0:
                    first_request_timestamp = time.time()

                usernamePredict = predictFromUsername(username)
                minute_consecutive_requests += 1
                day_consecutive_requests += 1

                # Check if response is dict and contains 'error' key
                if usernamePredict is not None and isinstance(usernamePredict, dict) and 'error' in usernamePredict:
                    if usernamePredict.get('status') == "408":
                        print("[USERNAME PREDICT] Timeout error: ", usernamePredict.get('error'))
                    elif usernamePredict.get('status') == "403":
                        print("[USERNAME PREDICT] OpenAI API error: ", usernamePredict.get('error'))
                    else:
                        print("[USERNAME PREDICT] Unknown error: ", usernamePredict.get('error'))
                    usernamePredict = None

                #########################################
                ############ MODULO LOCATION ############
                #########################################
                locationPredict = None
                locationPredict = predictFromLocation(user['location'], user['login'])

                if locationPredict is not None and (isinstance(locationPredict, dict) and 'error' in locationPredict):
                    locationPredict = None


                #########################################
                ############# MODULO COMMIT #############
                #########################################
                # Search n commits of contributor and make prediction
                commitsPredict = predictFromCommits(user['login'], owner, repo, 3, GITHUB_API_TOKEN, GOOGLE_API_KEY)

                if(isinstance(commitsPredict, dict) and 'error' in commitsPredict):
                    # If an error occured
                    commitsPredict = None

                #########################################
                ############## MODULO NAME ##############
                #########################################
                namePredict = predictFromName(user['name'])
                if(isinstance(namePredict, dict) and 'error' in namePredict):
                    # If an error occured
                    namePredict = None

                if(usernamePredict is not None):
                    try:
                        usernamePredictJson = json.loads(usernamePredict)
                    except json.decoder.JSONDecodeError:
                        usernamePredictJson = None
                        print(f"[USERNAME PREDICT] Error decoding JSON for value: {usernamePredict}")
                    if (usernamePredictJson is not None and 'isoPredicted' in usernamePredictJson):
                            usernameIso = usernamePredictJson['isoPredicted']
                    else:
                        usernameIso = None

                else:
                    usernameIso = None
                    usernamePredictJson = None


                if(usernameIso is None or usernameIso.lower() == 'null' or len(usernameIso) > 2):
                    usernameIso = None

                nameIso = namePredict

                # (Modulo cvToCountry disattivato).
                pdfsIso = None
                # try:
                    # if pdfsPredict is not None and len(pdfsPredict) != 0:
                        # for isoPredicted of pdf: pdfsPredict[0]['isoPredicted']['isoPredicted']
                        # pdfCountIso = {}
                        # for pdf in pdfsPredict:
                            # isoValue = None
                            # if pdf['isoPredicted']:
                                # try:
                                    # isoValue = json.loads(pdf['isoPredicted'])['isoPredicted']
                                # except json.decoder.JSONDecodeError:
                                    # isoValue = None
                                    # print(f"[PDF PREDICT] Error decoding JSON for value: {pdf['isoPredicted']}")
                                    # continue  # If error occured, skip to the next iteration
                            # if isoValue is not None and isoValue.upper() != 'NULL':
                                # if isoValue in pdfCountIso:
                                    # pdfCountIso[isoValue] += 1
                                # else:
                                    # pdfCountIso[isoValue] = 1
                        # if pdfCountIso:
                            # pdfsIso = max(pdfCountIso, key=pdfCountIso.get)
                # except Exception as e:
                    # pdfsIso = None

                if commitsPredict is not None:
                    commitsIso = commitsPredict['isoDetected']
                else:
                    commitsIso = None
                locationIso = locationPredict

                print('#################################')

                calculateObj = estimateCountryContributor(nameIso, usernameIso, pdfsIso, commitsIso, locationIso)

                final = calculateObj['final']
                estimatedCountry = calculateObj['estimatedCountry']

                # Update cultural disperion var, with info of all devs
                if(estimatedCountry is None):
                    if('N/A' in culturalDispersion):
                        culturalDispersion['N/A'] += 1
                    else:
                        culturalDispersion['N/A'] = 1
                else:
                    estimatedCountry = estimatedCountry.upper()
                    if(estimatedCountry in culturalDispersion):
                        culturalDispersion[estimatedCountry] += 1
                    elif(estimatedCountry not in culturalDispersion):
                        culturalDispersion[estimatedCountry] = 1

                user['prediction'] = {
                    'name': namePredict,
                    # 'pdfs': pdfsPredict,
                    'username': usernamePredictJson,
                    'commits': commitsPredict,
                    'location': locationPredict,
                    'estimatedCountry': estimatedCountry
                }

                if(len(final) != 0):
                    final[estimatedCountry] = round(final[estimatedCountry], 2)
                    print('estimatedCountry: ', estimatedCountry, ' ', str(final[estimatedCountry]))
                else:
                    print('estimatedCountry: N/A')

                print('#################################\n')


        if(count == 100):
            page += 1
            flag = True
        else:
            flag = False

    alert = isAlertNAinRepo(culturalDispersion)
    shannon = shannonIndex(culturalDispersion)
    contributorsObj = {
        'contributors': contributors,
        'culturalDispersion': {
            'countryDisp': culturalDispersion,
            'shannonIndex': shannon['index'],
            'percentCultDisp': shannon['percent']
        },
        'alert': alert
    }
    hofstedeCulturalDispersion = getHofstedeCulturalDispersion(contributorsObj, "./hofstede.json", owner, repo)

    print('\n#################################')
    print(f'Prediction for Contributors: {culturalDispersion}')
    print(f'Shannon Index: {shannon["index"]}')
    print(f'Cultural Dispersion Percent: {shannon["percent"]}')
    print(f'Alert N/A Noise: {alert}')
    print(f'Hofstede Cultural Dispersion: {hofstedeCulturalDispersion}')
    print('#################################\n')

    with open("rpd_info.json", "w") as file:
        rpd_info["requests_counter"] = day_consecutive_requests
        rpd_info["first_dr_date"] = first_dr_date.isoformat()
        json.dump(rpd_info, file)

    try:
        # print('contributorsObj:', contributorsObj)
        return contributorsObj
    except Exception as e:
        print(f"[GENERAL ERROR] Error during final jsonify: {e}")
        return jsonify({
            "error": str(e),
            "status": "403"
        }), "403"








#################################################
################ SERVICE METHODS ################
#################################################

def estimateCountryContributor(nameIso, usernameIso, pdfsIso, commitsIso, locationIso):
    final = {}

    # Calculate estimated country for developer
    ### NAME ###
    if(nameIso is not None):
        print(f'NAME PREDICTED ({WEIGHT_NAME}): ', nameIso)
        if(nameIso in final):
            final[nameIso] += WEIGHT_NAME
        else:
            final[nameIso] = WEIGHT_NAME
    else:
        print(f'NAME PREDICTED ({WEIGHT_NAME}): ', nameIso)

    ### USERNAME ###
    print(f'USERNAME PREDICTED ({WEIGHT_USERNAME}): ', usernameIso)

    if(usernameIso is not None):
        if(usernameIso in final):
            final[usernameIso] += WEIGHT_USERNAME
        else:
            final[usernameIso] = WEIGHT_USERNAME

    ### PDFS ###
    if pdfsIso is not None:
        print(f'PDF PREDICTED ({WEIGHT_PDFS}): ', pdfsIso)
        if(pdfsIso in final):
            final[pdfsIso] += WEIGHT_PDFS
        else:
            final[pdfsIso] = WEIGHT_PDFS
    # else:
        # print(f'PDF PREDICTED ({WEIGHT_PDFS}): ', pdfsIso)

    ### COMMITS ###
    if(commitsIso is not None):
        if(commitsIso in final):
            if(commitsIso != 'EN'):
                final[commitsIso] += WEIGHT_COMMITS
        else:
            if(commitsIso != 'EN'):
                final[commitsIso] = WEIGHT_COMMITS
        print(f'COMMIT PREDICTED ({WEIGHT_COMMITS} || if EN : {WEIGHT_COMMITS_EN}): ', commitsIso)
    else:
        print(f'COMMIT PREDICTED ({WEIGHT_COMMITS} || if EN : {WEIGHT_COMMITS_EN}): ', commitsIso)

    ### LOCATION ###
    if(locationIso is not None):
        if(locationIso in final):
            final[locationIso] += WEIGHT_LOCATION
        else:
            final[locationIso] = WEIGHT_LOCATION
        print(f'LOCATION PREDICTED ({WEIGHT_LOCATION}): ', locationIso)
    else:
        print(f'LOCATION PREDICTED ({WEIGHT_LOCATION}): ', locationIso)

    print('#################################')

    if(len(final) != 0):
        estimatedCountry =  max(final, key=final.get)
    else:
       estimatedCountry = None

    calculateObj = {
        'estimatedCountry': estimatedCountry,
        'final': final
    }

    return calculateObj



def isAlertNAinRepo(culturalDispersion):
    total = sum(culturalDispersion.values())
    if("N/A" in culturalDispersion):
        countNA = culturalDispersion["N/A"]
        percentNA = countNA / total

        if(percentNA > NA_LIMIT_PERCENT):
            return True
        else:
            return False
    else:
        return False

def shannonIndex(culturalDispersion):
    total = sum(culturalDispersion.values())

    index = 0
    for value in culturalDispersion.values():
        proportion = value / total
        index += proportion * math.log(proportion)

    index = -index

    if len(culturalDispersion) > 1:
        percent = index / math.log(len(culturalDispersion)) * 100
    else:
        percent = 0



    return {
        'index':index,
        'percent': percent
    }

