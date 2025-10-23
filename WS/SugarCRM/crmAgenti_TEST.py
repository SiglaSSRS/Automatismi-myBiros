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

xml = "C:/users/orion/Automatismi/WS/SugarCRM/xml/" # cartella in cui vengono salvate request e response
Path(xml).mkdir(parents = True, exist_ok = True) # se non esiste, viene creata

url = "https://siglacredit.lionsolution.it/service/v4/rest.php"

usr = "edp"
pwd = "Edp2010$"

attachDir = "allegati" # cartella dove vengono salvati gli allegati del crm
Path(attachDir).mkdir(parents = True, exist_ok = True) # se non esiste, viene creata


###   F U N Z I O N I   ###############################################


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

def write2file(filename, string):
    f = open(filename, "w")
    f.write(string)
    f.close()

def inserisciContatto(cognome, nome, telefono, email, datoreLavoro, idUtente, idCanale, descrizione, provincia, acSugar, contattoSugar):
    try:    
        session = crm.Session(url, usr, pwd)

        contatto = crm.Contact(
            last_name = cognome, 
            first_name = nome, 
            phone_other = telefono, 
            email1 = email, 
            datore_lavoro_c = datoreLavoro, 
            assigned_user_id = idUtente, 
            id_appoggio_canale_2_c = idCanale, 
            description = descrizione,
            #primary_address_city = provincia,
            primary_address_state = provincia,
            #residenza_provincia_c = provincia,
            google_idac_c = acSugar,
            google_id_contatto_c = contattoSugar

        )
        response = session.set_entry(contatto)
        print(response.fields)

        return response["id"]
    except Exception as e: print(response); return False

def aggiornaContatto(id, provincia):
    try:    
        session = crm.Session(url, usr, pwd)

        contact = session.get_entry("Contacts", id)
        contact.primary_address_state = provincia
        contact.nascita_regione_c = " "
        contact.nascita_provincia_c = " "

        '''if len(contact.phone_other) == 19:
            contact.phone_other = contact.phone_other.replace(" ", "").replace("+3939", "+39")
        else: contact.phone_other = contact.phone_other.replace(" ", "")'''
        session.set_entry(contact)

        return True
    except Exception as e: print(e); return False


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

# Paolo	Torterolo	Prestiti img 13/02/25	FACEBOOK	10/06/2025 08:38	paolo.torterolo69@gmail.com	3,93429E+11				Savona	Liguria	bee9b9fe-c8f9-d845-e207-60d20ad97f06	6514c3cb-86a5-3e4b-4e94-67641f939ff0

cognome = "Schiopu"
nome = "Ionut"
telefono = "+393897947837"
email = "ionutschiopu1983@gmail.com"
datoreLavoro = ""
idUtente = "1bead302-d6fc-d1bd-678d-5ea6fbdcd3dc"
idCanale = "6514c3cb-86a5-3e4b-4e94-67641f939ff0"
descrizione = "FONTE: FACEBOOK - Prestiti 05/2025 - video"
provincia = "VR"
acSugar = "87df1306-9f99-4a81-92c4-db0c85e6c42a"
contattoSugar = "0a6d52ef-4304-4a1b-951d-8848f836e2c2"

#print(inserisciContatto(cognome, nome, telefono, email, datoreLavoro, idUtente, idCanale, descrizione, provincia, acSugar, contattoSugar))

ids = ['10a8aa98-7b1c-c90a-bb40-6847d34b9bda', '12e49b6f-75a6-18e9-8dbf-6847d3bf75c2', '13959e6f-7eca-74b6-9ebf-6847d348724b', '13ab3940-1421-296e-e386-6847d3d66d64', '14f58d59-4363-c370-c1ed-6847e4a89a54', '168948aa-309b-f680-d3a4-6847d370e40c', '186f5c56-b396-41a7-7a5a-6847d30ec90e', '1909a01d-33b1-1502-08b1-68470742bcd2', '19830264-b41e-84c1-32f7-6847d35c544c', '19c11482-25a8-1122-750f-6847d32ca45c', '1c15ab52-3d7a-47d4-fde2-6846f5911530', '1e943b03-e862-d477-ac90-6847d31d0352', '1ff5bbb9-6f9c-5a82-97e1-68470e639d7c', '21e54caf-b2ff-a2f4-f695-6847d3d12e31', '23e9d5ae-3684-b207-27cb-6847e4ba2c2e', '248cfa27-2fcf-299c-0856-684707ab292c', '253997c7-f396-afae-b629-6847d3a3473c', '266afcf5-e717-25a6-d743-6847d33e907b', '281ee9f8-d88b-3215-96e9-6847d323227c', '295074e6-1a03-d44f-05fb-6847d3c6e8e2', '2988e607-3d90-013b-e762-6847d334a120', '2a0496e4-8eec-ae8d-f875-6847d3899442', '2a86a92a-30e7-5319-2a0f-6847d3957d72', '2ca179b0-b0f9-95cb-7ff9-6846f5083ed7', '2e4e05b3-0e03-f76e-9620-6847d3d5381a', '2f681f43-01a3-8b85-d7a2-6847d3cf2279', '31440453-8ee1-6eef-78eb-6847d332802c', '319e02df-64ed-56cb-38c2-6847d33b3232', '32632bb3-a8c5-4017-269e-68470e4c69be', '37327a83-7b8d-69e5-8166-6847d39d971e', '375d670f-7c38-8967-5be8-6847d37b8f77', '3784ee6c-cba4-908a-81eb-684707797043', '39c8baa2-c25b-68e8-75d1-6847d30ab652', '3b387c1c-2261-f404-6aea-6847d39c5e1a', '3cc1b615-a973-4d84-0e0b-6847d3c8306e', '3db95fc8-74fa-b7d8-3683-6847d34ed1d9', '3dcec19c-ff13-cdef-2f3a-6846f5ca49c7', '3dfad1bd-48c9-6691-a000-6847d38a5f27', '3f591a28-568a-0bce-f4d2-6847e42cfae5', '42b89516-f448-67a1-1004-6847d3a65864', '42daf00f-2641-9ce3-4956-68470e18af29', '47b3c86e-2be1-68d1-50a7-6847d3103904', '48e7073f-b4e2-f47a-b432-6847d30dba75', '4a84ec61-27fb-8d30-6c32-6846f5e8d154', '4b3012ac-2b79-546a-17c5-684707af76ad', '4b319f0a-6914-51a2-5a78-6847d3e531cd', '4eb17f97-1cb0-c039-b4ee-6847d3a8d7b4', '4fb458aa-170b-8658-8052-6846f585a746', '4feca01d-6f9b-0e9a-e9a6-6847d3d801a2', '515c45be-2bf3-a970-5043-6847d37cf962', '5306607a-3859-0e1f-7d09-6847d36decf9', '551d1239-4697-efed-ae01-6847d3f89a2d', '5754dd81-dfc9-e892-b625-68470e9708af', '58061798-2f8f-72f4-d84b-6847e4c499bf', '59a8f55d-60b5-6755-7739-6847d3efd87a', '5ad451df-b7d1-9b13-685f-6847d30d97a5', '5bcd42b6-2d07-4d23-acb3-6847d35a7aea', '5da5d30d-923c-a218-8f79-6846f5a50fc8', '5df6f20b-27ee-cfbd-7190-6847d3352130', '5f25c5da-a3ef-b1e3-635d-684707a9c5dc', '5fb9d0f0-13fb-8917-0430-684708b9225b', '5fbfae15-6a47-f870-3a61-6846f5b2f3e6', '61994de8-c662-ce4a-9788-6847d38d5990', '634b2fc9-7986-6d08-519a-6847d36bbca6', '650881bc-f2de-e857-0fb2-6847d39a6437', '685b2e32-aea3-bfab-60e0-6847d3cb1eb6', '69769e55-738f-8177-6517-6846dcede78a', '6b3ca6b7-9bd9-38bb-6471-6847d3472401', '6c660647-d648-0e48-fdd8-6847d392d5f6', '6c838052-a508-e987-ffe7-6847d3555ab6', '6cdbd873-3f47-761e-1c68-68470e3b838f', '6e31591c-a431-cf8d-5ff0-6847d364b7cf', '6f50062c-56f1-a462-8580-6847d39d843a', '6fc15577-81c7-eddb-357c-6846f5c52ced', '70014d6f-36aa-bf77-8ec9-6847d305af8b', '70fe5104-3531-43b1-7798-6846f510215b', '713e8c39-08cc-db3f-4a2b-684707fcb27e', '724d52bb-c128-0b3d-e1df-6847075d8661', '727201e9-5b80-2226-b247-6847d38630bc', '73fc983f-34a8-1d51-7904-6847d33c96db', '75460268-32e0-fac3-16ce-6847e4a432d0', '754e9e41-6572-54d9-57b4-6847d39a6b85', '7576580e-5e39-ac79-f5b7-6847d3717c3b', '7a890c40-144e-9668-7f88-6847085b61bf', '7b3209be-6064-e9af-ea67-6847074a8fdc', '7b869718-076f-cb70-96fe-6847d378c9ba', '7c940e4e-cd8b-56fa-b198-6847d3a19459', '7db36ef9-887d-ca7f-ca5c-6847d3e2e8c7', '7e65bd33-9c9b-4a4f-838b-6847d373d88c', '813c2273-e511-2d74-610b-6847d38a55a7', '81686e5e-51fe-b663-2236-6847d30a98f2', '8214626d-e60e-0ff4-7b4b-684707912008', '840d1277-1ce9-19ed-bbc7-6846f5ff3bb9', '86b77851-98ec-30a6-b575-6847d3a71b62', '87c03f1e-7240-9af0-92aa-6847d3514fd8', '890d0283-f46a-d349-c1d8-6847e44b6768', '8cf37822-0df3-84e4-8458-6847d37ce5d0', '8df26dfd-b88a-0fcb-1752-6847d3268e0f', '91256a6a-8302-105c-ecee-6847d3a53403', '91b2cd6a-427c-dbc3-5a48-6847d3fa3b67', '92a114fd-2648-609a-b309-6847e4fcee0f', '93093e1c-6c12-3b6f-ae39-6847d3103e3d', '938e8f52-59b1-f00b-df41-684707b29738', '93f00bc5-e3ff-ebdd-73ba-6846f5c151c1', '94ce725b-8bec-32a8-7601-6846f5b38b10', '990e0ba3-0cce-5779-afa5-68470e37b521', '99998b63-b1fb-ad6e-9e09-6847d301c899', '9a6d5827-c925-3dc0-a3be-6847d3244216', '9d95882c-4fef-03fb-0c7d-6847d3f07e5f', '9e8ccc86-5333-c5cc-f7af-6847d37d75cc', 'a2d47b8d-faca-63ec-c8f9-6847d3b77b37', 'a382d8ba-72b7-fd98-905d-684707974bea', 'a3eb22f0-398e-f923-37f8-6847d3000214', 'a4a6378d-b099-658f-1ada-6847d3fd5d9d', 'a5de5b48-bdc8-abb0-4fdd-68470e1f8571', 'a6a0213a-1ec3-af99-54c2-6846f5918c2a', 'aa9c4775-bfa6-9149-8907-6847d396bff1', 'ac94b391-ca5e-923d-720e-6847e4da1f99', 'ad69ec20-d325-31ea-82e5-6847d3dbed46', 'ae7a94a9-3ac4-6e28-23a8-6847d3ff4b33', 'b043a235-759c-819c-e83a-6847d31194ef', 'b3da73d9-3f27-102b-6c9a-6847d31762cf', 'b4e6bd44-3019-f4cb-e48f-6847d3b36431', 'b4e78729-a5ff-1e09-74f2-684707763c89', 'b5a52218-b96f-8c42-6b9c-6847d3f3641f', 'b833a9f0-e849-8ce6-b28d-6846f58a351c', 'bd1f6e67-3e1a-25e7-9826-6847d3ca1c6e', 'be0263f9-0924-606d-74b2-68470eb07518', 'bf23abfa-3f9e-e978-c71f-6847d3972769', 'c1961761-e246-87ba-7c16-6847d3b8b6d9', 'c1f02cba-0907-5b87-ffae-6847d3e32a99', 'c37705aa-530b-507c-5a9b-6847d30b795e', 'c4c113a6-0196-f8f1-6ccc-6847d32c89b8', 'c67d64ee-e8f2-4b55-c669-6847d3b8352e', 'c68e07e7-6588-e63b-52b1-68470700b8e2', 'c7417cfa-cdb6-4c06-0454-6847d362cdd7', 'c84db2f9-47ee-2470-1d50-6847e46a8b12', 'c9be8d95-e0d1-95a7-cbcb-6846f537443b', 'cd69fe12-b139-e226-2ae7-6847d35365be', 'd2210a8c-958f-99e1-bc18-6847d36b5f63', 'd45f52d6-fb8f-afd8-41a5-6847d330612e', 'd4d3e8a4-23e1-d764-5009-68470e5cfb5a', 'd5639afd-0cab-95a0-b834-6847d34055c9', 'd641a063-3f34-b054-eb39-6847d3d838e2', 'd81dda17-d895-ae7d-41e6-6847d36b59d6', 'd9644bcc-4b21-aff6-1923-68470794fad9', 'db77149d-255e-cf10-a1db-6846f543238d', 'df5e2e8f-991d-58a1-cbd5-6847d39449c9', 'e1e5ab70-cc48-fbdb-135e-6847e4b7ed38', 'e410e41c-17f2-2d69-cd63-6847d31ee575', 'e4768bb9-03a4-555a-65ab-6847d3ef732f', 'e627547e-ade1-a768-de16-6847d3ace2f8', 'e64adcb6-7fa1-f458-4a99-6847d324fa72', 'e754d41a-b428-8129-e812-68470e281d90', 'e8108a2a-05c6-bc15-62ba-6847d3295ede', 'e99307c3-c541-743d-130e-6847d34bfe04', 'e99909e7-fa2c-9659-fbc3-6847d3c124fc', 'eb303db0-3275-0a8f-b604-6847e43e7386', 'eb4b46e3-03f0-920f-883f-684707f043cc', 'ee3e54fa-f74d-cb53-3b28-6846f598dc7b', 'f02738a6-3b62-f9e8-fdd8-6847d30da9f5', 'f8fc0012-dc49-5753-fb59-684707a79467']
ids = ['16fe11be-1b52-3aa3-a356-6847efec01e1','2da00dd3-5e47-4a89-76e6-6847fb575a7f','47dd6882-a07c-ee4c-24e4-6847ecb5a2cb','484be911-1a06-e71e-a89c-6848135caa98','4d65a3e9-e1a6-5887-cfae-68481d1f4f8d','52483264-ff72-8ff6-2be7-68481de9509b','57282668-da7f-da7d-f918-6848191f2fe7','590692d7-1ee4-281f-5c93-68481d32dd3d','5ca05c2a-2379-76f2-8813-6847eea609cd','5d92afd3-93e7-ce86-9a1b-68480f3464cb','609f7403-f8b9-5ec7-cbb9-684818dd0c75','6b134d47-c9c8-7595-2aac-68480a4daa3b','70d4de99-5614-bed1-a012-68480411c66d','775dfff2-8c70-22da-a4ab-684806452e0e','7be29c85-eb53-74c9-b296-6848148ba14f','7e330e50-f8e2-8ef1-5f06-6847f6a00e44','8810c650-af9f-fc5f-2441-684808c08885','8de3f8c3-d4a5-6fae-a308-68481bca8d7d','8ee82411-35b6-f94b-39cc-6847e2307d32','98a77765-1d11-4aed-d4c2-6847ebf803e5','99e99a4b-737f-cffe-71d6-6848163f8a64','9fff17c5-2b87-33bf-901a-68480e99ae1b','ae6627cb-6ec5-bc2b-4135-68480358f9e6','b8a186df-ea1e-13d0-36a5-6847fd89434d','bcb02304-1dad-c140-a8ac-684814dc532a','c21427e3-7f72-79d4-1b4c-68481be3c37c','c4f67a9f-303f-3139-4b0a-6847d624525e','c5366c09-6a6c-1865-7837-68481955c3f6','df859020-95c0-906a-6126-68480003e319','e5725d88-fc4f-28e5-4523-6848003686ee','eba66022-e857-bff7-3dea-6847f6cca107','f4430a62-2323-3dbf-1a55-6847ef21a989']

ids = [
    ['10a8aa98-7b1c-c90a-bb40-6847d34b9bda','LO'],
    ['12e49b6f-75a6-18e9-8dbf-6847d3bf75c2','PO'],
    ['13959e6f-7eca-74b6-9ebf-6847d348724b','AN'],
    ['13ab3940-1421-296e-e386-6847d3d66d64','TV'],
    ['168948aa-309b-f680-d3a4-6847d370e40c','BO'],
    ['186f5c56-b396-41a7-7a5a-6847d30ec90e','VT'],
    ['1909a01d-33b1-1502-08b1-68470742bcd2','BI'],
    ['19830264-b41e-84c1-32f7-6847d35c544c','NA'],
    ['19c11482-25a8-1122-750f-6847d32ca45c','PN'],
    ['1c15ab52-3d7a-47d4-fde2-6846f5911530',''],
    ['1e943b03-e862-d477-ac90-6847d31d0352','RM'],
    ['1ff5bbb9-6f9c-5a82-97e1-68470e639d7c','FI'],
    ['21e54caf-b2ff-a2f4-f695-6847d3d12e31','VR'],
    ['248cfa27-2fcf-299c-0856-684707ab292c','CH'],
    ['253997c7-f396-afae-b629-6847d3a3473c','LO'],
    ['266afcf5-e717-25a6-d743-6847d33e907b','CS'],
    ['281ee9f8-d88b-3215-96e9-6847d323227c','VI'],
    ['295074e6-1a03-d44f-05fb-6847d3c6e8e2','PR'],
    ['2988e607-3d90-013b-e762-6847d334a120','BR'],
    ['2a0496e4-8eec-ae8d-f875-6847d3899442','AL'],
    ['2a86a92a-30e7-5319-2a0f-6847d3957d72','PD'],
    ['2e4e05b3-0e03-f76e-9620-6847d3d5381a','AN'],
    ['2f681f43-01a3-8b85-d7a2-6847d3cf2279','NA'],
    ['31440453-8ee1-6eef-78eb-6847d332802c','PD'],
    ['319e02df-64ed-56cb-38c2-6847d33b3232','CE'],
    ['32632bb3-a8c5-4017-269e-68470e4c69be','SS'],
    ['37327a83-7b8d-69e5-8166-6847d39d971e','LC'],
    ['3784ee6c-cba4-908a-81eb-684707797043','RM'],
    ['39c8baa2-c25b-68e8-75d1-6847d30ab652','RN'],
    ['3b387c1c-2261-f404-6aea-6847d39c5e1a','MI'],
    ['3cc1b615-a973-4d84-0e0b-6847d3c8306e','MN'],
    ['3db95fc8-74fa-b7d8-3683-6847d34ed1d9','VA'],
    ['3dcec19c-ff13-cdef-2f3a-6846f5ca49c7','TO'],
    ['3dfad1bd-48c9-6691-a000-6847d38a5f27','NA'],
    ['420d123f-5ea3-18aa-776d-6847d3b9c452','FI'],
    ['42b89516-f448-67a1-1004-6847d3a65864','CT'],
    ['42daf00f-2641-9ce3-4956-68470e18af29','VA'],
    ['47b3c86e-2be1-68d1-50a7-6847d3103904','PV'],
    ['48e7073f-b4e2-f47a-b432-6847d30dba75','BS'],
    ['4a84ec61-27fb-8d30-6c32-6846f5e8d154','BA'],
    ['4b3012ac-2b79-546a-17c5-684707af76ad','CE'],
    ['4b319f0a-6914-51a2-5a78-6847d3e531cd','CR'],
    ['4eb17f97-1cb0-c039-b4ee-6847d3a8d7b4','VE'],
    ['4fb458aa-170b-8658-8052-6846f585a746','MI'],
    ['4feca01d-6f9b-0e9a-e9a6-6847d3d801a2','LT'],
    ['515c45be-2bf3-a970-5043-6847d37cf962','TO'],
    ['5306607a-3859-0e1f-7d09-6847d36decf9','LO'],
    ['551d1239-4697-efed-ae01-6847d3f89a2d','SS'],
    ['5754dd81-dfc9-e892-b625-68470e9708af','CN'],
    ['59a8f55d-60b5-6755-7739-6847d3efd87a','AV'],
    ['5ad451df-b7d1-9b13-685f-6847d30d97a5','TV'],
    ['5bcd42b6-2d07-4d23-acb3-6847d35a7aea','TO'],
    ['5da5d30d-923c-a218-8f79-6846f5a50fc8','SA'],
    ['5df6f20b-27ee-cfbd-7190-6847d3352130','RG'],
    ['5f25c5da-a3ef-b1e3-635d-684707a9c5dc','FG'],
    ['5fbfae15-6a47-f870-3a61-6846f5b2f3e6','RC'],
    ['61994de8-c662-ce4a-9788-6847d38d5990','RC'],
    ['634b2fc9-7986-6d08-519a-6847d36bbca6','GE'],
    ['685b2e32-aea3-bfab-60e0-6847d3cb1eb6','NA'],
    ['6b3ca6b7-9bd9-38bb-6471-6847d3472401','VI'],
    ['6c660647-d648-0e48-fdd8-6847d392d5f6','PR'],
    ['6cdbd873-3f47-761e-1c68-68470e3b838f','BG'],
    ['6e31591c-a431-cf8d-5ff0-6847d364b7cf','NA'],
    ['6f50062c-56f1-a462-8580-6847d39d843a','NA'],
    ['6fc15577-81c7-eddb-357c-6846f5c52ced',''],
    ['70014d6f-36aa-bf77-8ec9-6847d305af8b','PU'],
    ['70fe5104-3531-43b1-7798-6846f510215b','MN'],
    ['713e8c39-08cc-db3f-4a2b-684707fcb27e','GR'],
    ['724d52bb-c128-0b3d-e1df-6847075d8661',''],
    ['727201e9-5b80-2226-b247-6847d38630bc','VB'],
    ['73fc983f-34a8-1d51-7904-6847d33c96db','PU'],
    ['754e9e41-6572-54d9-57b4-6847d39a6b85','NO'],
    ['7576580e-5e39-ac79-f5b7-6847d3717c3b','TR'],
    ['7a890c40-144e-9668-7f88-6847085b61bf','PR'],
    ['7b3209be-6064-e9af-ea67-6847074a8fdc','TO'],
    ['7b869718-076f-cb70-96fe-6847d378c9ba','NA'],
    ['7c940e4e-cd8b-56fa-b198-6847d3a19459','TV'],
    ['7db36ef9-887d-ca7f-ca5c-6847d3e2e8c7','BA'],
    ['7e65bd33-9c9b-4a4f-838b-6847d373d88c','ME'],
    ['813c2273-e511-2d74-610b-6847d38a55a7','BI'],
    ['81686e5e-51fe-b663-2236-6847d30a98f2','TO'],
    ['8214626d-e60e-0ff4-7b4b-684707912008','BG'],
    ['840d1277-1ce9-19ed-bbc7-6846f5ff3bb9','NU'],
    ['86b77851-98ec-30a6-b575-6847d3a71b62','SA'],
    ['87c03f1e-7240-9af0-92aa-6847d3514fd8','MI'],
    ['8cf37822-0df3-84e4-8458-6847d37ce5d0','PG'],
    ['8df26dfd-b88a-0fcb-1752-6847d3268e0f','BA'],
    ['91256a6a-8302-105c-ecee-6847d3a53403','RM'],
    ['91b2cd6a-427c-dbc3-5a48-6847d3fa3b67','PD'],
    ['938e8f52-59b1-f00b-df41-684707b29738','CT'],
    ['93f00bc5-e3ff-ebdd-73ba-6846f5c151c1','PG'],
    ['94ce725b-8bec-32a8-7601-6846f5b38b10','AR'],
    ['990e0ba3-0cce-5779-afa5-68470e37b521','CE'],
    ['99998b63-b1fb-ad6e-9e09-6847d301c899','FR'],
    ['9a6d5827-c925-3dc0-a3be-6847d3244216','PG'],
    ['9d95882c-4fef-03fb-0c7d-6847d3f07e5f','CH'],
    ['9e8ccc86-5333-c5cc-f7af-6847d37d75cc','SI'],
    ['a2d47b8d-faca-63ec-c8f9-6847d3b77b37','BI'],
    ['a382d8ba-72b7-fd98-905d-684707974bea','CR'],
    ['a3eb22f0-398e-f923-37f8-6847d3000214','GO'],
    ['a4a6378d-b099-658f-1ada-6847d3fd5d9d','RM'],
    ['a5de5b48-bdc8-abb0-4fdd-68470e1f8571','PG'],
    ['a6a0213a-1ec3-af99-54c2-6846f5918c2a','IM'],
    ['aa9c4775-bfa6-9149-8907-6847d396bff1','CO'],
    ['ad69ec20-d325-31ea-82e5-6847d3dbed46','CH'],
    ['ae7a94a9-3ac4-6e28-23a8-6847d3ff4b33','SS'],
    ['b043a235-759c-819c-e83a-6847d31194ef','CS'],
    ['b3da73d9-3f27-102b-6c9a-6847d31762cf','LT'],
    ['b4e6bd44-3019-f4cb-e48f-6847d3b36431','RG'],
    ['b4e78729-a5ff-1e09-74f2-684707763c89','LT'],
    ['b5a52218-b96f-8c42-6b9c-6847d3f3641f','NA'],
    ['b833a9f0-e849-8ce6-b28d-6846f58a351c','LO'],
    ['bd1f6e67-3e1a-25e7-9826-6847d3ca1c6e','MB'],
    ['be0263f9-0924-606d-74b2-68470eb07518','TE'],
    ['bf23abfa-3f9e-e978-c71f-6847d3972769','LO'],
    ['c1961761-e246-87ba-7c16-6847d3b8b6d9','RM'],
    ['c1f02cba-0907-5b87-ffae-6847d3e32a99','MB'],
    ['c37705aa-530b-507c-5a9b-6847d30b795e','RM'],
    ['c4c113a6-0196-f8f1-6ccc-6847d32c89b8','FI'],
    ['c67d64ee-e8f2-4b55-c669-6847d3b8352e','NA'],
    ['c68e07e7-6588-e63b-52b1-68470700b8e2','TO'],
    ['c7417cfa-cdb6-4c06-0454-6847d362cdd7','AR'],
    ['c9be8d95-e0d1-95a7-cbcb-6846f537443b','CS'],
    ['cd69fe12-b139-e226-2ae7-6847d35365be','VT'],
    ['d2210a8c-958f-99e1-bc18-6847d36b5f63','BS'],
    ['d45f52d6-fb8f-afd8-41a5-6847d330612e','RM'],
    ['d4d3e8a4-23e1-d764-5009-68470e5cfb5a','PV'],
    ['d5639afd-0cab-95a0-b834-6847d34055c9','MT'],
    ['d641a063-3f34-b054-eb39-6847d3d838e2','MC'],
    ['d81dda17-d895-ae7d-41e6-6847d36b59d6','TV'],
    ['d9644bcc-4b21-aff6-1923-68470794fad9','TO'],
    ['db77149d-255e-cf10-a1db-6846f543238d','RM'],
    ['df5e2e8f-991d-58a1-cbd5-6847d39449c9','BL'],
    ['e410e41c-17f2-2d69-cd63-6847d31ee575','PE'],
    ['e4768bb9-03a4-555a-65ab-6847d3ef732f','SS'],
    ['e627547e-ade1-a768-de16-6847d3ace2f8','NA'],
    ['e64adcb6-7fa1-f458-4a99-6847d324fa72','AR'],
    ['e754d41a-b428-8129-e812-68470e281d90','BG'],
    ['e8108a2a-05c6-bc15-62ba-6847d3295ede','BO'],
    ['e99307c3-c541-743d-130e-6847d34bfe04','BS'],
    ['e99909e7-fa2c-9659-fbc3-6847d3c124fc','LO'],
    ['eb4b46e3-03f0-920f-883f-684707f043cc','VT'],
    ['ee3e54fa-f74d-cb53-3b28-6846f598dc7b','MN'],
    ['f02738a6-3b62-f9e8-fdd8-6847d30da9f5','MI'],
    ['f8fc0012-dc49-5753-fb59-684707a79467','FG']
]

for id in ids: print(id[0], id[1], aggiornaContatto(id[0], id[1]))

#print("10a8aa98-7b1c-c90a-bb40-6847d34b9bda", "LO", aggiornaContatto("10a8aa98-7b1c-c90a-bb40-6847d34b9bda", "LO"))