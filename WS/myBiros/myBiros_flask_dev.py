###   I M P O R T   ###################################################

#Da togliere per deploy <-----------------------------
import sys
sys.path.insert(0, r"C:\Projects\Automatismi\WS\SugarCRM")  # parent


import base64
import crmAgenti
from datetime import datetime as dt
from datetime import timezone as tz
from flask import Flask, render_template, request, session
import locale
import myBiros
import os
from pathlib import Path
import sugarcrm as crm
from typing import Optional
import unicodedata
import json
import cx_Oracle

###   L O G G E R   ###################################################

import logging
from   logging.handlers import TimedRotatingFileHandler
import werkzeug

werkzeug.serving._log_add_style = False # no formattazione nei log

logger = logging.getLogger('werkzeug')
logger.setLevel(logging.DEBUG)

# 1. Handler per file rotanti giornalieri
file_handler = TimedRotatingFileHandler("myBiros_CRM_prod.log", when="midnight", backupCount=30)
file_handler.suffix = "%Y%m%d"
file_handler.setLevel(logging.DEBUG)
file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
file_handler.setFormatter(file_formatter)

# 2. Handler per console
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)
console_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
console_handler.setFormatter(console_formatter)

# Evita doppie scritture
if not logger.handlers:
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)


###   C O S T A N T I   ###############################################

PORT = 7200

locale.setlocale(locale.LC_ALL, "it_IT")

# WS crm Agenti (produzione)
url = "https://siglacredit.lionsolution.it/service/v4/rest.php"
usr = "edp"
pwd = "Edp2010$"
# WS crm Agenti (demo)
url = "https://demosiglacredit.lionsolution.it/service/v4/rest.php"
usr = "cattai.denis"
pwd = "@Zr4ppZ34WxW"

#----------------------------------------------------------------
#CONNESSIONE DB ORACLE PROD
#----------------------------------------------------------------
DSN_CQS              = "sigladb.sigla.net/sigladb"
USERNAME_CQS         = "cqs"
PASSWORD_CQS         = "cqs"

#----------------------------------------------------------------
#DECIDERE SE PER OGNI DOCUMENTO SCARICATO e VERIFICATO CON MYBIROS
#SE SOVRASCRIVERE IL NOME E COGNOME
#----------------------------------------------------------------
SOVRASCRIVI_NOME_COGNOME = True

attachDir = "allegati" # cartella dove vengono salvati gli allegati del crm
Path(attachDir).mkdir(parents = True, exist_ok = True) # se non esiste, viene creata

#---------------------------------------------------------------------------------
#CAI = CARTA IDENTITA
#PAT = PATENTE
#PAS = PASSAPORTO
#TS  = TESSERA SANITARIA
#PS  = PERMESSO DI SOGGIORNO

#OBIS= OBIS
#BP  = BUSTA PAGA
#CP  = CEDOLINO PENSIONE
#PE  = PRIVACY ESTESA

#MC:   MERITO CREDITIZIO
#CS:   CERTIFICATO PENSIONE
#CUD:  CUD
#F24:  F24
#---------------------------------------------------------------------------------

TIPI_DOC = ["CAI", "PAT", "PAS", "TS", "BP", "OBIS", "CP", "PE", "MC", "CS", "CUD", "PS", "F24"] # mappatura documenti su CRM (provvisoria)
MIN_CONF = 0.80 # soglia confidence

###   F U N Z I O N I   ###############################################

def cerca_valore_in_db_ora(dsn, username, password, nome_tabella, campo_ricerca, campo_chiave, valore_chiave, usa_like):
    """
    Cerca il valore di un campo specifico in una tabella Oracle.
    Se usa LIKE e trova più di un record, restituisce None.
    """

    try:
        # Crea la connessione a Oracle
        conn = cx_Oracle.connect(user=username, password=password, dsn=dsn)
        cursor = conn.cursor()
        
        # Crea la query dinamicamente
        if usa_like:
            query = f"""
                SELECT {campo_ricerca} 
                FROM {nome_tabella} 
                WHERE TRIM({campo_chiave}) LIKE '%{valore_chiave}%'
            """
        else:
            query = f"""
                SELECT {campo_ricerca} 
                FROM {nome_tabella} 
                WHERE TRIM({campo_chiave}) = '{valore_chiave}'
            """
        
        # Esegui la query
        cursor.execute(query)
        results = cursor.fetchall()
        
        # Chiudi risorse
        cursor.close()
        conn.close()

        # Nessun risultato
        if not results:
            return None
        
        # Caso LIKE: se più di un record → None
        if usa_like and len(results) > 1:
            return None
        
        # Caso normale o LIKE con 1 solo risultato
        return results[0][0]

    except cx_Oracle.DatabaseError as e:
        logger.info(f"Errore durante la connessione al database: {e}")
        return None
    
def stampa_risultati_estrazione(ret, output, titolo="DEBUG – VALORI ESTRATTI"):
    print("\n# ----------------------------------------------------")
    print(f"# {titolo}")
    print("# ----------------------------------------------------")

    error_code = ret[0]
    error_detail = json.loads(ret[1].decode('utf-8'))

    # Stampa i risultati se errore
    if(error_code != 200):
        print(f"Errore myBiros {error_code}: {error_detail['detail']}")

    if not output:
        print("⚠️ Nessun risultato da mostrare.")
        print("# ----------------------------------------------------\n")
        return

    # Se output è una lista di dict, normalizza a lista di liste
    if all(isinstance(el, dict) for el in output):
        output = [output]

    for i, page_data in enumerate(output, start=1):
        print(f"\n📄 Pagina {i}:")

        if not page_data:
            print("  ⚠️ Nessun dato in questa pagina.")
            continue

        for item in page_data:
            if not isinstance(item, dict):
                print(f"  ⚠️ Elemento non valido: {item}")
                continue

            # Crea la chiave "parlante" a partire da tipo
            tipo = item.get("tipo", "—")
            key = tipo.lower().replace(" ", "_") if isinstance(tipo, str) else "—"

            valore = item.get("valore", "—")
            item_id = item.get("id", "—")

            # Gestione confidence (stringa → float)
            conf_raw = str(item.get("confidence", "0")).replace(",", ".")
            try:
                conf_val = float(conf_raw)
                conf_str = f"{conf_val:.2f}"
            except (ValueError, TypeError):
                conf_str = str(conf_raw)

            print(f"  - [{key}] {tipo}: {valore}  (conf: {conf_str}, id: {item_id})")

    print("\n# ----------------------------------------------------\n")



def scaricaAllegatiContatto(id):
    try:
        s = crm.Session(url, usr, pwd)
        notes = s.get_entry_list(crm.Note(contact_id = id)) # tutte le note collegate al contatto
        files = []
        for note in notes:
            file = s.get_note_attachment(note)["note_attachment"] # allegato
            ext = os.path.splitext(file["filename"])[1][1:].lower() # estensione del file, senza punto e in minuscolo
            #with open(os.path.join(attachDir, file["filename"]), "wb") as f: f.write(base64.b64decode(file["file"])) # salva copia in locale
            files.append({"nome": note.name, "estensione": ext, "tipo": note.description, "b64": file["file"]})

        files = [f for f in files if f["tipo"] in TIPI_DOC] # tengo solo i documenti d'interesse
        return files
    except Exception as e: logger.info(e); return False

def aggiornaContatto(id, campi):
    try: 
        session = crm.Session(url, usr, pwd)
        opportunity = session.get_entry("Contacts", id)
        for campo in campi: 
            if hasattr(opportunity, campo["nome"]):
                setattr(opportunity, campo["nome"], campo["valore"])
        session.set_entry(opportunity)
        return True
    except: return False

def analizzaDocumento(tipo, b64, estensione):
    # routing
    if      tipo in ("CAI", "PAT", "PAS", "TS", "PS"):        output, ret = myBiros.estraiDatiDocumento_b64(b64, estensione)
    elif    tipo == "BP":                                     output, ret = myBiros.estraiDatiBustaPaga_b64(b64, estensione)
    elif    tipo == "OBIS":                                   output, ret = myBiros.estraiDatiObisM_b64(b64, estensione)
    elif    tipo == "CP":                                     output, ret = myBiros.estraiDatiCedolinoPensione_b64(b64, estensione)
    elif    tipo == "PE":                                     output, ret = myBiros.estraiDatiPrivacyEstesa_b64(b64, estensione)
    elif    tipo == "MC":                                     output, ret = myBiros.estraiDatiMeritoCreditizio_b64(b64, estensione)
    elif    tipo == "CS":                                     output, ret = myBiros.estraiDatiCertificatoStipendio_b64(b64, estensione)
    elif    tipo == "CUD":                                    output, ret = myBiros.estraiDatiCUD_b64(b64, estensione)
    elif    tipo == "F24":                                    output, ret = myBiros.estraiDatiF24_b64(b64, estensione)
    else:
        return False

    #Stampa valori estratti
    stampa_risultati_estrazione(ret, output, tipo)
    return output

def to_iso_date(s: str) -> Optional[str]:
    """
    Converte stringhe data comuni in ISO YYYY-MM-DD.
    Restituisce None se non riconosce il formato.
    """
    if s is None:
        return None
    s = str(s).strip()
    if not s:
        return None

    # Già ISO?
    try:
        return dt.strptime(s, "%Y-%m-%d").strftime("%Y-%m-%d")
    except ValueError:
        pass

    # Formati europei più comuni
    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y", "%d/%m/%y", "%d-%m-%y", "%d.%m.%y"):
        try:
            return dt.strptime(s, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue

    return None

def to_bool(value):
    return str(value).strip().lower() == "true"

def add_campi(mode, campi, nome_crm, key_ocr, mappa_variabili, conf_map, isDate=False):
    """
    mode = "ai"  → prende da mappa_variabili/conf_map e applica soglia MIN_CONF
    mode = "man" → inserisce direttamente key_ocr come valore
    isDate = True → applica conversione a ISO (YYYY-MM-DD)
    """
    if mode == "man":
        val = key_ocr  # qui key_ocr è già il valore da assegnare
        if isDate:
            val = to_iso_date(val)
            if not val:
                #print(f"[add_campi] Skip {nome_crm}: data non valida")
                return
        campi.append({"nome": nome_crm, "valore": val})
        #print(f"[add_campi] {nome_crm} = {val}")
        return

    elif mode == "ai":
        val = mappa_variabili.get(key_ocr)
        conf = conf_map.get(key_ocr, 0.0)

        if not val:
            return
        if conf < MIN_CONF:
            return

        if isDate:
            val = to_iso_date(val)
            if not val:
                #print(f"[add_campi] Skip {nome_crm}: data OCR non valida")
                return

        campi.append({"nome": nome_crm, "valore": val})
        #print(f"[add_campi] {nome_crm} = {val}")
        return

    else:
        err = f"Mode non valido: {mode}"
        #print(err)
        raise ValueError(err)

def aggiornaCRM(id, ret):

    """
    # Se ret è una lista di una lista, lo "appiattisco", i documenti di riconoscimento rispetto alle altre tipologie bisogna recupeare
    # la ret[0]
    if isinstance(ret, list) and len(ret) == 1 and isinstance(ret[0], list):
        ret = ret[0]

    mappa_variabili = {}

    for campo in ret:
        nome_campo = campo["tipo"].lower().replace(" ", "_")  # esempio: "Fiscal Code" → "fiscal_code"
        valore = campo["valore"]
        mappa_variabili[nome_campo] = valore
    """

    # 1) Se arriva come [{'tipo':'OBIS','dati': [[...],[...]]}] prendo i 'dati'
    if (isinstance(ret, list) and len(ret) == 1
        and isinstance(ret[0], dict) and 'dati' in ret[0]):
        ret = ret[0]['dati']

    # 2) Appiattisco finché ci sono liste annidate (es. [[{...}], [{...}]])
    def flatten_once(seq):
        out = []
        for el in seq:
            if isinstance(el, list):
                out.extend(el)
            else:
                out.append(el)
        return out

    while isinstance(ret, list) and any(isinstance(x, list) for x in ret):
        ret = flatten_once(ret)

    # A questo punto 'ret' dovrebbe essere: [{ 'tipo':..., 'valore':... }, ...]
    mappa_variabili = {}
    for campo in (ret if isinstance(ret, list) else [ret]):
        if not isinstance(campo, dict):
            continue
        nome_campo = str(campo.get("tipo", "")).lower().replace(" ", "_")
        if not nome_campo:
            continue
        mappa_variabili[nome_campo] = campo.get("valore")

    # Costruisco una mappa delle confidenze per chiave normalizzata (tipo -> float)
    conf_map = {}
    for campo in ret:
        key = campo["tipo"].lower().replace(" ", "_")
        # la confidence arriva come stringa, la converto (gestisco eventuali virgole)
        try:
            conf_map[key] = float(str(campo.get("confidence", "0")).replace(",", "."))
        except Exception:
            conf_map[key] = 0.0
            
    #Stampa ret
    print(ret)        

    #Carta identita, Patente, Codice Fiscale, Passaporto
    #--------------------------------------------------------------------------------------------
    category_field = next((c for c in ret if c["tipo"].lower().replace(" ", "_") == "category"), None)

    #OBIS
    #--------------------------------------------------------------------------------------------
    obis_netto_pensione = next((c for c in ret if c["tipo"].lower().replace(" ", "_") == "obis_netto_pensione"), None)

    #BP BUSTA PAGA
    #--------------------------------------------------------------------------------------------
    datore_lavoro = next((c for c in ret if c["tipo"].lower().replace(" ", "_") == "datore_lavoro"), None)

    #CEDOLINO PENSIONE
    #--------------------------------------------------------------------------------------------
    categoria_pensione = next((c for c in ret if c["tipo"].lower().replace(" ", "_") == "categoria_pensione"), None)

    #MERITO CREDITIZIO
    tipo_merito = any("Ulteriore Spesa Mensile".lower() in item.get("tipo", "").lower() for item in ret)

    #CERTIFIATO STIPENDIO
    #Se presente questa tipologia di campo stiamo parlando sicuramente di un certificato di stipendio,
    #nella busta paga che contiene dati simili non e' presente questo campo spcifico.
    data_certificato = next((c for c in ret if c["tipo"].lower().replace(" ", "_") == "data_certificato"), None)

    #CUD
    #Anche qua se presente questa etichetta stiamo parlando di un documento CUD
    tipo_cud = any("TFR (".lower() in item.get("tipo", "").lower() for item in ret)

    #Per vedere i campi reali recuperari da myBiros per implementare vari tipi di documenti
    #--------------------------------------------------------------------------------------------
    logger.info(f"Valore di ret      in aggiornaCRM: {ret}")
    logger.info(f"Valore di conf_map in aggiornaCRM: {conf_map}")

    #print(ret)

    if category_field:
        category_val = str(category_field["valore"]).strip().lower()

        #CARTA DI IDENTITA --------------------------------------------------
        if category_val == "id_card":

            logger.info("DEBUG - CAMPI MAPPATI")
            logger.info(mappa_variabili)

            campi = []
        
            if(SOVRASCRIVI_NOME_COGNOME):
                add_campi("ai",     campi, "first_name",      "name",        mappa_variabili, conf_map,  isDate=False)
                add_campi("ai",     campi, "last_name",       "surname",     mappa_variabili, conf_map,  isDate=False)

            # Procedura add_campi:
            # la variabile dopo 'campi' e' il nome della colonna della tabella di CRM in questo caso: hralphas_siglacredit.contacts e contacts_cstm - > Contacts
            # ai  , inserico un chiave, valore dove valore è un valore recuperato da myBiros
            # man , inserico un chiave, valore dove valore è una stringa recuperata in altre fonti o assegnata direttamente

            #hralphas_siglacredit.contacts
            add_campi("man",    campi, "issuing_body",          "MUNICIPALITY",     mappa_variabili, conf_map,  isDate=False)
            add_campi("man",    campi, "document_type",         "CAI",              mappa_variabili, conf_map,  isDate=False)
            add_campi("ai",     campi, "release_date",          "issue_date",       mappa_variabili, conf_map,  isDate=True)
            add_campi("ai",     campi, "expiration_date",       "expire_date",      mappa_variabili, conf_map,  isDate=True)
            add_campi("ai",     campi, "document_number",       "id_number",        mappa_variabili, conf_map,  isDate=False)

            #--------------------------------------------------------------------------------------------
            #Comune di nascita
            #Esempio ->  nascita_regione_c  nascita_provincia_c     nascita_comune_c
            #            ITALIA_LOMBARDIA	ITALIA_LOMBARDIA_VA	    ITALIA_LOMBARDIA_VA_A085
            #--------------------------------------------------------------------------------------------

            birth_place = mappa_variabili["birth_place"]

            #Decodifica comune di nascita
            birth_place = (
                unicodedata.normalize("NFD", birth_place)  # separa lettere e accenti
                .encode("ascii", "ignore")                 # rimuove accenti
                .decode("ascii")                           # torna in stringa normale
                .replace("'", " ")                         # sostituisce apostrofi con spazio
                .upper()                                   # tutto maiuscolo
                .replace(" ", "_")                         # sostituisce spazi con underscore
            )

            nascita_comune_c = cerca_valore_in_db_ora(DSN_CQS, USERNAME_CQS, PASSWORD_CQS, "CRM_DECOD_COMUNI",  "COMUNE", "DESCR_COMUNE", birth_place, False)
            if(nascita_comune_c):
                parts = nascita_comune_c.split("_")
                add_campi("man", campi, "nascita_comune_c",      nascita_comune_c,       mappa_variabili, conf_map,  isDate=False)
                add_campi("man", campi, "nascita_provincia_c",   "_".join(parts[:-1]),   mappa_variabili, conf_map,  isDate=False)
                add_campi("man", campi, "nascita_regione_c",     "_".join(parts[:2]),    mappa_variabili, conf_map,  isDate=False)
                add_campi("man", campi, "nascita_nazione_c",     parts[0],               mappa_variabili, conf_map,  isDate=False)
             
            nationality = mappa_variabili["nationality"]
            if(nationality):
                if(nationality == "ITA"):
                    add_campi("man", campi, "cittadinanza_c",     "Italiana",            mappa_variabili, conf_map,  isDate=False)
                else:
                    add_campi("man", campi, "cittadinanza_c",     "NonItaliana",         mappa_variabili, conf_map,  isDate=False)

            add_campi("ai",      campi, "sesso_c",               "sex",              mappa_variabili, conf_map,  isDate=False)
            add_campi("ai",      campi, "birthdate",             "birth_date",       mappa_variabili, conf_map,  isDate=True)
            add_campi("ai",      campi, "municipality_of_issue", "issue_place",      mappa_variabili, conf_map,  isDate=False)

            issue_place = mappa_variabili["issue_place"]

            #Decodifica comune di residenza
            issue_place = (
                unicodedata.normalize("NFD", issue_place)  # separa lettere e accenti
                .encode("ascii", "ignore")                 # rimuove accenti
                .decode("ascii")                           # torna in stringa normale
                .replace("'", " ")                         # sostituisce apostrofi con spazio
                .upper()                                   # tutto maiuscolo
                .replace(" ", "_")                         # sostituisce spazi con underscore
            )

            issue_place = cerca_valore_in_db_ora(DSN_CQS, USERNAME_CQS, PASSWORD_CQS, "CRM_DECOD_COMUNI",  "COMUNE", "DESCR_COMUNE", issue_place, False)
            if(issue_place):
                parts = issue_place.split("_")
                if(parts[0] == "ITALIA"):
                     add_campi("man", campi, "residenza_nazione_c",     parts[0],             mappa_variabili, conf_map,  isDate=False)
                     add_campi("man", campi, "residenza_regione_c",     "_".join(parts[:2]),  mappa_variabili, conf_map,  isDate=False)

                     add_campi("man", campi, "residenza_provincia_c",   "_".join(parts[:3]),  mappa_variabili, conf_map,  isDate=False)
                     add_campi("man", campi, "primary_address_state",   "_".join(parts[:3]),  mappa_variabili, conf_map,  isDate=False)

                     add_campi("ai",  campi, "primary_address_city",    "residence",          mappa_variabili, conf_map,  isDate=False)
                     add_campi("man", campi, "primary_address_country", parts[0],             mappa_variabili, conf_map,  isDate=False)
                     add_campi("ai",  campi, "primary_address_street",  "address",            mappa_variabili, conf_map,  isDate=False)

                     residence = mappa_variabili["residence"]
                     ret_cap = cerca_valore_in_db_ora(DSN_CQS, USERNAME_CQS, PASSWORD_CQS, "CRM_DECOD_COMUNI_CAP",  "CAP", "COMUNE", residence, False)
                     if(ret_cap):
                        add_campi("man", campi, "primary_address_postalcode", ret_cap, mappa_variabili, conf_map,  isDate=False)

                else:
                     add_campi("man", campi, "residenza_nazione_c",     "ESTERO",         mappa_variabili, conf_map,  isDate=False)
                     add_campi("man", campi, "residenza_regione_c",     "ESTERO",         mappa_variabili, conf_map,  isDate=False)
                     add_campi("man", campi, "residenza_provincia_c",   "EE",             mappa_variabili, conf_map,  isDate=False)

            #hralphas_siglacredit.contacts
            add_campi("ai",     campi, "codice_fiscale_c",      "fiscal_code",      mappa_variabili, conf_map,  isDate=False)

            if aggiornaContatto(id, campi): logger.info("CRM AGGIORNATO")
            else: logger.error("ERRORE NELL'AGGIORNAMENTO DEL CRM")

            logger.info(f"Aggiornamento:{category_val} {campi}")

        #PATENTE --------------------------------------------------
        if category_val == "driver_license":

            logger.info("DEBUG - CAMPI MAPPATI")
            logger.info(mappa_variabili)

            campi = []

            if(SOVRASCRIVI_NOME_COGNOME):
                add_campi("ai",     campi, "first_name",      "name",        mappa_variabili, conf_map,  isDate=False)
                add_campi("ai",     campi, "last_name",       "surname",     mappa_variabili, conf_map,  isDate=False)            

            add_campi("man",campi, "issuing_body",          "MOTORIZATION_DEPARTMENT",      mappa_variabili, conf_map,  isDate=False)
            add_campi("man",campi, "document_type",         "PAT",                          mappa_variabili, conf_map,  isDate=False)                        

            add_campi("ai", campi, "document_number",       "id_number",                    mappa_variabili, conf_map,  isDate=False)
            add_campi("ai", campi, "expiration_date",       "expire_date",                  mappa_variabili, conf_map,  isDate=True)
            add_campi("ai", campi, "release_date",          "issue_date",                   mappa_variabili, conf_map,  isDate=True)
            add_campi("ai", campi, "birthdate",             "birth_date",                   mappa_variabili, conf_map,  isDate=True)
            add_campi("ai", campi, "sesso_c",               "sex",                          mappa_variabili, conf_map,  isDate=False)

            birth_place = mappa_variabili["birth_place"]

            #Decodifica comune di nascita
            birth_place = (
                unicodedata.normalize("NFD", birth_place)  # separa lettere e accenti
                .encode("ascii", "ignore")                 # rimuove accenti
                .decode("ascii")                           # torna in stringa normale
                .replace("'", " ")                         # sostituisce apostrofi con spazio
                .upper()                                   # tutto maiuscolo
                .replace(" ", "_")                         # sostituisce spazi con underscore
            )

            nascita_comune_c = cerca_valore_in_db_ora(DSN_CQS, USERNAME_CQS, PASSWORD_CQS, "CRM_DECOD_COMUNI",  "COMUNE", "DESCR_COMUNE", birth_place, False)
            if(nascita_comune_c):
                parts = nascita_comune_c.split("_")
                add_campi("man", campi, "COMUNE",      nascita_comune_c,       mappa_variabili, conf_map,  isDate=False)
                add_campi("man", campi, "nascita_provincia_c",   "_".join(parts[:-1]),   mappa_variabili, conf_map,  isDate=False)
                add_campi("man", campi, "nascita_regione_c",     "_".join(parts[:2]),    mappa_variabili, conf_map,  isDate=False)
                add_campi("man", campi, "nascita_nazione_c",     parts[0],               mappa_variabili, conf_map,  isDate=False)            

            #Forzo comunque in quando nella patente myBiros non torna nulla, e se fosse gia inserito meglio pulirlo in quanto
            #potrebbe essere presente un documento gia inserito
            add_campi("man",campi, "municipality_of_issue", " ",                            mappa_variabili, conf_map,  isDate=False)            
        
            if aggiornaContatto(id, campi): logger.info("CRM AGGIORNATO")
            else: logger.error("ERRORE NELL'AGGIORNAMENTO DEL CRM")

            logger.info(f"Aggiornamento:{category_val} {campi}")

        #PASSAPORTO --------------------------------------------------
        if category_val == "passport":

            logger.info("DEBUG - CAMPI MAPPATI")
            logger.info(mappa_variabili)

            campi = []

            if(SOVRASCRIVI_NOME_COGNOME):
                add_campi("ai",     campi, "first_name",      "name",        mappa_variabili, conf_map,  isDate=False)
                add_campi("ai",     campi, "last_name",       "surname",     mappa_variabili, conf_map,  isDate=False)               

            add_campi("man",campi, "issuing_body",          "POLICE_HEADQUARTERS",     mappa_variabili, conf_map,  isDate=False)
            add_campi("man",campi, "document_type",         "PAS",                     mappa_variabili, conf_map,  isDate=False)                        

            add_campi("ai", campi, "document_number",       "id_number",               mappa_variabili, conf_map,  isDate=False)
            add_campi("ai", campi, "expiration_date",       "expire_date",             mappa_variabili, conf_map,  isDate=True)
            add_campi("ai", campi, "release_date",          "issue_date",              mappa_variabili, conf_map,  isDate=True)
            add_campi("ai", campi, "birthdate",             "birth_date",              mappa_variabili, conf_map,  isDate=True)
            add_campi("ai", campi, "sesso_c",               "sex",                     mappa_variabili, conf_map,  isDate=False)

            #Decodifica comune di residenza
            residence = mappa_variabili["residence"]
            residence = (
                unicodedata.normalize("NFD", residence)    # separa lettere e accenti
                .encode("ascii", "ignore")                 # rimuove accenti
                .decode("ascii")                           # torna in stringa normale
                .replace("'", " ")                         # sostituisce apostrofi con spazio
                .upper()                                   # tutto maiuscolo
                .replace(" ", "_")                         # sostituisce spazi con underscore
            )

            residence = cerca_valore_in_db_ora(DSN_CQS, USERNAME_CQS, PASSWORD_CQS, "CRM_DECOD_COMUNI",  "COMUNE", "DESCR_COMUNE", residence, False)
            if(residence):
                parts = residence.split("_")
                if(parts[0] == "ITALIA"):
                     add_campi("man", campi, "residenza_nazione_c",     parts[0],             mappa_variabili, conf_map,  isDate=False)
                     add_campi("man", campi, "residenza_regione_c",     "_".join(parts[:2]),  mappa_variabili, conf_map,  isDate=False)

                     add_campi("man", campi, "residenza_provincia_c",   "_".join(parts[:3]),  mappa_variabili, conf_map,  isDate=False)
                     add_campi("man", campi, "primary_address_state",   "_".join(parts[:3]),  mappa_variabili, conf_map,  isDate=False)

                     add_campi("ai",  campi, "primary_address_city",    "residence",          mappa_variabili, conf_map,  isDate=False)
                     add_campi("man", campi, "primary_address_country", parts[0],             mappa_variabili, conf_map,  isDate=False)
                     add_campi("ai",  campi, "primary_address_street",  "address",            mappa_variabili, conf_map,  isDate=False)

                     residence = mappa_variabili["residence"]
                     ret_cap = cerca_valore_in_db_ora(DSN_CQS, USERNAME_CQS, PASSWORD_CQS, "CRM_DECOD_COMUNI_CAP",  "CAP", "COMUNE", residence, False)
                     if(ret_cap):
                        add_campi("man", campi, "primary_address_postalcode", ret_cap, mappa_variabili, conf_map,  isDate=False)

                else:
                     add_campi("man", campi, "residenza_nazione_c",     "ESTERO",         mappa_variabili, conf_map,  isDate=False)
                     add_campi("man", campi, "residenza_regione_c",     "ESTERO",         mappa_variabili, conf_map,  isDate=False)
                     add_campi("man", campi, "residenza_provincia_c",   "EE",             mappa_variabili, conf_map,  isDate=False)


            #Decodifica comune di nascita
            birth_place = mappa_variabili["birth_place"]
            birth_place = (
                unicodedata.normalize("NFD", birth_place)  # separa lettere e accenti
                .encode("ascii", "ignore")                 # rimuove accenti
                .decode("ascii")                           # torna in stringa normale
                .replace("'", " ")                         # sostituisce apostrofi con spazio
                .upper()                                   # tutto maiuscolo
                .replace(" ", "_")                         # sostituisce spazi con underscore
            )

            nascita_comune_c = cerca_valore_in_db_ora(DSN_CQS, USERNAME_CQS, PASSWORD_CQS, "CRM_DECOD_COMUNI",  "COMUNE", "DESCR_COMUNE", birth_place, False)
            if(nascita_comune_c):
                parts = nascita_comune_c.split("_")
                add_campi("man", campi, "COMUNE",      nascita_comune_c,       mappa_variabili, conf_map,  isDate=False)
                add_campi("man", campi, "nascita_provincia_c",   "_".join(parts[:-1]),   mappa_variabili, conf_map,  isDate=False)
                add_campi("man", campi, "nascita_regione_c",     "_".join(parts[:2]),    mappa_variabili, conf_map,  isDate=False)
                add_campi("man", campi, "nascita_nazione_c",     parts[0],               mappa_variabili, conf_map,  isDate=False)
             
            nationality = mappa_variabili["nationality"]
            if(nationality):
                if(nationality == "ITA"):
                    add_campi("man", campi, "cittadinanza_c",     "Italiana",            mappa_variabili, conf_map,  isDate=False)
                else:
                    add_campi("man", campi, "cittadinanza_c",     "NonItaliana",         mappa_variabili, conf_map,  isDate=False)

            #Forzo comunque in quando nella patente myBiros non torna nulla, e se fosse gia inserito meglio pulirlo in quanto
            #potrebbe essere presente un documento gia inserito
            add_campi("man",campi, "municipality_of_issue", " ",                       mappa_variabili, conf_map,  isDate=False)         
        
            if aggiornaContatto(id, campi): logger.info("CRM AGGIORNATO")
            else: logger.error("ERRORE NELL'AGGIORNAMENTO DEL CRM")    

            logger.info(f"Aggiornamento:{category_val} {campi}")

        #DOCUMENTO CODICE FISCALE --------------------------------------------------
        if category_val == "health_card":

            logger.info("DEBUG - CAMPI MAPPATI")
            logger.info(mappa_variabili)

            campi = []

            if(SOVRASCRIVI_NOME_COGNOME):
                add_campi("ai",     campi, "first_name",      "name",        mappa_variabili, conf_map,  isDate=False)
                add_campi("ai",     campi, "last_name",       "surname",     mappa_variabili, conf_map,  isDate=False)       

            add_campi("ai", campi, "codice_fiscale_c",      "fiscal_code",      mappa_variabili, conf_map,  isDate=False)
            add_campi("ai", campi, "birthdate",             "birth_date",       mappa_variabili, conf_map,  isDate=True)
            add_campi("ai", campi, "sesso_c",               "sex",              mappa_variabili, conf_map,  isDate=False)

            #Decodifica comune di nascita
            birth_place = mappa_variabili["birth_place"]
            birth_place = (
                unicodedata.normalize("NFD", birth_place)  # separa lettere e accenti
                .encode("ascii", "ignore")                 # rimuove accenti
                .decode("ascii")                           # torna in stringa normale
                .replace("'", " ")                         # sostituisce apostrofi con spazio
                .upper()                                   # tutto maiuscolo
                .replace(" ", "_")                         # sostituisce spazi con underscore
            )

            nascita_comune_c = cerca_valore_in_db_ora(DSN_CQS, USERNAME_CQS, PASSWORD_CQS, "CRM_DECOD_COMUNI",  "COMUNE", "DESCR_COMUNE", birth_place, False)
            if(nascita_comune_c):
                parts = nascita_comune_c.split("_")
                add_campi("man", campi, "COMUNE",      nascita_comune_c,       mappa_variabili, conf_map,  isDate=False)
                add_campi("man", campi, "nascita_provincia_c",   "_".join(parts[:-1]),   mappa_variabili, conf_map,  isDate=False)
                add_campi("man", campi, "nascita_regione_c",     "_".join(parts[:2]),    mappa_variabili, conf_map,  isDate=False)
                add_campi("man", campi, "nascita_nazione_c",     parts[0],               mappa_variabili, conf_map,  isDate=False)

            if aggiornaContatto(id, campi): logger.info("CRM AGGIORNATO")
            else: logger.error("ERRORE NELL'AGGIORNAMENTO DEL CRM")          
             
            logger.info(f"Aggiornamento:{category_val} {campi}")    

        #PERMESSO DI SOGGIORNO --------------------------------------------------
        if category_val == "residence_permit":            

            logger.info("DEBUG - CAMPI MAPPATI")
            logger.info(mappa_variabili)

            campi = []

            if(SOVRASCRIVI_NOME_COGNOME):
                add_campi("ai",     campi, "first_name",      "name",        mappa_variabili, conf_map,  isDate=False)
                add_campi("ai",     campi, "last_name",       "surname",     mappa_variabili, conf_map,  isDate=False)       

            add_campi("ai", campi, "sesso_c",               "sex",              mappa_variabili, conf_map,  isDate=False)
            add_campi("ai", campi, "codice_fiscale_c",      "fiscal_code",      mappa_variabili, conf_map,  isDate=False)

            nationality = mappa_variabili["nationality"]
            if(nationality):
                if(nationality == "ITA"):
                    add_campi("man", campi, "cittadinanza_c",     "Italiana",          mappa_variabili, conf_map,  isDate=False)
                else:
                    add_campi("man", campi, "cittadinanza_c",     "NonItaliana",       mappa_variabili, conf_map,  isDate=False)

            add_campi("ai", campi, "document_number",       "id_number",               mappa_variabili, conf_map,  isDate=False)
            
            add_campi("ai", campi, "release_date",          "issue_date",              mappa_variabili, conf_map,  isDate=True)            
            add_campi("ai", campi, "expiration_date",       "expire_date",             mappa_variabili, conf_map,  isDate=True)
            add_campi("ai", campi, "birthdate",             "birth_date",              mappa_variabili, conf_map,  isDate=True)
            
            birth_place = mappa_variabili["birth_place"]

            #Decodifica comune di nascita
            birth_place = (
                unicodedata.normalize("NFD", birth_place)  # separa lettere e accenti
                .encode("ascii", "ignore")                 # rimuove accenti
                .decode("ascii")                           # torna in stringa normale
                .replace("'", " ")                         # sostituisce apostrofi con spazio
                .upper()                                   # tutto maiuscolo
                .replace(" ", "_")                         # sostituisce spazi con underscore
            )

            nascita_comune_c = cerca_valore_in_db_ora(DSN_CQS, USERNAME_CQS, PASSWORD_CQS, "CRM_DECOD_COMUNI",  "COMUNE", "DESCR_COMUNE", birth_place, False)
            if(nascita_comune_c):
                parts = nascita_comune_c.split("_")
                add_campi("man", campi, "COMUNE",      nascita_comune_c,       mappa_variabili, conf_map,  isDate=False)
                add_campi("man", campi, "nascita_provincia_c",   "_".join(parts[:-1]),   mappa_variabili, conf_map,  isDate=False)
                add_campi("man", campi, "nascita_regione_c",     "_".join(parts[:2]),    mappa_variabili, conf_map,  isDate=False)
                add_campi("man", campi, "nascita_nazione_c",     parts[0],               mappa_variabili, conf_map,  isDate=False)


            if aggiornaContatto(id, campi): logger.info("CRM AGGIORNATO")
            else: logger.error("ERRORE NELL'AGGIORNAMENTO DEL CRM")          
             
            logger.info(f"Aggiornamento:{category_val} {campi}")                

    #OBIS -------------------------------------------------------
    if obis_netto_pensione:

        #--------------------------------------------------------------------------------------------
        #Tabella decodifica OBIS, data dall'ufficio commerciale
        #--------------------------------------------------------------------------------------------
        #Codice Fiscale	        Campo	codice_fiscale_c            codice_fiscale
        #Anno Retribuzione	    Campo	
        #Nome	                Campo	first_name                  -gia inseriti in crm
        #Cognome	            Campo	last_name                   -gia inseriti in crm
        #Netto Pensione	        Campo	reddito_netto_mensile_c     obis_netto_pensione
        #Categoria Pensione	    Campo	category_code_c             categoria_pensione
        #Mensilità	            Campo	
        #Chiave Pensione		Campo   certificate_number_c        chiave_pensione   
        #Lordo Pensione		    Campo    
        #Sede pensione (citta)  Campo	site_c                      sede_pensione

        logger.info("DEBUG - CAMPI MAPPATI")
        logger.info(mappa_variabili)

        campi = []

        add_campi("ai", campi, "codice_fiscale_c",          "codice_fiscale",        mappa_variabili, conf_map,  isDate=False)
        add_campi("ai", campi, "reddito_netto_mensile_c",   "netto_obis",            mappa_variabili, conf_map,  isDate=False)
        add_campi("ai", campi, "category_code_c",           "categoria_pensione",    mappa_variabili, conf_map,  isDate=False)

        #Da testare -------------------------------
        add_campi("ai", campi, "certificate_number_c",      "chiave_pensione",       mappa_variabili, conf_map,  isDate=False)
        add_campi("ai", campi, "site_c",                    "sede_pensione",         mappa_variabili, conf_map,  isDate=False)
        #Da testare -------------------------------

        if aggiornaContatto(id, campi): logger.info("CRM AGGIORNATO")
        else: logger.error("ERRORE NELL'AGGIORNAMENTO DEL CRM")  

        logger.info(f"Aggiornamento: OBIS {campi}")    

    #BP BUSTA PAGA
    if datore_lavoro:

        #--------------------------------------------------------------------------------------------
        #Tabella decodifica BUSTA PAGA, data dall'ufficio commerciale
        #--------------------------------------------------------------------------------------------
        #Campo	                        Tipo	CAMPI CRM                       CAMPI MYBIROS
        #Data Assunzione	            Campo	data_assunzione_c               data_assunzione
        #Codice Fiscale Dipendente	    Campo	codice_fiscale_c                codice_fiscale
        #Mese Retribuzione	            Campo	
        #Anno Retribuzione	            Campo	
        #Tipo Rapporto	                Campo	
        #Ragione Sociale Datore Lavoro	Campo	datore_lavoro_c                 datore_lavoro
        #Cognome	                    Campo	last_name                       - gia inserito in crm
        #Nome	                        Campo	first_name                      - gia inserito in crm
        #Part Time Percentuale	        Campo	
        #Cessione	                    Campo	cqs_rata_c                      cessione
        #Prestito	                    Campo	altri_prestiti_rata1_c          prestito
        #Pignoramento	                Campo	
        #Totale Trattenute	            Campo	
        #Netto	                        Campo	reddito_netto_mensile_c         netto
        #Totale Competenze	            Campo	
        #Retribuzione Lorda	            Campo	
        #Partita IVA Datore Lavoro		Campo   vat_number_c                    codice_fiscale_azienda
        #Delega/Delegazione		        Campo   delega_rata_c                   delega
        #Acconto
        #Cassa Edile
        #CIG
        #Multa/Provvedimento disciplinare
        #Paga oraria

        logger.info("DEBUG - CAMPI MAPPATI")
        logger.info(mappa_variabili)

        campi = []

        if(SOVRASCRIVI_NOME_COGNOME):
            add_campi("ai",     campi, "first_name",      "nome",        mappa_variabili, conf_map,  isDate=False)
            add_campi("ai",     campi, "last_name",       "cognome",     mappa_variabili, conf_map,  isDate=False)       

        add_campi("ai", campi, "data_assunzione_c",         "data_assunzione",              mappa_variabili, conf_map,isDate=True)
        add_campi("ai", campi, "codice_fiscale_c",          "codice_fiscale",               mappa_variabili, conf_map,isDate=False)
        add_campi("ai", campi, "datore_lavoro_c",           "datore_lavoro",                mappa_variabili, conf_map,isDate=False)
        add_campi("ai", campi, "reddito_netto_mensile_c",   "netto",                        mappa_variabili, conf_map,isDate=False)
        add_campi("ai", campi, "vat_number_c",              "codice_fiscale_azienda",       mappa_variabili, conf_map,isDate=False)

        #Da testare --------------------
        add_campi("ai", campi, "cqs_rata_c",                "cessione",                     mappa_variabili, conf_map,isDate=False)
        add_campi("ai", campi, "altri_prestiti_rata1_c",    "prestito",                     mappa_variabili, conf_map,isDate=False)
        add_campi("ai", campi, "delega_rata_c",             "delegazione_prestito",         mappa_variabili, conf_map,isDate=False)
        #Da testare --------------------

        if aggiornaContatto(id, campi): logger.info("CRM AGGIORNATO")
        else: logger.error("ERRORE NELL'AGGIORNAMENTO DEL CRM")   

        logger.info(f"Aggiornamento: BP BUSTA PAGA {campi}")    

    #CEDOLINO PENSIONE
    if categoria_pensione:

        #--------------------------------------------------------------------------------------------
        #Tabella decodifica CEDOLINO PENSIONE, data dall'ufficio commerciale
        #--------------------------------------------------------------------------------------------
        #Campo	                        Tipo	CAMPI CRM                       CAMPI MYBIROS
        #Codice Fiscale	                Campo	codice_fiscale_c                codice_fiscale
        #Periodo Retribuzione	        Campo	
        #Nome	                        Campo	first_name                      - gia inserito in crm
        #Cognome	                    Campo	last_name                       - gia inserito in crm
        #Netto	                        Campo	reddito_netto_mensile_c         netto
        #Categoria Pensione	            Campo	category_code_c                 categoria_pensione
        #Lordo		
        #Trattenuta obbligatoria		
        #Recupero obbligatorio		            altri_prestiti_rata1_c
        #Prestito		

        logger.info("DEBUG - CAMPI MAPPATI")
        logger.info(mappa_variabili)

        campi = []

        add_campi("ai", campi, "codice_fiscale_c",          "codice_fiscale",               mappa_variabili, conf_map,isDate=False)
        add_campi("ai", campi, "reddito_netto_mensile_c",   "netto",                        mappa_variabili, conf_map,isDate=False)
        add_campi("ai", campi, "category_code_c",           "categoria_pensione",           mappa_variabili, conf_map,isDate=False)        

        #Da verificare non e' facile trovare un caso con la voce prestito.....
        add_campi("ai", campi, "altri_prestiti_rata1_c",    "prestito",                     mappa_variabili, conf_map,isDate=False)     

        if aggiornaContatto(id, campi): logger.info("CRM AGGIORNATO")
        else: logger.error("ERRORE NELL'AGGIORNAMENTO DEL CRM")   

        logger.info(f"Aggiornamento: CEDOLINO PENSIONE {campi}")    


    #MERITO CREDITIZIO
    if tipo_merito:

        #--------------------------------------------------------------------------------------------
        #Tabella decodifica MERITO CREDITIZIO, data dall'ufficio commerciale
        #--------------------------------------------------------------------------------------------

        #Campo	                            Tipologia	        CAMPI CRM                           CAMPI MYBIROS
        #Nome	                                Campo	        first_name                          - gia inserito in crm  
        #Cognome	                            Campo	        last_name                           - gia inserito in crm
        #Luogo di Nascita	                    Campo	        nascita_comune_c                    
        #Data di Nascita	                    Campo   	    birthdate
        #Codice Fiscale	                        Campo	        codice_fiscale_c                     
        #Check Stato Matrimoniale	            Check	        stato_civile_c
        #Check Tipo Dipendente/Pensionato	    Check	        professione_c
        #Numero Componenti	                    Campo / Tabella	numero_componenti_c
        #con disabilità	                        Campo / Tabella	con_disabilita_c
        #figli	                                Campo / Tabella	figli_c
        #di cui minori	                        Campo / Tabella	di_cui_minori_di_3_anni_c
        #beneficiari di prestazioni	            Campo / Tabella	beneficiari_di_prestazioni_c
        #check percepimento reddito (1)	        Check	
        #check percepimento reddito (2)	        Check	
        #Check impegni finanziari	            Check	
        #Campi Impegni Tabella	                Campo / Tabella	
        #Situazioni Reddituale Nucleo Familiare	Campi	
        #Data	                                Campo 	
        #Firma Modulo	                        Firma	  

        logger.info("DEBUG - CAMPI MAPPATI")
        logger.info(mappa_variabili)

        campi = []

        #Lettura myBiros
        vedova                  = to_bool(mappa_variabili["vedovo/a"])
        coniugato_convivente    = to_bool(mappa_variabili["coniugato/convivente"])
        celibe_nubile           = to_bool(mappa_variabili["celibe/nubile"]) 
        separato_divorziato     = to_bool(mappa_variabili["separato/divorziato"])

        #Nel CRM il valore deve essere ben definito in base allo schema sotto
        if(vedova):
            add_campi("man", campi, "stato_civile_c",    "vedova",                  mappa_variabili, conf_map,  isDate=False)

        if(coniugato_convivente):
            add_campi("man", campi, "stato_civile_c",    "coniugato_convivente",    mappa_variabili, conf_map,  isDate=False)

        if(celibe_nubile):
            add_campi("man", campi, "stato_civile_c",    "celibe_nubile",           mappa_variabili, conf_map,  isDate=False)

        if(separato_divorziato): 
            add_campi("man", campi, "stato_civile_c",    "separato_divorziato",     mappa_variabili, conf_map,  isDate=False)

        add_campi("ai",  campi, "codice_fiscale_c",             "codice_fiscale",          mappa_variabili, conf_map,  isDate=False)
        add_campi("man", campi, "numero_componenti_c",          "numero_componenti",       mappa_variabili, conf_map,  isDate=False)
        add_campi("man", campi, "con_disabilita_c",             "componenti_disabilita",   mappa_variabili, conf_map,  isDate=False)
        add_campi("man", campi, "figli_c",                      "componenti_figli",        mappa_variabili, conf_map,  isDate=False)
        add_campi("man", campi, "di_cui_minori_di_3_anni_c",    "componenti_minori",       mappa_variabili, conf_map,  isDate=False)
 
        pensionato          = to_bool(mappa_variabili["pensionato"])
        dipendente_privato  = to_bool(mappa_variabili["dipendente_privato"])

        if(pensionato): 
            add_campi("man", campi, "professione_c",    "Q",     mappa_variabili, conf_map,  isDate=False)

        if(dipendente_privato): 
            add_campi("man", campi, "professione_c",    "P",     mappa_variabili, conf_map,  isDate=False)
 

        if aggiornaContatto(id, campi): logger.info("CRM AGGIORNATO")
        else: logger.error("ERRORE NELL'AGGIORNAMENTO DEL CRM")   

        logger.info(f"Aggiornamento: MERITO CREDITIZIO {campi}")    

    #CUD
    if tipo_cud:

        #--------------------------------------------------------------------------------------------
        #Tabella decodifica CUD, data dall'ufficio commerciale
        #--------------------------------------------------------------------------------------------
        #CUD	                            CAMPI CRM
        #Azienda Denominazione              -datore_lavoro_c *
        #Ritenute Irpef	                    -   
        #Data Inizio Rapporto	            -data_assunzione_c *
        #Dipendente Nome	                -first_name *
        #Reddito Pensione	                -
        #Redditi Assoggettati Totale	    -
        #Acc. Add. Com. Irpef AP	        -
        #Red. Assog. Tot. Irpef Sost	    -
        #Dipendente Genere	                -sesso_c
        #Azienda Codice Fiscale	            -vat_number_c
        #Red. Assog. Tot. Irpef	            -
        #Dipendente Codice Fiscale	        -codice_fiscale_c
        #Anno Competenza	                -
        #Giorni Detrazione	                -
        #Sal. Add. Com. Irpef AP	        -
        #Reddito T. Indeter.	            -
        #Ritenute Add. Reg. Irpef	        -
        #Dipendente Provincia Nascita	    -nascita_provincia_c
        #Reddito T. Determ.	                -
        #Dipendente Cognome	                -last_name
        #Imponibile Prev. Pensione (18)	    -
        #Acc. Add. Com. Irpef AC	        -
        #Comune Nascita Dipendente	        -nascita_comune_c
        #Dipendente Data Nascita	        -birthdate
        #Imponibile Previdenziali (4)	    -
        #TFR (809)	                        -
        #TFR (810)	                        -
        #TFR (811)	                        -
        #TFR (812)	                        -
        #TFR (813)	                        -
		
        logger.info("DEBUG - CAMPI MAPPATI")
        logger.info(mappa_variabili)

        campi = []

        if(SOVRASCRIVI_NOME_COGNOME):
            add_campi("ai",     campi, "first_name",      "dipendente_nome",        mappa_variabili, conf_map,  isDate=False)
            add_campi("ai",     campi, "last_name",       "dipendente_cognome",     mappa_variabili, conf_map,  isDate=False)               

        add_campi("ai",  campi, "datore_lavoro_c",      "azienda_denominazione",      mappa_variabili, conf_map,  isDate=False)
        add_campi("ai",  campi, "data_assunzione_c",    "data_inizio_rapporto",       mappa_variabili, conf_map,  isDate=True)
        add_campi("ai",  campi, "sesso_c",              "dipendente_genere",          mappa_variabili, conf_map,  isDate=False)
        add_campi("ai",  campi, "vat_number_c",         "azienda_codice_fiscale",     mappa_variabili, conf_map,  isDate=False)
        add_campi("ai",  campi, "codice_fiscale_c",     "dipendente_codice_fiscale",  mappa_variabili, conf_map,  isDate=False)
        add_campi("ai",  campi, "birthdate",            "dipendente_data_nascita",    mappa_variabili, conf_map,  isDate=True)

        comune_nascita_dipendente = mappa_variabili["comune_nascita_dipendente"]

        #Decodifica comune di nascita
        comune_nascita_dipendente = (
            unicodedata.normalize("NFD", comune_nascita_dipendente)  # separa lettere e accenti
            .encode("ascii", "ignore")                 # rimuove accenti
            .decode("ascii")                           # torna in stringa normale
            .replace("'", " ")                         # sostituisce apostrofi con spazio
            .upper()                                   # tutto maiuscolo
            .replace(" ", "_")                         # sostituisce spazi con underscore
        )

        comune_nascita_dipendente = cerca_valore_in_db_ora(DSN_CQS, USERNAME_CQS, PASSWORD_CQS, "CRM_DECOD_COMUNI",  "COMUNE", "DESCR_COMUNE", comune_nascita_dipendente, False)
        if(comune_nascita_dipendente):
            parts = comune_nascita_dipendente.split("_")
            add_campi("man", campi, "nascita_comune_c",      comune_nascita_dipendente,       mappa_variabili, conf_map,  isDate=False)
            add_campi("man", campi, "nascita_provincia_c",   "_".join(parts[:-1]),            mappa_variabili, conf_map,  isDate=False)
            add_campi("man", campi, "nascita_regione_c",     "_".join(parts[:2]),             mappa_variabili, conf_map,  isDate=False)
            add_campi("man", campi, "nascita_nazione_c",     parts[0],                        mappa_variabili, conf_map,  isDate=False)        


        if aggiornaContatto(id, campi): logger.info("CRM AGGIORNATO")
        else: logger.error("ERRORE NELL'AGGIORNAMENTO DEL CRM")   

        logger.info(f"Aggiornamento: CUD {campi}")    

    #CERITFICATO STIPENDIO
    if data_certificato:

        #--------------------------------------------------------------------------------------------
        #Tabella decodifica CERITFICATO STIPENDIO, data dall'ufficio commerciale
        #--------------------------------------------------------------------------------------------
        #Campo	                                Tipo	Colonna1
        #Data Certificato	                    Campo	
        #Azienda Emittente (Datore di Lavoro)	Campo	datore_lavoro_c
        #Sede Azienda	                        Campo	
        #P. IVA	                                Campo	vat_number_c
        #Nome Dipendente	                    Campo	first_name
        #Cognome Dipendente	                    Campo	last_name
        #Luogo di Nascita Dipendente	        Campo	nascita_comune_c
        #Data di Nascita Dipendente       	    Campo	birthdate
        #Codice Fiscale Dipendente	            Campo	codice_fiscale_c
        #Data Inizio Rapporto	                Campo	data_assunzione_c
        #Qualifica	                            Campo	professione_specifica_c
        #Tipo Contratto	                        Campo	
        #Tipo Rapporto	                        Campo	
        #Retribuzione Lorda	                    Campo	
        #TFR Accumulato	                        Campo	
        #Retribuzione Netta		                        reddito_netto_mensile_c
        #Cessione		                                cqs_rata_c
        #Prestito		                                altri_prestiti_rata1_c
        #Pignoramento		
        #Delega/Delegazione		                        delega_rata_c
        #CIG		
        #Cassa Edile		

        logger.info("DEBUG - CAMPI MAPPATI")
        logger.info(mappa_variabili)

        campi = []

        add_campi("ai",  campi, "datore_lavoro_c",          "datore_lavoro",            mappa_variabili, conf_map,  isDate=False)
        add_campi("ai",  campi, "codice_fiscale_c",         "codice_fiscale",           mappa_variabili, conf_map,  isDate=False)
        add_campi("ai",  campi, "data_assunzione_c",        "data_inizio_rapporto",     mappa_variabili, conf_map,  isDate=True)
        add_campi("ai",  campi, "vat_number_c",             "vat_azienda",              mappa_variabili, conf_map,  isDate=False)
        add_campi("ai",  campi, "professione_specifica_c",  "qualifica",                mappa_variabili, conf_map,  isDate=False)
        add_campi("ai",  campi, "reddito_netto_mensile_c",  "retribuzione_netta",       mappa_variabili, conf_map,  isDate=False)
        add_campi("ai",  campi, "birthdate",                "data_nascita_dipendente",  mappa_variabili, conf_map,  isDate=True)

        if aggiornaContatto(id, campi): logger.info("CRM AGGIORNATO")
        else: logger.error("ERRORE NELL'AGGIORNAMENTO DEL CRM")   

        logger.info(f"Aggiornamento: CERITFICATO STIPENDIO {campi}")  

###   M A I N   #######################################################

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY") or "you-will-never-guess" # provvisoria

@app.route('/', methods=['GET'])
def index(): 
    for key in ["id", "esito", "messaggio", "start"]: session.pop(key, None) # cancello i cookies
    session["start"] = dt.now(tz.utc) # data e ora della richiesta
    logger.info("SESSION: %s", session) # print dei cookies salvati, qui dovrebbe essere vuoto

    session["id"] = request.args.get("id") # recupero l'id del contatto dalla querystring
    return render_template("loading.html", title = "Analisi documenti")


@app.route('/result', methods=['GET'])
def result(): 
    logger.info("SESSION: %s", session) # cookies salvati
    return render_template("result.html", title = "Analisi documenti", esito = session["esito"], messaggio = session["messaggio"])


@app.route('/analizza', methods=['GET'])
def analizza():
    logger.info("SESSION: %s", session) # cookies salvati
    id = session["id"] # recupero l'id del contatto dai cookies

    documenti = scaricaAllegatiContatto(id)
    if documenti:
        output = []
        logger.info("DOCUMENTI SCARICATI: %s", len(documenti))
        for doc in documenti: 
            logger.info("%s: %s, %s", doc["nome"], doc["tipo"], doc["estensione"])

            #Una volta scarticato il documento esso viene analizzato da myBiros
            dati = analizzaDocumento(doc["tipo"], doc["b64"], doc["estensione"])

            if dati: 
                output.append({"tipo": doc["tipo"], "dati": dati})
            else:  logger.warning("ERRORE NELL'ESTRAZIONE DATI O NESSUN DATO ESTRATTO")
        if output: 
            logger.info("OUTPUT: %s", output)
            session["esito"] = "Analizzato 1 documento" if len(output) == 1 else "Analizzati " + str(len(output)) + " documenti"
            session["messaggio"] = "Ricaricare la pagina del CRM per verificare i dati estratti."

            #Ho i dati estratti da myBiros, ora aggiorno il CRM
            for doc in output: aggiornaCRM(id, doc["dati"])

        else: 
            logger.warning("DOCUMENTI SCARICATI MA NESSUN DATO ESTRATTO")
            session["esito"] = "Errore nell'estrazione o nessun dato estratto"
            session["messaggio"] = "Verificare i documenti presenti nel CRM e riprovare." 
    
    else:
        logger.warning("NESSUN DOCUMENTO SCARICATO")
        session["esito"] = "Errore nella ricerca o nessun documento trovato"
        session["messaggio"] = "Verificare i documenti presenti nel CRM e riprovare."
    
    logger.info("TEMPO ELABORAZIONE: %s", str(dt.now(tz.utc) - session["start"])[:-5]) # calcolo tempo dalla richiesta iniziale
    return documenti or []


if __name__ == '__main__': app.run(host = "0.0.0.0", port = PORT) # ip e porta dove eseguire il web server