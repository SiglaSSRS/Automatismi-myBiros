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

def inserisciNotaOpportunitiesSenzaAllegati(nome, id, nota):
    try:    
        session = crm.Session(url, usr, pwd)

        opportunity = session.get_entry("Opportunities", id) # NEW
        user = session.get_entry("Users", opportunity.assigned_user_id) # NEW
        note = crm.Note(name = nome, parent_type = "Opportunities", parent_id = id, description = nota)
        note.assigned_user_id = user.id # NEW
        response = session.set_entry(note)
        return response.id
    except Exception as e: print(e); return False

def inserisciNotaOpportunitiesNEW(nome, id, file, nota):
    try:    
        session = crm.Session(url, usr, pwd)

        opportunity = session.get_entry("Opportunities", id) # NEW
        user = session.get_entry("Users", opportunity.assigned_user_id) # NEW

        mimetype = mimetypes.guess_type(file)[0]
        note = crm.Note(name = nome, parent_type = "Opportunities", parent_id = id, description = nota, file_mime_type = mimetype, file_ext = Path(file).suffix[1:], file_size = os.path.getsize(file))
        note.assigned_user_id = user.id # NEW
        session.set_entry(note)
        response = session.set_note_attachment(note, file)
        note = session.get_entry("Notes", response["id"])
        note.file_mime_type = mimetype # NEW
        session.set_entry(note)
        '''with SSHTunnelForwarder((ssh_host, ssh_port), ssh_username=ssh_user, ssh_password=ssh_pwd, remote_bind_address=(sql_hostname, sql_port)) as tunnel:
            connection = pymysql.connect(host='127.0.0.1', user=sql_username, passwd=sql_password, db=sql_main_database, port=tunnel.local_bind_port)
            cursor = connection.cursor()
            cursor.execute("update sugarcrm.notes set file_mime_type = '" + mimetype + "' where id = '" + respone["id"] + "'")
            connection.commit()
            cursor.close(); connection.close()'''
        return response["id"]
    except Exception as e: print(e); return False

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

def aggiornaTrattativa(id, campi):
    try: 
        session = crm.Session(url, usr, pwd)
        opportunity = session.get_entry("Opportunities", id)
        for campo in campi: 
            if hasattr(opportunity, campo["nome"]):
                setattr(opportunity, campo["nome"], campo["valore"])
        session.set_entry(opportunity)
        return True
    except: return False
        


    

def write2file(filename, string):
    f = open(filename, "w")
    f.write(string)
    f.close()


###   T E S T   #######################################################

#print(scaricaAllegatiOpportunities("6A9317D1-5608-4E9F-BDB7-45BB25014DA2"))