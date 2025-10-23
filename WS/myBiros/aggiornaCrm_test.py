#aggiornaCrm.py

###   I M P O R T   ###################################################

import base64
import locale
import myBiros
import io
import os
import pandas   as pd
from   pathlib          import Path
import pymysql
from   datetime         import date, datetime, timedelta
from   sshtunnel        import SSHTunnelForwarder
from   typing           import Optional
import requests
import cx_Oracle 
import csv
import json
import sugarcrm as crm
import crmAgenti


###   C O S T A N T I   ###############################################

locale.setlocale(locale.LC_ALL, "it_IT")

# connessione MySQL CRM Agenti
sql_hostname =      "127.0.0.1"
sql_username =      "siglaitmanager"
sql_password =      "sigla@lionsolutions"
sql_main_database = ""
sql_port =          3306
ssh_host =          "18.102.27.41"
ssh_user =          "sigladbuser"
ssh_pwd =           ""
ssh_pkey =          "H:/IT/siglaitmanager.pem"
ssh_port =          22

#--------------------------------------------------------------
#CONNESSIONE DB ORACLE PROD
#----------------------------------------------------------------
DSN_CQS              = "sigladb.sigla.net/sigladb"
USERNAME_CQS         = "cqs"
PASSWORD_CQS         = "cqs"

# WS crm Agenti
url = "https://siglacredit.lionsolution.it/service/v4/rest.php"
usr = "edp"
pwd = "Edp2010$"

#Soglia Confidence
MIN_CONF = 0.80 

###   DEF DI UTILITA  ###############################################

def get_log_filename():
    """Restituisce il nome del file di log basato sulla data corrente"""
    return fr".\log\log_{datetime.now().strftime('%Y%m%d')}.log"

def print_ex(info):
    """Stampa un messaggio e lo scrive nel file di log giornaliero"""
    dt_str = datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:-3]
    log_message = f"[{dt_str}]: {info}"

    # Stampa a video
    print(log_message)

    # Assicurati che la cartella log esista
    os.makedirs(".\\log", exist_ok=True)

    # Determina il file di log del giorno
    log_filename = get_log_filename()

    # Scrive nel file di log giornaliero
    with open(log_filename, "a", encoding="utf-8") as log_file:
        log_file.write(log_message + "\n")

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
        return datetime.strptime(s, "%Y-%m-%d").strftime("%Y-%m-%d")
    except ValueError:
        pass

    # Formati europei più comuni
    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y", "%d/%m/%y", "%d-%m-%y", "%d.%m.%y"):
        try:
            dt = datetime.strptime(s, fmt)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            continue

    return None

def add_campi(mode, campi, nome_crm, key_ocr, isDate=False):
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
                print(f"[add_campi] Skip {nome_crm}: data non valida")
                return
        campi.append({"nome": nome_crm, "valore": val})
        print(f"[add_campi] {nome_crm} = {val}")
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
                print(f"[add_campi] Skip {nome_crm}: data OCR non valida")
                return

        campi.append({"nome": nome_crm, "valore": val})
        print(f"[add_campi] {nome_crm} = {val}")
        return

    else:
        err = f"Mode non valido: {mode}"
        print(err)
        raise ValueError(err)

###   DEF PRINCIPALI  ###############################################

def scaricaAllegati_Ex(id, tipo):
    attachDir = fr"allegati\{id}"  # cartella dove vengono salvati gli allegati del crm
    Path(attachDir).mkdir(parents=True, exist_ok=True)

    b64 = None
    ext = None

    try:
        session = crm.Session(url, usr, pwd)

        notes = session.get_entry_list(crm.Note(contact_id=id))
        for note in notes:
            if note.description.strip() == tipo:
                file = session.get_note_attachment(note)["note_attachment"]
                ext = os.path.splitext(file["filename"])[1][1:].lower()
                with open(os.path.join(attachDir, file["filename"]), "wb") as f:
                    f.write(base64.b64decode(file["file"]))
                b64 = file["file"]
                return b64, ext

        return None, ext

    except crm.ConnectionError as e:  # CRM non raggiungibile
        print_ex(f"CRM non raggiungibile: {e}")
        return None, ext
    except crm.CRMError as e:         # errori specifici CRM
        print_ex(f"Errore CRM: {e}")
        return None, ext
    except Exception as e:            # bug  
        print_ex(f"Bug nel codice: {e}")
        raise

if __name__ == "__main__":

    print_ex("Simulazione Download Documenti CRM")

    #DEBUG -------------------------------------------
    #In arrivo da CRM
    #-------------------------------------------------
    id   = "bc3df338-6d96-37c1-cf8e-68a599f073b7"
    #Scelta in debug, CAI o PAT, PAS, BP, OBIS, CED-PEN, PRIVACY
    tipo = "PRIVACY"

    #Una Tantum una volta a settimana/mese....
    #Sarebbe da aggiornare i codici catastali nella tabella SEDA_DECOD_COMUNI 
    #per aggiornare anche sulla tabella di crm il comune di nascita

    # A seconda del tipo documento andremo a fare chiamate diverse ...

    print_ex(f"Analisi soggetto: {id} Tipo Documento: {tipo}")

    #Lancio scarica allgati per Tipo
    #Attualmente dalla tabella hralphas_siglacredit.notes, campo description. 
    #Se il valore in description è quello atteso recupera il base64
    #Successivamente si pensa di testare partendo da una combobox da frontend.

    b64, ext = scaricaAllegati_Ex(id, tipo)

    if(b64):
        print_ex(f"Documento {tipo} rilevato.")

        #TIPO DOCUMENTO: CED-PEN
        if tipo in ("CED-PEN"):
            print_ex("CED-PEN da implementare.")        
         
        #TIPO DOCUMENTO: PRIVACY
        if tipo in ("PRIVACY"):
            print_ex("PRIVACY")        

        #TIPO DOCUMENTO: OBIS
        if tipo in ("OBIS"):

            ret = myBiros.estraiDatiObisM_b64(b64, ext)

            if(ret):
                print_ex("OBIS analizzato e valori recuperati.")

                #Campi recuperati e lancio del webservice di aggiornamento verso CRM.
                #--------------------------------------------------------------------

                mappa_variabili = {}

                for campo in ret[0]: #<<<< in questo caso è una lista di una lista
                    nome_campo = campo["tipo"].lower().replace(" ", "_")  # esempio: "Fiscal Code" → "fiscal_code"
                    valore = campo["valore"]
                    mappa_variabili[nome_campo] = valore

                
                conf_map = {}
                for campo in ret[0]: #<<<< in questo caso è una lista di una lista
                    key = campo["tipo"].lower().replace(" ", "_")
                    # la confidence arriva come stringa, la converto (gestisco eventuali virgole)
                    try:
                        conf_map[key] = float(str(campo.get("confidence", "0")).replace(",", "."))
                    except Exception:
                        conf_map[key] = 0.0

                # Costruisco una mappa delle confidenze per chiave normalizzata (tipo -> float)
                conf_map = {}
                print_ex("=== Log campi myBiros estratti ===")
                for campo in ret[0]: #<<<< in questo caso è una lista di una lista
                    key = campo["tipo"].lower().replace(" ", "_")
                    val = campo["valore"]
                    try:
                        conf = float(str(campo.get("confidence", "0")).replace(",", "."))
                    except Exception:
                        conf = 0.0
                    conf_map[key] = conf

                    print_ex(f"- {key}: {val} (conf={conf:.2f})")

                #Il campo category in OBIS non e' presente...

                campi = []

                #Tabella decodifica 
                #Campo	                Tipo	CAMPI CRM                   CAMPI MYBIROS
                #Codice Fiscale	        Campo	codice_fiscale_c            
                #Anno Retribuzione	    Campo	
                #Nome	                Campo	first_name                  -gia inseriti in crm
                #Cognome	            Campo	last_name                   -gia inseriti in crm
                #Netto Pensione	        Campo	reddito_netto_mensile_c     obis_netto_pensione
                #Categoria Pensione	    Campo	category_code_c             categoria_pensione
                #Mensilità	            Campo	
                #Chiave Pensione		Campo   certificate_number_c        ?   
                #Lordo Pensione		    Campo    
                #Sede pensione (citta)  Campo	site_c                      ?

                #Esempio campi a disposizione:
                #=== Log campi myBiros estratti ===
                #- categoria_pensione: VOCTPS (conf=99.60)
                #- obis_netto_pensione: 1691.14 (conf=88.34)
                #- anno_retribuzione: 2021 (conf=99.81)
                #- obis_mensilità: Gennaio (conf=98.26)
                #- obis_pensione_lorda: 2271.90 (conf=74.37)
                #- obis_pensione_lorda_complessiva: 2294.55 (conf=88.36)
        
                add_campi("ai", campi, "reddito_netto_mensile_c",   "obis_netto_pensione",   isDate=False)
                add_campi("ai", campi, "category_code_c",           "categoria_pensione",    isDate=False)

                # Logging
                print_ex(f"Payload campi → {campi}")

                ok = crmAgenti.aggiornaContatto(id, campi)

                if ok:
                    print_ex(f"✅ Contatto {id} aggiornato correttamente")
                else:
                    print_ex(f"❌ Errore nell'aggiornamento del contatto {id}")    


        #TIPO DOCUMENTO: BUSTA PAGA
        if tipo in ("BP"):

            ret = myBiros.estraiDatiBustaPaga_b64(b64, ext)

            if(ret):
                print_ex("Busta paga analizzata e valori recuperati.")

                #Campi recuperati e lancio del webservice di aggiornamento verso CRM.
                #--------------------------------------------------------------------

                mappa_variabili = {}

                for campo in ret:
                    nome_campo = campo["tipo"].lower().replace(" ", "_")  # esempio: "Fiscal Code" → "fiscal_code"
                    valore = campo["valore"]
                    mappa_variabili[nome_campo] = valore

                # Costruisco una mappa delle confidenze per chiave normalizzata (tipo -> float)
                conf_map = {}
                for campo in ret:
                    key = campo["tipo"].lower().replace(" ", "_")
                    # la confidence arriva come stringa, la converto (gestisco eventuali virgole)
                    try:
                        conf_map[key] = float(str(campo.get("confidence", "0")).replace(",", "."))
                    except Exception:
                        conf_map[key] = 0.0

                # Costruisco una mappa delle confidenze per chiave normalizzata (tipo -> float)
                conf_map = {}
                print_ex("=== Log campi myBiros estratti ===")
                for campo in ret:
                    key = campo["tipo"].lower().replace(" ", "_")
                    val = campo["valore"]
                    try:
                        conf = float(str(campo.get("confidence", "0")).replace(",", "."))
                    except Exception:
                        conf = 0.0
                    conf_map[key] = conf

                    print_ex(f"- {key}: {val} (conf={conf:.2f})")

                #Il campo category in busta paga non e' presente...

                campi = []

                #Tabella decodifica 
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
                #Cessione	                    Campo	cqs_rata_c                      ?
                #Prestito	                    Campo	altri_prestiti_rata1_c          ?
                #Pignoramento	                Campo	
                #Totale Trattenute	            Campo	
                #Netto	                        Campo	reddito_netto_mensile_c         netto
                #Totale Competenze	            Campo	
                #Retribuzione Lorda	            Campo	
                #Partita IVA Datore Lavoro		Campo   vat_number_c                    codice_fiscale_azienda
                #Delega/Delegazione		        Campo   delega_rata_c                   ?
                #Acconto
                #Cassa Edile
                #CIG
                #Multa/Provvedimento disciplinare
                #Paga oraria

                #Esempio campi a disposizione:
                #=== Log campi myBiros estratti ===
                #- datore_lavoro: NUOVO PASTIFICIO ITALIANO SRL (conf=98.23)
                #- codice_fiscale: DMJGRL87S16Z614N (conf=96.67)
                #- cognome: DI MAJO (conf=99.14)
                #- tipo_rapporto: Indeterminato (conf=99.00)
                #- data_assunzione: 20/03/2020 (conf=99.92)
                #- mese_retribuzione: novembre (conf=99.50)
                #- nome: GABRIELE (conf=99.41)
                #- totale_trattenute: 551.86 (conf=98.94)
                #- codice_fiscale_azienda: 02509360604 (conf=99.62)
                #- netto: 1750.00 (conf=93.91)
                #- totale_competenze: 2038.89 (conf=98.61)
                #- anno_retribuzione: 2023 (conf=99.69)
        
                add_campi("ai", campi, "data_assunzione_c",         "data_assunzione",              isDate=True)
                add_campi("ai", campi, "codice_fiscale_c",          "codice_fiscale",               isDate=False)
                add_campi("ai", campi, "datore_lavoro_c",           "datore_lavoro",                isDate=False)
                add_campi("ai", campi, "reddito_netto_mensile_c",   "netto",                        isDate=False)
                add_campi("ai", campi, "vat_number_c",              "codice_fiscale_azienda",       isDate=False)

                # Logging
                print_ex(f"Payload campi → {campi}")

                ok = crmAgenti.aggiornaContatto(id, campi)

                if ok:
                    print_ex(f"✅ Contatto {id} aggiornato correttamente")
                else:
                    print_ex(f"❌ Errore nell'aggiornamento del contatto {id}")    

        #TIPO DOCUMENTO: CARTA IDENTITA
        #TIPO DOCUMENTO: PATENTE
        #TIPO DOCUMENTO: PASSAPORTO

        if tipo in ("CAI", "PAT", "PAS"):

            ret = myBiros.estraiDatiDocumento_b64(b64, ext)

            if(ret):
                print_ex("Documento analizzato e valori recuperati.")

                #print(ret)

                #Campi recuperati e lancio del webservice di aggiornamento verso CRM.
                #--------------------------------------------------------------------

                mappa_variabili = {}

                for campo in ret:
                    nome_campo = campo["tipo"].lower().replace(" ", "_")  # esempio: "Fiscal Code" → "fiscal_code"
                    valore = campo["valore"]
                    mappa_variabili[nome_campo] = valore

                # Costruisco una mappa delle confidenze per chiave normalizzata (tipo -> float)
                conf_map = {}
                for campo in ret:
                    key = campo["tipo"].lower().replace(" ", "_")
                    # la confidence arriva come stringa, la converto (gestisco eventuali virgole)
                    try:
                        conf_map[key] = float(str(campo.get("confidence", "0")).replace(",", "."))
                    except Exception:
                        conf_map[key] = 0.0

                # Costruisco una mappa delle confidenze per chiave normalizzata (tipo -> float)
                conf_map = {}
                print_ex("=== Log campi myBiros estratti ===")
                for campo in ret:
                    key = campo["tipo"].lower().replace(" ", "_")
                    val = campo["valore"]
                    try:
                        conf = float(str(campo.get("confidence", "0")).replace(",", "."))
                    except Exception:
                        conf = 0.0
                    conf_map[key] = conf

                    print_ex(f"- {key}: {val} (conf={conf:.2f})")

                #Devo verificare se esite il campo category
                #in quanto devo identificare se patente o carta identita, poi a seconda devo mappare campi diversi.
                category_field = next((c for c in ret if c["tipo"].lower().replace(" ", "_") == "category"), None)

                if category_field:
                    category_val = str(category_field["valore"]).strip().lower()

                    #CARTA DI IDENTITA --------------------------------------------------
                    if category_val == "id_card":
                        print_ex(">> Rilevata category: id_card")

                        campi = []
                    
                        # Procedura add_campi:
                        # la variabile dopo 'campi' e' il nome della colonna della tabella di CRM in questo caso: hralphas_siglacredit.contacts e contacts_cstm - > Contacts
                        # ai  , inserico un chiave, valore dove valore è un valore recuperato da myBiros
                        # man , inserico un chiave, valore dove valore è una stringa recuperata in altre fonti o assegnata direttamente
                        print_ex("=== Log campi assegnati su CRM ===")

                        #hralphas_siglacredit.contacts
                        add_campi("man",campi, "issuing_body",          "MUNICIPALITY",     isDate=False)
                        add_campi("man",campi, "document_type",         "CAI",              isDate=False)
                        add_campi("ai", campi, "release_date",          "issue_date",       isDate=True)
                        add_campi("ai", campi, "expiration_date",       "expire_date",      isDate=True)
                        add_campi("ai", campi, "document_number",       "id_number",        isDate=False)
                        add_campi("ai", campi, "sesso_c",               "sex",              isDate=False)

                        #Comune di nascita
                        #Qui in base al contenuto di birth_place, bisognerebbe trovare il codice catastale e formattare per bene: nascita_comune_c
                        #Esempio ->  nascita_regione_c  nascita_provincia_c     nascita_comune_c
                        #            ITALIA_LOMBARDIA	ITALIA_LOMBARDIA_VA	    ITALIA_LOMBARDIA_VA_A085

                        #->> add_campi("ai", campi, "nascita_comune_c",      "birth_place",      isDate=False)

                        add_campi("ai", campi, "birthdate",             "birth_date",       isDate=True)
                        add_campi("ai", campi, "municipality_of_issue", "issue_place",      isDate=False)

                        #hralphas_siglacredit.contacts
                        add_campi("ai", campi, "codice_fiscale_c",      "fiscal_code",      isDate=False)

                        # Logging
                        print_ex(f"Payload campi → {campi}")

                        ok = crmAgenti.aggiornaContatto(id, campi)

                        if ok:
                            print_ex(f"✅ Contatto {id} aggiornato correttamente")
                        else:
                            print_ex(f"❌ Errore nell'aggiornamento del contatto {id}")                        

                    #PATENTE --------------------------------------------------
                    elif category_val == "driver_license":
                        print_ex(f">> Rilevata category: {category_val}")

                        campi = []

                        add_campi("man",campi, "issuing_body",          "MOTORIZATION_DEPARTMENT",     isDate=False)
                        add_campi("man",campi, "document_type",         "PAT",                         isDate=False)                        

                        add_campi("ai", campi, "document_number",       "id_number",        isDate=False)
                        add_campi("ai", campi, "expiration_date",       "expire_date",      isDate=True)
                        add_campi("ai", campi, "release_date",          "issue_date",       isDate=True)
                        add_campi("ai", campi, "birthdate",             "birth_date",       isDate=True)
                        add_campi("ai", campi, "sesso_c",               "sex",              isDate=False)

                        #Forzo comunque in quando nella patente myBiros non torna nulla, e se fosse gia inserito meglio pulirlo in quanto
                        #potrebbe essere presente un documento gia inserito
                        add_campi("man",campi, "municipality_of_issue", " ",                isDate=False)

                        # Logging
                        print_ex(f"Payload campi → {campi}")

                        ok = crmAgenti.aggiornaContatto(id, campi)

                        if ok:
                            print_ex(f"✅ Contatto {id} aggiornato correttamente")
                        else:
                            print_ex(f"❌ Errore nell'aggiornamento del contatto {id}")        
                    
                    #PASSAPORTO --------------------------------------------------
                    elif category_val == "passport":
                        print_ex(f">> Rilevata category: {category_val}")

                        campi = []

                        add_campi("man",campi, "issuing_body",          "POLICE_HEADQUARTERS",     isDate=False)
                        add_campi("man",campi, "document_type",         "PAS",                     isDate=False)                        

                        add_campi("ai", campi, "document_number",       "id_number",        isDate=False)
                        add_campi("ai", campi, "expiration_date",       "expire_date",      isDate=True)
                        add_campi("ai", campi, "release_date",          "issue_date",       isDate=True)
                        add_campi("ai", campi, "birthdate",             "birth_date",       isDate=True)
                        add_campi("ai", campi, "sesso_c",               "sex",              isDate=False)

                        #Forzo comunque in quando nella patente myBiros non torna nulla, e se fosse gia inserito meglio pulirlo in quanto
                        #potrebbe essere presente un documento gia inserito
                        add_campi("man",campi, "municipality_of_issue", " ",                isDate=False)

                        # Logging
                        print_ex(f"Payload campi → {campi}")

                        ok = crmAgenti.aggiornaContatto(id, campi)                             

                        if ok:
                            print_ex(f"✅ Contatto {id} aggiornato correttamente")
                        else:
                            print_ex(f"❌ Errore nell'aggiornamento del contatto {id}")   


                    #DOCUMENTO CODICE FISCALE --------------------------------------------------
                    elif category_val == "health_card":
                        print_ex(f">> Rilevata category: {category_val}")

                        campi = []

                        add_campi("ai", campi, "codice_fiscale_c",      "fiscal_code",      isDate=False)
                        add_campi("ai", campi, "birthdate",             "birth_date",       isDate=True)
                        add_campi("ai", campi, "sesso_c",               "sex",              isDate=False)

                        # Logging
                        print_ex(f"Payload campi → {campi}")

                        ok = crmAgenti.aggiornaContatto(id, campi)                             

                        if ok:
                            print_ex(f"✅ Contatto {id} aggiornato correttamente")
                        else:
                            print_ex(f"❌ Errore nell'aggiornamento del contatto {id}")                               

                    else:
                        print_ex(f">> Category presente ma non riconosciuta: {category_val}")
                else:
                    print_ex(">> Nessun campo category trovato")

        else:
            print_ex("[estraiDatiDocumento_b64]: Estrazione documenti fallita !")

    else:
        print_ex(f"Nessun documento {tipo} rilevato.")


    print_ex(f"Fine Procedura")    