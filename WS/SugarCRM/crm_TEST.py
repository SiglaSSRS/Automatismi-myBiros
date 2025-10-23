###   W S   S U G A R   C R M   #######################################
#
# Autore                Denis Cattai
# Ultima modifica       18/12/2023
# Versione Python       3.9.12
# Descrizione           Modulo per utilizzo WS SugarCRM
#                       Per CRM CD
#
# Note
# WIP


###   I M P O R T   ###################################################

import base64
from datetime import datetime as dt
import mimetypes
import os
from pathlib import Path
import pymysql
from sshtunnel import SSHTunnelForwarder
import sugarcrm as crm
import sys


###   C O S T A N T I   ###############################################

xml = "C:/users/orion/Automatismi/WS/SugarCRM/xml/" # cartella in cui vengono salvate request e response
Path(xml).mkdir(parents = True, exist_ok = True) # se non esiste, viene creata

url = "https://crm.siglacredit.eu/service/v4/rest.php"

usr = "dcattai"
pwd = os.environ.get("SUGARCRM")

attachDir = "allegati" # cartella dove vengono salvati gli allegati del crm
Path(attachDir).mkdir(parents = True, exist_ok = True) # se non esiste, viene creata

# connessione MySQL SugarCRM
sql_hostname = "127.0.0.1"
sql_username = "root"
sql_password = "nlT$8ejf2ltOBwbt"
sql_main_database = ""
sql_port = 3306
ssh_host = "192.168.64.41"
ssh_user = "caronte"
ssh_pwd = "_yDmkyyce6w:8A8."
ssh_port = 22


###   F U N Z I O N I   ###############################################

def aggiornaTrattativaYounited(id, esito = 200, link = "") -> bool:
    """
    Aggiorna una trattativa a seconda dell'esito fornito da Younited.

    :param str id: Id della trattativa
    :param int esito: Esito della chiamata Younited (200 default, 400, 429)
    :param str link: Link per la continuazione del funnel (default "")
    :param priority: The priority of the message, can be a number 1-5
    :return: True in caso di aggiornamento completato, False in caso di errore
    """
    try:    
        session = crm.Session(url, usr, pwd)
        o = session.get_entry("Opportunities", id)
        print([o.fase_c, o.dettaglio_stato_c, o.sales_stage, o.fase_stato_codifica_c, o.fase_stato_dettaglio_codifica_c, o.stato_lavorazione_scp_c, o.nota_lavorazione_scp_c, o.scp_c, o.abi_filiale_c])
        
        if esito == 200 and not link:
            o.fase_c = "D"
            o.dettaglio_stato_c = "Non fattibile"
            o.sales_stage = "Closed Lost"
            o.fase_stato_codifica_c = "D2_5"
            o.fase_stato_dettaglio_codifica_c = "D2"
            o.stato_lavorazione_scp_c = "9"
            o.nota_lavorazione_scp_c = "KO YOUNITED\n" + o.nota_lavorazione_scp_c if o.nota_lavorazione_scp_c else "KO YOUNITED"
            o.abi_filiale_c = "1" # 200 KO YOUNITED
        elif esito == 200:
            #o.scp_c = "DP" # ok lasciare a STEAM
            # inserire nota trattativa con il link di Younited
            o.abi_filiale_c = "2" # 200 CON LINK
        elif esito == 400:
            o.abi_filiale_c = "3" # DATI MANCANTI

        session.set_entry(o)
        return True
    except Exception as e: print(str(e)); return False


def inserisciNotaOpportunitiesNEW(nome, id, file, nota):
    try:    
        session = crm.Session(url, usr, pwd)

        opportunity = session.get_entry("Opportunities", id) # NEW
        user = session.get_entry("Users", opportunity.assigned_user_id) # NEW

        mimetype = mimetypes.guess_type(file)[0]
        note = crm.Note(name = nome, parent_type = "Opportunities", parent_id = id, description = nota, file_mime_type = mimetype, file_ext = Path(file).suffix[1:], file_size = os.path.getsize(file))
        note.assigned_user_id = user.id # NEW
        session.set_entry(note)
        respone = session.set_note_attachment(note, file)
        note = session.get_entry("Notes", respone["id"])
        note.file_mime_type = mimetype # NEW
        session.set_entry(note)
        '''with SSHTunnelForwarder((ssh_host, ssh_port), ssh_username=ssh_user, ssh_password=ssh_pwd, remote_bind_address=(sql_hostname, sql_port)) as tunnel:
            connection = pymysql.connect(host='127.0.0.1', user=sql_username, passwd=sql_password, db=sql_main_database, port=tunnel.local_bind_port)
            cursor = connection.cursor()
            cursor.execute("update sugarcrm.notes set file_mime_type = '" + mimetype + "' where id = '" + respone["id"] + "'")
            connection.commit()
            cursor.close(); connection.close()'''
        return respone["id"]
    except: return False

def inserisciNotaOpportunities(nome, id, file = False):
    try:    
        session = crm.Session(url, usr, pwd)

        note = crm.Note(name = nome, parent_type = "Opportunities", parent_id = id)
        session.set_entry(note)
        respone = session.set_note_attachment(note, file)

        return respone["id"]
    except: return False

def inserisciNotaContacts(nome, id, file = False):
    try:    
        session = crm.Session(url, usr, pwd)

        note = crm.Note(name = nome, parent_type = "Contacts", parent_id = id, contact_id = id)
        session.set_entry(note)
        idNota = session.set_note_attachment(note, file)["id"]
        return idNota
    except: return False

def scaricaAllegatiOpportunities(id):
    #try:
    session = crm.Session(url, usr, pwd)

    notes = session.get_entry_list(crm.Note(parent_type = "Opportunities", parent_id = id)) # tutte le note collegate all'id opputunities id
    files = []
    for note in notes:
        file = session.get_note_attachment(note)["note_attachment"]
        if not file["filename"]: continue # evito note senza allegati
        ext = os.path.splitext(file["filename"])[1].upper()
        if ext not in [".WAV", ".WEBM"]: # non scarico le registrazioni
            with open(os.path.join(attachDir, file["filename"]), "wb") as f: f.write(base64.b64decode(file["file"]))
            files.append(file["filename"])
    return files
    #except: return False

def scaricaAllegatiContacts(ids):
    #try:
    session = crm.Session(url, usr, pwd)
    files = []
    docs = session.get_entries("Documents", ids)
    print(docs)
    for doc in docs:
        file = session.get_document_revision(doc.document_revision_id)["document_revision"]
        #print(file)
        with open(os.path.join(attachDir, file["filename"]), "wb") as f: f.write(base64.b64decode(file["file"]))
        files.append(file["filename"])
    return files

def scaricaRegistrazioniOpportunities(id):
    #try:
    session = crm.Session(url, usr, pwd)

    notes = session.get_entry_list(crm.Note(parent_type = "Opportunities", parent_id = id)) # tutte le note collegate all'id opputunities id
    files = []
    for note in notes:
        file = session.get_note_attachment(note)["note_attachment"]
        if not file["filename"]: continue # evito note senza allegati
        ext = os.path.splitext(file["filename"])[1].upper()
        if ext in [".WAV", ".WEBM"]: # scarico solo le registrazioni
            with open(os.path.join(attachDir, file["filename"]), "wb") as f: f.write(base64.b64decode(file["file"]))
            files.append(file["filename"])
    return files
    #except: return False

def write2file(filename, string):
    f = open(filename, "w")
    f.write(string)
    f.close()


###   T E S T   #######################################################

#ids = ["77b43cd0-66f5-11f0-a4f6-0242ac130003"]

#for id in ids: print([id, aggiornaTrattativaYounited(id, 400)])