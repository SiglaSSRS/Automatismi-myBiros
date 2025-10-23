###   W S   S U G A R   C R M   #######################################
#
# Autore                Denis Cattai
# Ultima modifica       18/12/2023
# Versione Python       3.9.12
# Descrizione           Modulo per utilizzo WS SugarCRM
#
# Note
# WIP


###   I M P O R T   ###################################################

import base64
from datetime import datetime as dt
import os
from pathlib import Path
import requests
from requests.auth import HTTPBasicAuth


###   C O S T A N T I   ###############################################

xml = "C:/users/orion/Automatismi/WS/SugarCRM/xml/" # cartella in cui vengono salvate request e response
Path(xml).mkdir(parents = True, exist_ok = True) # se non esiste, viene creata


urlTkn = "https://crm.siglacredit.eu/rest/v11_16/oauth2/token"
headersTkn = {"Cache-Control": "no-cache", "Content-Type": "application//json"}
url = "https://crm.siglacredit.eu/rest/v11_16/"

clientId        = "jLL1JbaJzxp8Xyk9bn5IrES06qoa"
clientSecret    = "h0ckAhs5X5kqgsATlHblwkb1090a"
auth = HTTPBasicAuth(clientId, clientSecret)


###   F U N Z I O N I   ###############################################

def getToken():
    service = "token"
    request = {
        "grant_type":"password", 
        "client_id":"sugar", 
        "client_secret":"", 
        "username":"dcattai", 
        "password":os.environ.get("SUGARCRM"), 
        "platform":"base" 
    }

    file = dt.now().strftime("%Y%m%d_%H%M%S%f") + "_" + service + "_"
    write2file(xml + file + "request.xml", str(request)) # salva request in file xml

    try:
        response = requests.post(urlTkn, json = request) # richiesta POST
        write2file(xml + file + "response.xml", response.text) # salva response in file xml
        print(response.json())
        return response.json()["access_token"]
    except: return False

def uploadFile(token = False):
    if not token: token = getToken()
    if not token: return False

    service = "saveFilePut"
    headers = {"Content-Type": "application/document-doc", "Authorization": "Bearer " + token}
    request = {
        "method": "set_note_attachment",
        "input_type": "JSON",
        "response_type": "JSON",
        "rest_data": {
            "id": "4ccbfe80-c996-11ed-a614-0050569145a6",
            "filename": "TEST.PDF",
            "file": base64.b64encode(open("TEST.pdf", "r").read()).decode('utf-8')
            }
        }

    file = dt.now().strftime("%Y%m%d_%H%M%S%f") + "_" + service + "_"
    write2file(xml + file + "request.xml", str(request)) # salva request in file xml

    try: 
        response = requests.post(url + "Note/4ccbfe80-c996-11ed-a614-0050569145a6/file/field", headers = headers, data = request) # richiesta POST
        write2file(xml + file + "response.xml", response.text) # salva response in file xml
        response = response.json() # conversione in dict

        return response
    except: return False

def write2file(filename, string):
    f = open(filename, "w")
    f.write(string)
    f.close()


###   T E S T   #######################################################

#token = "f3ae2780-ebcc-4ece-ae86-b74f1d156f5c"
#token = getToken()

#print(uploadFile(token))