###   W S   M Y B I R O S   ###########################################
#
# Autore                Denis Cattai
# Ultima modifica       26/09/2025
# Versione Python       3.9.12
# Descrizione           Modulo per utilizzo WS myBiros
#
# Note                  Versione di produzione
#                       Sito web: https://platform.mybiros.com/home
#                       Utilizzare il sito per creare casi d'uso e
#                       associare Service ID e API Key per ognuno
#                       Doc: https://docs-platform.mybiros.com/v1
#


###   I M P O R T   ###################################################

import base64
import io
import mimetypes
import requests


###   C O S T A N T I   ###############################################

params = { # parametri delle chiamate API myBiros
    "include": ["service_fields"], # campi da includere nella risposta (ocr | service_fields | validation_errors)
    "document_details": "summary" # riassume i dati estratti da tutte le pagine del documento (pages | summary)
}

mimetype_file = { # mimetype dei file accettati (da file)
    "pdf":  "application/pdf",
    "png":  "image/png",
    "jpg":  "image/jpeg",
    "jpeg": "image/jpeg"
}

mimetype_b64 = { # mimetype dei file accettati (da base64)
    "JVBERi0":      "application/pdf",
    "iVBORw0KGgo":  "image/png",
    "/9j/":         "image/jpeg"
}

#Ordina una lista di dizionari in base al campo 'id' e ne seleziona uno in base alla modalità specificata.
def _pick_by_id(items, mode="min"):
    """
    Seleziona un elemento ordinando per 'id'.
    mode: "min", "max", "max-1"/"penultimo", oppure un int (es. -2).
    Gli item senza 'id' vanno in coda.
    """
    if not items:
        return None
    ordered = sorted(items, key=lambda x: (x.get("id") is None, x.get("id", 10**9)))
    if mode == "min":
        return ordered[0]
    if mode == "max":
        return ordered[-1]
    if mode in ("max-1", "penultimo"):
        return ordered[-2] if len(ordered) >= 2 else ordered[-1]
    if isinstance(mode, int):
        idx = mode if mode >= 0 else len(ordered) + mode
        return ordered[idx] if 0 <= idx < len(ordered) else ordered[-1]
    return ordered[0] 


###   CUD  ###########################################

def estraiDatiCUD_file(file):
    """
    Estrae i dati presenti in una busta paga, a partire dal percorso del file.

    :param str file: percorso del file
    :return: list con le pensioni presenti nel documento, False in caso di errore
    """

    url = f"https://platform.mybiros.com/api/v1/inference/service/c0863db3-cb42-4a5c-8a34-66e47d447727/predict" # include il Service ID del caso d'uso
    headers = {"x-api-key": "FNsVmzYR2OHNPX-Ozvy6i9FI52nss4BZMeUUuEk6", "Accept": "application/json"} # include l'API Key del caso d'uso

    with open(file, "rb") as f:
        files = {"file": (file, f, mimetypes.guess_type(file)[0]),"push_result_on_platform": (None, "never")}
        response = requests.post(url, headers=headers, params=params, files=files)

    if response.status_code == 200: 
        response = response.json(); output = []

        for field in response["service_fields"]:
            for entity in response["document_summary"]["entities"]:
                if field == entity and response["document_summary"]["entities"][entity]:
                    if type(response["document_summary"]["entities"][entity]) is list: # più valori, scelgo quello con confidence più alta
                        value = ""; confidence = 0
                        for e in response["document_summary"]["entities"][entity]:
                            if e["confidence"] > confidence: confidence = e["confidence"]; value = e["text"] # prendo il match con il valore di confidence più alto
                        output.append({"tipo": response["service_fields"][field]["tag_alias"], "valore": value, "confidence": str(confidence)})
                    else: # unico valore, lo resetituisco
                        output.append({"tipo": response["service_fields"][field]["tag_alias"], "valore": response["document_summary"]["entities"][entity]["text"], "confidence": str(response["document_summary"]["entities"][entity]["confidence"])})       
        return output
    else: return False

def estraiDatiCUD_b64(b64, estensione):
    """
    Estrae i dati presenti in una busta paga, a partire da una stringa in base64.

    :param str b64: stringa base64 del file
    :param str estensione: estensione del file
    :return: list con le pensioni presenti nel documento, False in caso di errore
    """

    url = f"https://platform.mybiros.com/api/v1/inference/service/c0863db3-cb42-4a5c-8a34-66e47d447727/predict" # include il Service ID del caso d'uso
    headers = {"x-api-key": "FNsVmzYR2OHNPX-Ozvy6i9FI52nss4BZMeUUuEk6", "Accept": "application/json"} # include l'API Key del caso d'uso

    file_bytes = base64.b64decode(b64) # creo un file virtuale a partire dal base64
    f = io.BytesIO(file_bytes)
    f.name = "documento." + estensione # necessario per farlo accettare come file

    files = {"file": (f.name, f, mimetype_file[estensione]),"push_result_on_platform": (None, "never")}
    response = requests.post(url, headers=headers, params=params, files=files)

    if response.status_code == 200: 
        response = response.json(); output = []
    
        for field in response["service_fields"]:
            for entity in response["document_summary"]["entities"]:
                if field == entity and response["document_summary"]["entities"][entity]:
                    if type(response["document_summary"]["entities"][entity]) is list: # più valori, scelgo quello con confidence più alta
                        value = ""; confidence = 0
                        for e in response["document_summary"]["entities"][entity]:
                            if e["confidence"] > confidence: confidence = e["confidence"]; value = e["text"] # prendo il match con il valore di confidence più alto
                        output.append({"tipo": response["service_fields"][field]["tag_alias"], "valore": value, "confidence": str(confidence)})
                    else: # unico valore, lo resetituisco
                        output.append({"tipo": response["service_fields"][field]["tag_alias"], "valore": response["document_summary"]["entities"][entity]["text"], "confidence": str(response["document_summary"]["entities"][entity]["confidence"])})       
        return output
    else: return False


###   F24  ###########################################

def estraiDatiF24_file(file):
    """
    Estrae i dati presenti in una busta paga, a partire dal percorso del file.

    :param str file: percorso del file
    :return: list con le pensioni presenti nel documento, False in caso di errore
    """

    url = f"https://platform.mybiros.com/api/v1/inference/service/c0863db3-cb42-4a5c-8a34-66e47d447727/predict" # include il Service ID del caso d'uso
    headers = {"x-api-key": "FNsVmzYR2OHNPX-Ozvy6i9FI52nss4BZMeUUuEk6", "Accept": "application/json"} # include l'API Key del caso d'uso

    with open(file, "rb") as f:
        files = {"file": (file, f, mimetypes.guess_type(file)[0]),"push_result_on_platform": (None, "never")}
        response = requests.post(url, headers=headers, params=params, files=files)

    if response.status_code == 200: 
        response = response.json(); output = []

        for field in response["service_fields"]:
            for entity in response["document_summary"]["entities"]:
                if field == entity and response["document_summary"]["entities"][entity]:
                    if type(response["document_summary"]["entities"][entity]) is list: # più valori, scelgo quello con confidence più alta
                        value = ""; confidence = 0
                        for e in response["document_summary"]["entities"][entity]:
                            if e["confidence"] > confidence: confidence = e["confidence"]; value = e["text"] # prendo il match con il valore di confidence più alto
                        output.append({"tipo": response["service_fields"][field]["tag_alias"], "valore": value, "confidence": str(confidence)})
                    else: # unico valore, lo resetituisco
                        output.append({"tipo": response["service_fields"][field]["tag_alias"], "valore": response["document_summary"]["entities"][entity]["text"], "confidence": str(response["document_summary"]["entities"][entity]["confidence"])})       
        return output
    else: return False

def estraiDatiF24_b64(b64, estensione):
    """
    Estrae i dati presenti in una busta paga, a partire da una stringa in base64.

    :param str b64: stringa base64 del file
    :param str estensione: estensione del file
    :return: list con le pensioni presenti nel documento, False in caso di errore
    """

    url = f"https://platform.mybiros.com/api/v1/inference/service/c0863db3-cb42-4a5c-8a34-66e47d447727/predict" # include il Service ID del caso d'uso
    headers = {"x-api-key": "FNsVmzYR2OHNPX-Ozvy6i9FI52nss4BZMeUUuEk6", "Accept": "application/json"} # include l'API Key del caso d'uso

    file_bytes = base64.b64decode(b64) # creo un file virtuale a partire dal base64
    f = io.BytesIO(file_bytes)
    f.name = "documento." + estensione # necessario per farlo accettare come file

    files = {"file": (f.name, f, mimetype_file[estensione]),"push_result_on_platform": (None, "never")}
    response = requests.post(url, headers=headers, params=params, files=files)

    if response.status_code == 200: 
        response = response.json(); output = []
    
        for field in response["service_fields"]:
            for entity in response["document_summary"]["entities"]:
                if field == entity and response["document_summary"]["entities"][entity]:
                    if type(response["document_summary"]["entities"][entity]) is list: # più valori, scelgo quello con confidence più alta
                        value = ""; confidence = 0
                        for e in response["document_summary"]["entities"][entity]:
                            if e["confidence"] > confidence: confidence = e["confidence"]; value = e["text"] # prendo il match con il valore di confidence più alto
                        output.append({"tipo": response["service_fields"][field]["tag_alias"], "valore": value, "confidence": str(confidence)})
                    else: # unico valore, lo resetituisco
                        output.append({"tipo": response["service_fields"][field]["tag_alias"], "valore": response["document_summary"]["entities"][entity]["text"], "confidence": str(response["document_summary"]["entities"][entity]["confidence"])})       
        return output
    else: return False

###   CERTIFICATO STIPENDIO  ###########################################

def estraiDatiCertificatoStipendio_file(file):
    """
    Estrae i dati presenti in una busta paga, a partire dal percorso del file.

    :param str file: percorso del file
    :return: list con le pensioni presenti nel documento, False in caso di errore
    """

    url = f"https://platform.mybiros.com/api/v1/inference/service/169d8ed6-1b81-4437-9a9f-874d0e8df02a/predict" # include il Service ID del caso d'uso
    headers = {"x-api-key": "EyeqzIyB1hWcWzCL0VZlCKmyOf1ZQZyCM5FQgSla", "Accept": "application/json"} # include l'API Key del caso d'uso

    with open(file, "rb") as f:
        files = {"file": (file, f, mimetypes.guess_type(file)[0]),"push_result_on_platform": (None, "never")}
        response = requests.post(url, headers=headers, params=params, files=files)

    if response.status_code == 200: 
        response = response.json(); output = []

        for field in response["service_fields"]:
            for entity in response["document_summary"]["entities"]:
                if field == entity and response["document_summary"]["entities"][entity]:
                    if type(response["document_summary"]["entities"][entity]) is list: # più valori, scelgo quello con confidence più alta
                        value = ""; confidence = 0
                        for e in response["document_summary"]["entities"][entity]:
                            if e["confidence"] > confidence: confidence = e["confidence"]; value = e["text"] # prendo il match con il valore di confidence più alto
                        output.append({"tipo": response["service_fields"][field]["tag_alias"], "valore": value, "confidence": str(confidence)})
                    else: # unico valore, lo resetituisco
                        output.append({"tipo": response["service_fields"][field]["tag_alias"], "valore": response["document_summary"]["entities"][entity]["text"], "confidence": str(response["document_summary"]["entities"][entity]["confidence"])})       
        return output
    else: return False

def estraiDatiCertificatoStipendio_b64(b64, estensione):
    """
    Estrae i dati presenti in una busta paga, a partire da una stringa in base64.

    :param str b64: stringa base64 del file
    :param str estensione: estensione del file
    :return: list con le pensioni presenti nel documento, False in caso di errore
    """

    url = f"https://platform.mybiros.com/api/v1/inference/service/169d8ed6-1b81-4437-9a9f-874d0e8df02a/predict" # include il Service ID del caso d'uso
    headers = {"x-api-key": "EyeqzIyB1hWcWzCL0VZlCKmyOf1ZQZyCM5FQgSla", "Accept": "application/json"} # include l'API Key del caso d'uso

    file_bytes = base64.b64decode(b64) # creo un file virtuale a partire dal base64
    f = io.BytesIO(file_bytes)
    f.name = "documento." + estensione # necessario per farlo accettare come file

    files = {"file": (f.name, f, mimetype_file[estensione]),"push_result_on_platform": (None, "never")}
    response = requests.post(url, headers=headers, params=params, files=files)

    if response.status_code == 200: 
        response = response.json(); output = []
    
        for field in response["service_fields"]:
            for entity in response["document_summary"]["entities"]:
                if field == entity and response["document_summary"]["entities"][entity]:
                    if type(response["document_summary"]["entities"][entity]) is list: # più valori, scelgo quello con confidence più alta
                        value = ""; confidence = 0
                        for e in response["document_summary"]["entities"][entity]:
                            if e["confidence"] > confidence: confidence = e["confidence"]; value = e["text"] # prendo il match con il valore di confidence più alto
                        output.append({"tipo": response["service_fields"][field]["tag_alias"], "valore": value, "confidence": str(confidence)})
                    else: # unico valore, lo resetituisco
                        output.append({"tipo": response["service_fields"][field]["tag_alias"], "valore": response["document_summary"]["entities"][entity]["text"], "confidence": str(response["document_summary"]["entities"][entity]["confidence"])})       
        return output
    else: return False


###   MERITO CREDITIZIO  ###########################################

def estraiDatiMeritoCreditizio_file(file):
    """
    Estrae i dati presenti in una busta paga, a partire dal percorso del file.

    :param str file: percorso del file
    :return: list con le pensioni presenti nel documento, False in caso di errore
    """

    url = f"https://platform.mybiros.com/api/v1/inference/service/ce5d1566-2481-4d2e-9bb7-fbb9a68face5/predict" # include il Service ID del caso d'uso
    headers = {"x-api-key": "2i3sqce_dH7mU18PzekHTlxiz9mlNvWt-EwB5ZJ9", "Accept": "application/json"} # include l'API Key del caso d'uso

    with open(file, "rb") as f:
        files = {"file": (file, f, mimetypes.guess_type(file)[0]),"push_result_on_platform": (None, "never")}
        response = requests.post(url, headers=headers, params=params, files=files)

    if response.status_code == 200: 
        response = response.json(); output = []

        for field in response["service_fields"]:
            for entity in response["document_summary"]["entities"]:
                if field == entity and response["document_summary"]["entities"][entity]:
                    if type(response["document_summary"]["entities"][entity]) is list: # più valori, scelgo quello con confidence più alta
                        value = ""; confidence = 0
                        for e in response["document_summary"]["entities"][entity]:
                            if e["confidence"] > confidence: confidence = e["confidence"]; value = e["text"] # prendo il match con il valore di confidence più alto
                        output.append({"tipo": response["service_fields"][field]["tag_alias"], "valore": value, "confidence": str(confidence)})
                    else: # unico valore, lo resetituisco
                        output.append({"tipo": response["service_fields"][field]["tag_alias"], "valore": response["document_summary"]["entities"][entity]["text"], "confidence": str(response["document_summary"]["entities"][entity]["confidence"])})       
        return output
    else: return False

def estraiDatiMeritoCreditizio_b64(b64, estensione):
    """
    Estrae i dati presenti in una busta paga, a partire da una stringa in base64.

    :param str b64: stringa base64 del file
    :param str estensione: estensione del file
    :return: list con le pensioni presenti nel documento, False in caso di errore
    """

    url = f"https://platform.mybiros.com/api/v1/inference/service/ce5d1566-2481-4d2e-9bb7-fbb9a68face5/predict" # include il Service ID del caso d'uso
    headers = {"x-api-key": "2i3sqce_dH7mU18PzekHTlxiz9mlNvWt-EwB5ZJ9", "Accept": "application/json"} # include l'API Key del caso d'uso

    file_bytes = base64.b64decode(b64) # creo un file virtuale a partire dal base64
    f = io.BytesIO(file_bytes)
    f.name = "documento." + estensione # necessario per farlo accettare come file

    files = {"file": (f.name, f, mimetype_file[estensione]),"push_result_on_platform": (None, "never")}
    response = requests.post(url, headers=headers, params=params, files=files)

    if response.status_code == 200: 
        response = response.json(); output = []
    
        for field in response["service_fields"]:
            for entity in response["document_summary"]["entities"]:
                if field == entity and response["document_summary"]["entities"][entity]:
                    if type(response["document_summary"]["entities"][entity]) is list: # più valori, scelgo quello con confidence più alta
                        value = ""; confidence = 0
                        for e in response["document_summary"]["entities"][entity]:
                            if e["confidence"] > confidence: confidence = e["confidence"]; value = e["text"] # prendo il match con il valore di confidence più alto
                        output.append({"tipo": response["service_fields"][field]["tag_alias"], "valore": value, "confidence": str(confidence)})
                    else: # unico valore, lo resetituisco
                        output.append({"tipo": response["service_fields"][field]["tag_alias"], "valore": response["document_summary"]["entities"][entity]["text"], "confidence": str(response["document_summary"]["entities"][entity]["confidence"])})       
        return output
    else: return False


###   CEDOLINO PENSIONE  ###########################################

def estraiDatiCedolinoPensione_file(file):
    """
    Estrae i dati presenti in una busta paga, a partire dal percorso del file.

    :param str file: percorso del file
    :return: list con le pensioni presenti nel documento, False in caso di errore
    """

    url = f"https://platform.mybiros.com/api/v1/inference/service/e15577b7-206e-4dd7-816e-36728d5885a8/predict" # include il Service ID del caso d'uso
    headers = {"x-api-key": "LfnS82Mf_xOlqI9jLMvkNJItlYg-nBLT4cgPdr6r", "Accept": "application/json"} # include l'API Key del caso d'uso

    with open(file, "rb") as f:
        files = {"file": (file, f, mimetypes.guess_type(file)[0]),"push_result_on_platform": (None, "never")}
        response = requests.post(url, headers=headers, params=params, files=files)

    if response.status_code == 200: 
        response = response.json(); output = []

        for field in response["service_fields"]:
            for entity in response["document_summary"]["entities"]:
                if field == entity and response["document_summary"]["entities"][entity]:
                    if type(response["document_summary"]["entities"][entity]) is list: # più valori, scelgo quello con confidence più alta
                        value = ""; confidence = 0
                        for e in response["document_summary"]["entities"][entity]:
                            if e["confidence"] > confidence: confidence = e["confidence"]; value = e["text"] # prendo il match con il valore di confidence più alto
                        output.append({"tipo": response["service_fields"][field]["tag_alias"], "valore": value, "confidence": str(confidence)})
                    else: # unico valore, lo resetituisco
                        output.append({"tipo": response["service_fields"][field]["tag_alias"], "valore": response["document_summary"]["entities"][entity]["text"], "confidence": str(response["document_summary"]["entities"][entity]["confidence"])})       
        return output
    else: return False

def estraiDatiCedolinoPensione_b64(b64, estensione):
    """
    Estrae i dati presenti in una busta paga, a partire da una stringa in base64.

    :param str b64: stringa base64 del file
    :param str estensione: estensione del file
    :return: list con le pensioni presenti nel documento, False in caso di errore
    """

    url = f"https://platform.mybiros.com/api/v1/inference/service/e15577b7-206e-4dd7-816e-36728d5885a8/predict" # include il Service ID del caso d'uso
    headers = {"x-api-key": "LfnS82Mf_xOlqI9jLMvkNJItlYg-nBLT4cgPdr6r", "Accept": "application/json"} # include l'API Key del caso d'uso

    file_bytes = base64.b64decode(b64) # creo un file virtuale a partire dal base64
    f = io.BytesIO(file_bytes)
    f.name = "documento." + estensione # necessario per farlo accettare come file

    files = {"file": (f.name, f, mimetype_file[estensione]),"push_result_on_platform": (None, "never")}
    response = requests.post(url, headers=headers, params=params, files=files)

    if response.status_code == 200: 
        response = response.json(); output = []
    
        for field in response["service_fields"]:
            for entity in response["document_summary"]["entities"]:
                if field == entity and response["document_summary"]["entities"][entity]:
                    if type(response["document_summary"]["entities"][entity]) is list: # più valori, scelgo quello con confidence più alta
                        value = ""; confidence = 0
                        for e in response["document_summary"]["entities"][entity]:
                            if e["confidence"] > confidence: confidence = e["confidence"]; value = e["text"] # prendo il match con il valore di confidence più alto
                        output.append({"tipo": response["service_fields"][field]["tag_alias"], "valore": value, "confidence": str(confidence)})
                    else: # unico valore, lo resetituisco
                        output.append({"tipo": response["service_fields"][field]["tag_alias"], "valore": response["document_summary"]["entities"][entity]["text"], "confidence": str(response["document_summary"]["entities"][entity]["confidence"])})       
        return output
    else: return False

###   PRIVACY ESTESA  ###########################################

def estraiDatiPrivacyEstesa_file(file):
    """
    Estrae i dati presenti in una busta paga, a partire dal percorso del file.

    :param str file: percorso del file
    :return: list con le pensioni presenti nel documento, False in caso di errore
    """

    url = f"https://platform.mybiros.com/api/v1/inference/service/c636d7e0-5dc5-4d22-b7ad-2d44b4bfea20/predict" # include il Service ID del caso d'uso
    headers = {"x-api-key": "oj94WWaIAav4wSU4ehfx7e-tpex1fH9KNd4baHrf", "Accept": "application/json"} # include l'API Key del caso d'uso

    with open(file, "rb") as f:
        files = {"file": (file, f, mimetypes.guess_type(file)[0]),"push_result_on_platform": (None, "never")}
        response = requests.post(url, headers=headers, params=params, files=files)

    if response.status_code == 200: 
        response = response.json(); output = []

        for field in response["service_fields"]:
            for entity in response["document_summary"]["entities"]:
                if field == entity and response["document_summary"]["entities"][entity]:
                    if type(response["document_summary"]["entities"][entity]) is list: # più valori, scelgo quello con confidence più alta
                        value = ""; confidence = 0
                        for e in response["document_summary"]["entities"][entity]:
                            if e["confidence"] > confidence: confidence = e["confidence"]; value = e["text"] # prendo il match con il valore di confidence più alto
                        output.append({"tipo": response["service_fields"][field]["tag_alias"], "valore": value, "confidence": str(confidence)})
                    else: # unico valore, lo resetituisco
                        output.append({"tipo": response["service_fields"][field]["tag_alias"], "valore": response["document_summary"]["entities"][entity]["text"], "confidence": str(response["document_summary"]["entities"][entity]["confidence"])})       
        return output
    else: return False

def estraiDatiPrivacyEstesa_b64(b64, estensione):
    """
    Estrae i dati presenti in una busta paga, a partire da una stringa in base64.

    :param str b64: stringa base64 del file
    :param str estensione: estensione del file
    :return: list con le pensioni presenti nel documento, False in caso di errore
    """

    url = f"https://platform.mybiros.com/api/v1/inference/service/c636d7e0-5dc5-4d22-b7ad-2d44b4bfea20/predict" # include il Service ID del caso d'uso
    headers = {"x-api-key": "oj94WWaIAav4wSU4ehfx7e-tpex1fH9KNd4baHrf", "Accept": "application/json"} # include l'API Key del caso d'uso

    file_bytes = base64.b64decode(b64) # creo un file virtuale a partire dal base64
    f = io.BytesIO(file_bytes)
    f.name = "documento." + estensione # necessario per farlo accettare come file

    files = {"file": (f.name, f, mimetype_file[estensione]),"push_result_on_platform": (None, "never")}
    response = requests.post(url, headers=headers, params=params, files=files)

    if response.status_code == 200: 
        response = response.json(); output = []
    
        for field in response["service_fields"]:
            for entity in response["document_summary"]["entities"]:
                if field == entity and response["document_summary"]["entities"][entity]:
                    if type(response["document_summary"]["entities"][entity]) is list: # più valori, scelgo quello con confidence più alta
                        value = ""; confidence = 0
                        for e in response["document_summary"]["entities"][entity]:
                            if e["confidence"] > confidence: confidence = e["confidence"]; value = e["text"] # prendo il match con il valore di confidence più alto
                        output.append({"tipo": response["service_fields"][field]["tag_alias"], "valore": value, "confidence": str(confidence)})
                    else: # unico valore, lo resetituisco
                        output.append({"tipo": response["service_fields"][field]["tag_alias"], "valore": response["document_summary"]["entities"][entity]["text"], "confidence": str(response["document_summary"]["entities"][entity]["confidence"])})       
        return output
    else: return False

###   B U S T A   P A G A   ###########################################

def estraiDatiBustaPaga_file(file):
    """
    Estrae i dati presenti in una busta paga, a partire dal percorso del file.

    :param str file: percorso del file
    :return: list con le pensioni presenti nel documento, False in caso di errore
    """

    url = f"https://platform.mybiros.com/api/v1/inference/service/cb2f96d2-a8f2-4538-bba3-363c0b74a0d4/predict" # include il Service ID del caso d'uso
    headers = {"x-api-key": "oJBu6EAh--QZ450BuRY4WjvS1T57KP6YKkwv41wx", "Accept": "application/json"} # include l'API Key del caso d'uso

    with open(file, "rb") as f:
        files = {"file": (file, f, mimetypes.guess_type(file)[0]),"push_result_on_platform": (None, "never")}
        response = requests.post(url, headers=headers, params=params, files=files)

    if response.status_code == 200: 
        response = response.json(); output = []

        for field in response["service_fields"]:
            for entity in response["document_summary"]["entities"]:
                if field == entity and response["document_summary"]["entities"][entity]:
                    if type(response["document_summary"]["entities"][entity]) is list: # più valori, scelgo quello con confidence più alta
                        value = ""; confidence = 0
                        for e in response["document_summary"]["entities"][entity]:
                            if e["confidence"] > confidence: confidence = e["confidence"]; value = e["text"] # prendo il match con il valore di confidence più alto
                        output.append({"tipo": response["service_fields"][field]["tag_alias"], "valore": value, "confidence": str(confidence)})
                    else: # unico valore, lo resetituisco
                        output.append({"tipo": response["service_fields"][field]["tag_alias"], "valore": response["document_summary"]["entities"][entity]["text"], "confidence": str(response["document_summary"]["entities"][entity]["confidence"])})       
        return output
    else: return False

def estraiDatiBustaPaga_b64(b64, estensione):
    """
    Estrae i dati presenti in una busta paga, a partire da una stringa in base64.

    :param str b64: stringa base64 del file
    :param str estensione: estensione del file
    :return: list con le pensioni presenti nel documento, False in caso di errore
    """

    url = f"https://platform.mybiros.com/api/v1/inference/service/cb2f96d2-a8f2-4538-bba3-363c0b74a0d4/predict" # include il Service ID del caso d'uso
    headers = {"x-api-key": "oJBu6EAh--QZ450BuRY4WjvS1T57KP6YKkwv41wx", "Accept": "application/json"} # include l'API Key del caso d'uso

    file_bytes = base64.b64decode(b64) # creo un file virtuale a partire dal base64
    f = io.BytesIO(file_bytes)
    f.name = "documento." + estensione # necessario per farlo accettare come file

    files = {"file": (f.name, f, mimetype_file[estensione]),"push_result_on_platform": (None, "never")}
    response = requests.post(url, headers=headers, params=params, files=files)

    if response.status_code == 200: 
        response = response.json(); output = []
    
        for field in response["service_fields"]:
            for entity in response["document_summary"]["entities"]:
                if field == entity and response["document_summary"]["entities"][entity]:
                    if type(response["document_summary"]["entities"][entity]) is list: # più valori, scelgo quello con confidence più alta
                        value = ""; confidence = 0
                        for e in response["document_summary"]["entities"][entity]:
                            if e["confidence"] > confidence: confidence = e["confidence"]; value = e["text"] # prendo il match con il valore di confidence più alto
                        output.append({"tipo": response["service_fields"][field]["tag_alias"], "valore": value, "confidence": str(confidence)})
                    else: # unico valore, lo resetituisco
                        output.append({"tipo": response["service_fields"][field]["tag_alias"], "valore": response["document_summary"]["entities"][entity]["text"], "confidence": str(response["document_summary"]["entities"][entity]["confidence"])})       
        return output
    else: return False


###   D O C U M E N T I   D ' I D E N T I T A '   #####################

def estraiDatiDocumento_file(file):
    """
    Estrae i dati presenti in un set di documenti d'identità, a partire dal percorso del file.

    :param str file: percorso del file
    :return: list con le pensioni presenti nel documento, False in caso di errore
    """

    url = f"https://platform.mybiros.com/api/v1/inference/service/7471fd22-ee8d-4512-b77b-642dec127574/predict" # include il Service ID del caso d'uso
    headers = {"x-api-key": "CDtFLxF5SQ2geVwjMb8JQiUGVGgOeAUapz1fpc_4", "Accept": "application/json"} # include l'API Key del caso d'uso

    with open(file, "rb") as f:
        files = {"file": (file, f, mimetypes.guess_type(file)[0]),"push_result_on_platform": (None, "never")}
        response = requests.post(url, headers=headers, params=params, files=files)

    if response.status_code == 200: 
        response = response.json(); output = []
        
        for field in response["service_fields"]:
            for entity in response["document_summary"]["entities"]:
                if field == entity and response["document_summary"]["entities"][entity]:
                    if type(response["document_summary"]["entities"][entity]) is list: # più valori, scelgo quello con confidence più alta
                        value = ""; confidence = 0
                        for e in response["document_summary"]["entities"][entity]:
                            if e["confidence"] > confidence: confidence = e["confidence"]; value = e["text"] # prendo il match con il valore di confidence più alto
                        output.append({"tipo": response["service_fields"][field]["tag_alias"], "valore": value, "confidence": str(confidence)})
                    else: # unico valore, lo resetituisco
                        output.append({"tipo": response["service_fields"][field]["tag_alias"], "valore": response["document_summary"]["entities"][entity]["text"], "confidence": str(response["document_summary"]["entities"][entity]["confidence"])})       
        return output
    else: return False

def estraiDatiDocumento_b64(b64, estensione):
    """
    Estrae i dati presenti in un set di documenti d'identità, a partire da una stringa in base64.

    :param str b64: stringa base64 del file
    :param str estensione: estensione del file
    :return: list con le pensioni presenti nel documento, False in caso di errore
    """

    url = f"https://platform.mybiros.com/api/v1/inference/service/7471fd22-ee8d-4512-b77b-642dec127574/predict" # include il Service ID del caso d'uso
    headers = {"x-api-key": "CDtFLxF5SQ2geVwjMb8JQiUGVGgOeAUapz1fpc_4", "Accept": "application/json"} # include l'API Key del caso d'uso

    file_bytes = base64.b64decode(b64)
    f = io.BytesIO(file_bytes)
    f.name = "documento." + estensione # necessario per farlo accettare come file

    files = {"file": (f.name, f, mimetype_file[estensione]),"push_result_on_platform": (None, "never")}
    response = requests.post(url, headers=headers, params=params, files=files)

    if response.status_code == 200: 
        response = response.json(); output = []

        for field in response["service_fields"]:
            for entity in response["document_summary"]["entities"]:
                if field == entity and response["document_summary"]["entities"][entity]:
                    if type(response["document_summary"]["entities"][entity]) is list: # più valori, scelgo quello con confidence più alta
                        value = ""; confidence = 0
                        for e in response["document_summary"]["entities"][entity]:
                            if e["confidence"] > confidence: confidence = e["confidence"]; value = e["text"] # prendo il match con il valore di confidence più alto
                        output.append({"tipo": response["service_fields"][field]["tag_alias"], "valore": value, "confidence": str(confidence)})
                    else: # unico valore, lo resetituisco
                        output.append({"tipo": response["service_fields"][field]["tag_alias"], "valore": response["document_summary"]["entities"][entity]["text"], "confidence": str(response["document_summary"]["entities"][entity]["confidence"])})       
        return output
    else: return False


###   O B I S   M   ###################################################

def calcola_valore_netto_OBIS(ret, campo, tipo, confidence=99.8):
    """
    Calcola la somma dei valori netti minimi (escludendo 'Tredicesima')
    per ciascuna pagina del risultato WS, e restituisce il tutto
    come lista annidata di dizionari JSON nel formato richiesto.
    """

    pagine = ret.get("document_pages", [])
    somma_minimi = 0.0

    for page in pagine:
        aggregati = page.get("aggregated_entities", {}).get("pension_payments_1", [])
        valori_netto = []

        for agg in aggregati:
            campi = agg.get("aggregated_fields", {})
            mese = campi.get("id_number_11", {}).get("text", "")
            netto_str = campi.get("total_5", {}).get("text", "")

            # Escludo 'Tredicesima' e valori non numerici
            if mese and "Tredicesima" not in mese and netto_str:
                try:
                    netto = float(netto_str.replace(",", "."))
                    valori_netto.append(netto)
                except ValueError:
                    continue

        if valori_netto:
            minimo_pagina = min(valori_netto)
            somma_minimi += minimo_pagina

    # Costruzione dell'output JSON nel formato richiesto
    risultato_json = [[{
        "campo": campo,
        "tipo": tipo,
        "valore": round(somma_minimi, 2),
        "confidence": confidence,
        "id": 0
    }]]

    return risultato_json

def estraiDatiObisM_file(file):
    """
    Estrae i dati presenti in un documento Obis M, a partire dal percorso del file.

    :param str file: percorso del file
    :return: list con le pensioni presenti nel documento, False in caso di errore
    """

    url = f"https://platform.mybiros.com/api/v1/inference/service/5f6f8a6c-ac77-4044-9ec7-eb491ef95f15/predict"
    headers = {"x-api-key": "7qdVqGJWylEEUAW4KY9HbWkd3AKJ2VKeTF8DTvcW", "Accept": "application/json"}

    params = { # parametri delle chiamate API myBiros
        "include": ["service_fields"], # campi da includere nella risposta
        "document_details": "pages" # output diviso per pagina
    }

    with open(file, "rb") as f:
        files = {"file": (file, f, mimetypes.guess_type(file)[0]),"push_result_on_platform": (None, "never")}
        response = requests.post(url, headers=headers, params=params, files=files)

    if response.status_code == 200: 
        response = response.json(); output = [] # output complessivo

        for page in response["document_pages"]:
            o = [] # output della singola pagina
            for field in response["service_fields"]:
                for entity in page["entities"]:
                    if field == entity and page["entities"][entity]:
                        for e in page["entities"][entity]:
                            o.append({"tipo": response["service_fields"][field]["tag_alias"], "valore": e["text"], "confidence": e["confidence"]}) 
            output.append(o)

        output = [o for o in output if "Obis Mensilità" in [x["tipo"] for x in o]] # tengo solo le pagine con campo Obis Mensilità, che corrispondo quindi al dettaglio di una pensione

        return output
    else: return False

def estraiDatiObisM_b64(b64, estensione):
    """
    Estrae i dati presenti in un documento Obis M, a partire da una stringa in base64.

    :param str b64: stringa base64 del file
    :param str estensione: estensione del file
    :return: list con le pensioni presenti nel documento, False in caso di errore
    """

    url = f"https://platform.mybiros.com/api/v1/inference/service/5f6f8a6c-ac77-4044-9ec7-eb491ef95f15/predict"
    headers = {"x-api-key": "7qdVqGJWylEEUAW4KY9HbWkd3AKJ2VKeTF8DTvcW", "Accept": "application/json"}

    params = { # parametri delle chiamate API myBiros
        "include": ["service_fields"], # campi da includere nella risposta
        "document_details": "pages" # output diviso per pagina
    }

    file_bytes = base64.b64decode(b64)
    f = io.BytesIO(file_bytes)
    f.name = "documento." + estensione # necessario per farlo accettare come file

    files = {"file": (f.name, f, mimetype_file[estensione]),"push_result_on_platform": (None, "never")}
    response = requests.post(url, headers=headers, params=params, files=files)

    if response.status_code == 200: 
        response = response.json(); output = [] # output complessivo
        
        for page in response["document_pages"]:
            o = [] # output della singola pagina
            for field in response["service_fields"]:
                for entity in page["entities"]:
                    if field == entity and page["entities"][entity]:
                        for e in page["entities"][entity]:
                            o.append({"tipo": response["service_fields"][field]["tag_alias"], "valore": e["text"], "confidence": e["confidence"]}) 
            output.append(o)

        output.append(calcola_valore_netto_OBIS(response, "netto_obis", "Netto OBIS"))

        output = [o for o in output if "Obis Mensilità" in [x["tipo"] for x in o]] # tengo solo le pagine con campo Obis Mensilità, che corrispondo quindi al dettaglio di una pensione

        return output
    else: return False


###   F U N Z I O N I   L E G A C Y   #################################
###   Utilizzate da alcuni programmi in produzione, da migrare

def estraiDatiBustaPaga(file, b64 = True):
    api_key = "oJBu6EAh--QZ450BuRY4WjvS1T57KP6YKkwv41wx"
    service_id = "cb2f96d2-a8f2-4538-bba3-363c0b74a0d4"
    url = f"https://platform.mybiros.com/api/v1/inference/service/{service_id}/predict"
    headers = {"x-api-key": api_key, "Accept": "application/json"}

    params = {"include": ["ocr", "service_fields"], "document_details": "summary"}

    if b64: # interpreto file come base64 (default)
        pdf_bytes = base64.b64decode(file)
        f = io.BytesIO(pdf_bytes)
        f.name = "documento.pdf" # necessario per farlo accettare come file
        files = {"file": ("file.pdf", f, "application/pdf"),"push_result_on_platform": (None, "never")}
        response = requests.post(url, headers=headers, params=params, files=files)
    else: # interpreto file come percorso
        with open(file, "rb") as f:
            files = {"file": (file, f, mimetypes.guess_type(file)[0]),"push_result_on_platform": (None, "never")}
            response = requests.post(url, headers=headers, params=params, files=files)

    if response.status_code == 200: 
        response = response.json(); output = []
    
        for field in response["service_fields"]:
            for entity in response["document_summary"]["entities"]:
                if field == entity and response["document_summary"]["entities"][entity]:
                    value = ""; confidence = 0
                    for e in response["document_summary"]["entities"][entity]:
                        if e["confidence"] > confidence: confidence = e["confidence"]; value = e["text"] # prendo il match con il valore più alto, ECCEZIONE PER CAMPI MULTIPLI?
                    output.append({"tipo": response["service_fields"][field]["tag_alias"], "valore": value, "confidence": str(confidence)})           
        return output
    else: return False

def estraiDatiDocumento(file, b64 = True):
    api_key = "CDtFLxF5SQ2geVwjMb8JQiUGVGgOeAUapz1fpc_4"
    service_id = "7471fd22-ee8d-4512-b77b-642dec127574"
    url = f"https://platform.mybiros.com/api/v1/inference/service/{service_id}/predict"
    headers = {"x-api-key": api_key, "Accept": "application/json"}

    params = {"include": ["ocr", "service_fields"], "document_details": "summary"}
    campiDocumento = {"Surname": "Cognome", "Name": "Nome", "Birth Date": "Data di Nascita", "Fiscal Code": "Codice Fiscale", "Sex": "Sesso", "Address": "Indirizzo", "Nationality": "Nazionalità", "Height": "Altezza", "ID Number": "Numero Documento"}

    if b64: # interpreto file come base64 (default)
        pdf_bytes = base64.b64decode(file)
        f = io.BytesIO(pdf_bytes)
        f.name = "documento.pdf" # necessario per farlo accettare come file
        files = {"file": ("file.pdf", f, "application/pdf"),"push_result_on_platform": (None, "never")}
    else: # interpreto file come percorso
        with open(file, "rb") as f:
            files = {"file": ("file.pdf", f, "application/pdf"),"push_result_on_platform": (None, "never")}

    response = requests.post(url, headers=headers, params=params, files=files)
    if response.status_code == 200: 
        response = response.json(); output = []
        #print(response)
        for campo in campiDocumento:
            for field in response["service_fields"]:
                for entity in response["document_summary"]["entities"]:
                    if field == entity and response["document_summary"]["entities"][entity]["text"] and response["service_fields"][field]["tag_alias"] == campo:
                        output.append({"tipo": campiDocumento[response["service_fields"][field]["tag_alias"]], "valore": response["document_summary"]["entities"][entity]["text"]})
                    #elif field == entity and response["service_fields"][field]["tag_alias"] == "Category" and response["document_summary"]["entities"][entity]["text"] != "id_card":
                    #    return [{"tipo": "Documento Valido", "valore": "no"}]                
        return output
    else: return False

def estraiDatiObisM(file, b64 = True):
    api_key = "7qdVqGJWylEEUAW4KY9HbWkd3AKJ2VKeTF8DTvcW"
    service_id = "5f6f8a6c-ac77-4044-9ec7-eb491ef95f15"
    url = f"https://platform.mybiros.com/api/v1/inference/service/{service_id}/predict"
    headers = {"x-api-key": api_key, "Accept": "application/json"}
    params = {"include": ["service_fields"], "document_details": "summary"}

    if b64: # interpreto file come base64 (default)
        pdf_bytes = base64.b64decode(file)
        f = io.BytesIO(pdf_bytes)
        f.name = "documento.pdf" # necessario per farlo accettare come file
    else: # interpreto file come percorso
        f = open(file, "rb")

    files = {"file": ("file.pdf", f, "application/pdf"),"push_result_on_platform": (None, "never")}
    response = requests.post(url, headers=headers, params=params, files=files)
    if not b64: f.close()

    if response.status_code == 200: 
        response = response.json(); output = []
        #print(response)
        for entity in response["document_summary"]["entities"]:
            output.append({"tipo": response["service_fields"][entity]["tag_alias"], "valore": response["document_summary"]["entities"][entity]})
        if output:
            for o in output:
                valori = []
                for v in o["valore"]:
                    if v["text"] not in valori: valori.append(v["text"])
                o["valore"] = valori
            return output
        else: return False
    else: return False


###   T E S T   #######################################################

#print(estraiDatiBustaPaga_file("bp1.pdf"))
#print(estraiDatiDocumento_file("allegati/bc3df338-6d96-37c1-cf8e-68a599f073b7/doc-codfiscale-es.pdf"))