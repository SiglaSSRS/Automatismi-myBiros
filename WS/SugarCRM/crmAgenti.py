###   W S   S U G A R   C R M   #######################################
#
# Autore                Denis Cattai
# Ultima modifica       18/12/2023
# Versione Python       3.9.12
# Descrizione           Modulo per utilizzo WS SugarCRM
#                       Per CRM Agenti
#
# Note
# WIP


###   I M P O R T   ###################################################

import base64
from datetime import datetime as dt
import os
from pathlib import Path
import sugarcrm as crm


###   C O S T A N T I   ###############################################

xml = "C:Projects/Automatismi/WS/SugarCRM/xml/" # cartella in cui vengono salvate request e response
Path(xml).mkdir(parents = True, exist_ok = True) # se non esiste, viene creata

url = "https://siglacredit.lionsolution.it/service/v4/rest.php"

usr = "edp"
pwd = "Edp2010$"

attachDir = "allegati" # cartella dove vengono salvati gli allegati del crm
Path(attachDir).mkdir(parents = True, exist_ok = True) # se non esiste, viene creata


###   F U N Z I O N I   ###############################################

def inserisciContatto(cognome, nome):
    try:    
        session = crm.Session(url, usr, pwd)

        contatto = crm.Contact(name = nome)
        id = session.set_entry(contatto)["id"]

        return id
    except: return False

def inserisciNotaOpportunitiesContacts(nome, id, file, nota):
    try:    
        session = crm.Session(url, usr, pwd)

        opportunity = session.get_entry("Opportunities", id, {"contacts_opportunities_1": ["id"]}) # NEW
        user = session.get_entry("Users", opportunity.assigned_user_id) # NEW

        note = crm.Note(name = nome, parent_type = "Opportunities", parent_id = id, description = nota, contact_id = opportunity.contacts_opportunities_1[0].id)
        note.assigned_user_id = user.id # NEW
        session.set_entry(note)
        idNota = session.set_note_attachment(note, file)["id"]
        return idNota
    except: return False

def inserisciNotaOpportunitiesNEW(nome, id, file, nota):
    try:    
        session = crm.Session(url, usr, pwd)

        opportunity = session.get_entry("Opportunities", id) # NEW
        user = session.get_entry("Users", opportunity.assigned_user_id) # NEW

        note = crm.Note(name = nome, parent_type = "Opportunities", parent_id = id, description = nota)
        note.assigned_user_id = user.id # NEW
        session.set_entry(note)
        idNota = session.set_note_attachment(note, file)["id"]
        return idNota
    except: return False

def inserisciNotaOpportunities(nome, id, file = False):
    try:    
        session = crm.Session(url, usr, pwd)

        note = crm.Note(name = nome, parent_type = "Opportunities", parent_id = id)
        session.set_entry(note)
        idNota = session.set_note_attachment(note, file)["id"]
        return idNota
    except: return False

def inserisciNotaContacts(nome, id, file = False):
    try:    
        session = crm.Session(url, usr, pwd)

        contact = session.get_entry("Contacts", id) # NEW
        user = session.get_entry("Users", contact.assigned_user_id) # NEW

        note = crm.Note(name = nome, parent_type = "Contacts", parent_id = id, contact_id = id)
        note.assigned_user_id = user.id # NEW
        session.set_entry(note)
        idNota = session.set_note_attachment(note, file)["id"]
        return idNota
    except: return False

def inserisciNotaContactsNew(nome, id, file, nota):
    try:    
        session = crm.Session(url, usr, pwd)

        contact = session.get_entry("Contacts", id) # NEW
        user = session.get_entry("Users", contact.assigned_user_id) # NEW

        note = crm.Note(name = nome, parent_type = "Contacts", parent_id = id, contact_id = id, description = nota)
        note.assigned_user_id = user.id # NEW
        session.set_entry(note)
        idNota = session.set_note_attachment(note, file)["id"]
        return idNota
    except: return False

def aggiornaNotaContacts(contact, user):
    try:    
        session = crm.Session(url, usr, pwd)
        note = session.get_entry_list(crm.Note(parent_type = "Contacts", parent_id = contact, contact_id = contact))

        for nota in note: nota.assigned_user_id = user; session.set_entry(nota)
        return True
    except: return False

def aggiornaContactAssignedUser(id, user = "7c6b5fc4-7a11-f6f4-40e3-5ebd6722b64f"):
    try:    
        session = crm.Session(url, usr, pwd)
        contact = session.get_entry("Contacts", id) # NEW

        contact.assigned_user_id = user; session.set_entry(contact)
        return True
    except: return False
'''
def cancellaSecurityGroups(id):
    #try:    
        session = crm.Session(url, usr, pwd)
        contact = session.get_entry("Contacts", "89390455-438c-405b-0f23-61324c52f980")
        #securityGroup = session.get_entry("SecurityGroups", "1106caf4-8121-0f9a-a836-5ea6f39cbb71", {"securitygroups_contacts": ["id"]}) # NEW
        #securityGroup = session.get_entry("Contacts", "89390455-438c-405b-0f23-61324c52f980", {"contacts_opportunities_1": ["id"]}) # NEW
        contacts = session.get_relationships(contact, "securitygroups")
        print(contacts)

        #securityGroup = session.get_entry("SecurityGroups", "0000e6ac-1098-11ec-ab23-00163ef44464")

        return True
    #except: return False
'''
def cancellaContatto(id):
    #try:    
        session = crm.Session(url, usr, pwd)
        contact = session.get_entry("Contacts", id, {"contacts_opportunities_1": ["id"]})
        try:
            opportunities = contact.contacts_opportunities_1
            for opportunity in opportunities: 
                o = session.get_entry("Opportunities", opportunity.id)
                print(o.id)
                o.deleted = 1; session.set_entry(o)
        except AttributeError as e: pass

        try:
            note = session.get_entry_list(crm.Note(contact_id = id))
            print(note)
            for nota in note:
                print(nota.id)
                nota.deleted = 1; session.set_entry(nota)
        except AttributeError as e: pass

        contact = session.get_entry("Contacts", id)
        contact.deleted = 1; session.set_entry(contact)

        return True
    #except: return False

def ripristinaContatto(id):
    #try:    
        session = crm.Session(url, usr, pwd)
        contact = session.get_entry_list(crm.Contact(id = id), deleted = True)[0]
        contact.deleted = 0; session.set_entry(contact)

        return True
    #except: return False


def inserisciChiamataContacts(nome, id):
    try:    
        session = crm.Session(url, usr, pwd)

        call = crm.Call(name = nome, parent_type = "Contacts", parent_id = id, contact_id = id, status = "Planned", date_start = "2024-03-22 10:00:00", date_end = "2024-03-22 10:00:00")
        call =  session.set_entry(call)
        return call.id
    except: return False

def scaricaAllegatiOpportunities(id):
    try:
        session = crm.Session(url, usr, pwd)

        notes = session.get_entry_list(crm.Note(parent_type = "Opportunities", parent_id = id)) # tutte le note collegate all'id opputunities id
        files = []
        for note in notes:
            file = session.get_note_attachment(note)["note_attachment"]
            ext = os.path.splitext(file["filename"])[1].upper()
            if ext != ".WAV": # non scarico le registrazioni
                with open(os.path.join(attachDir, file["filename"]), "wb") as f: f.write(base64.b64decode(file["file"]))
                files.append(file["filename"])
        return files
    except: return False

def scaricaAllegatiContacts(id):
    try:
        session = crm.Session(url, usr, pwd)

        notes = session.get_entry_list(crm.Note(contact_id = id)) # tutte le note collegate all'id opputunities id
        files = []
        for note in notes:
            file = session.get_note_attachment(note)["note_attachment"]
            ext = os.path.splitext(file["filename"])[1].upper()
            #if ext != ".WAV": # non scarico le registrazioni
            with open(os.path.join(attachDir, file["filename"]), "wb") as f: f.write(base64.b64decode(file["file"]))
            files.append(file["filename"])
        return files
    except: return False

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

def write2file(filename, string):
    f = open(filename, "w")
    f.write(string)
    f.close()


###   T E S T   #######################################################


#idCon = "ea3d42fe-2c5e-3867-2d6a-60e311ab6214"
#idOpp = "732eab56-8852-11ee-9c90-0242ac130004"

#print(inserisciNotaOpportunities("PDF EXPERIAN TEST", idOpp, "C:/Users/orion/Automatismi/WS/SugarCRM/TEST.pdf"))
#print(inserisciNotaContacts("PDF EXPERIAN TEST", idCon, "allegati/russomanno.jpeg"))
#print(inserisciChiamataContacts("CHIAMATA TEST 2", idCon))

'''
session = crm.Session(url, usr, pwd)
call = session.get_entry("Calls", "b926fd9f-ff98-784a-98a5-658553da503a")
for key, value in vars(call).items(): print(str(key) + ": "+ str(value))
'''