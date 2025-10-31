"""
mappa_campi_crm.py
----------------------------------------
Contiene la mappatura tra i tipi di documento gestiti da MyBiros e
i campi CRM che vengono aggiornati tramite la funzione add_campi("ai", ...).

Ogni voce del dizionario MAPPA_CAMPI include:
- campo_crm: il nome del campo su CRM
- campo_mybiros: il campo sorgente restituito da MyBiros

Questo file è pensato per essere manutenuto facilmente:
- Aggiungere un nuovo tipo → aggiungere un blocco nel dizionario MAPPA_CAMPI.
- Aggiungere o rimuovere campi → modificare la lista di dizionari.
"""

MAPPA_CAMPI = {
    "CAI": [
        {"campo_crm": "first_name",             "campo_mybiros": "name"},
        {"campo_crm": "last_name",              "campo_mybiros": "surname"},
        {"campo_crm": "release_date",           "campo_mybiros": "issue_date"},
        {"campo_crm": "expiration_date",        "campo_mybiros": "expire_date"},
        {"campo_crm": "document_number",        "campo_mybiros": "id_number"},
        {"campo_crm": "sesso_c",                "campo_mybiros": "sex"},
        {"campo_crm": "birthdate",              "campo_mybiros": "birth_date"},
        {"campo_crm": "municipality_of_issue",  "campo_mybiros": "issue_place"},
        {"campo_crm": "primary_address_city",   "campo_mybiros": "residence"},
        {"campo_crm": "primary_address_street", "campo_mybiros": "address"},
        {"campo_crm": "codice_fiscale_c",       "campo_mybiros": "fiscal_code"},
    ],

    "PAT": [
        {"campo_crm": "first_name",             "campo_mybiros": "name"},
        {"campo_crm": "last_name",              "campo_mybiros": "surname"},
        {"campo_crm": "document_number",        "campo_mybiros": "id_number"},
        {"campo_crm": "expiration_date",        "campo_mybiros": "expire_date"},
        {"campo_crm": "release_date",           "campo_mybiros": "issue_date"},
        {"campo_crm": "birthdate",              "campo_mybiros": "birth_date"},
        {"campo_crm": "sesso_c",                "campo_mybiros": "sex"},
    ],

    "PAS": [
        {"campo_crm": "first_name",             "campo_mybiros": "name"},
        {"campo_crm": "last_name",              "campo_mybiros": "surname"},
        {"campo_crm": "document_number",        "campo_mybiros": "id_number"},
        {"campo_crm": "expiration_date",        "campo_mybiros": "expire_date"},
        {"campo_crm": "release_date",           "campo_mybiros": "issue_date"},
        {"campo_crm": "birthdate",              "campo_mybiros": "birth_date"},
        {"campo_crm": "sesso_c",                "campo_mybiros": "sex"},
        {"campo_crm": "primary_address_city",   "campo_mybiros": "residence"},
        {"campo_crm": "primary_address_street", "campo_mybiros": "address"},
    ],

    "TS": [
        {"campo_crm": "first_name",             "campo_mybiros": "name"},
        {"campo_crm": "last_name",              "campo_mybiros": "surname"},
        {"campo_crm": "codice_fiscale_c",       "campo_mybiros": "fiscal_code"},
        {"campo_crm": "birthdate",              "campo_mybiros": "birth_date"},
        {"campo_crm": "sesso_c",                "campo_mybiros": "sex"},
    ],

    "PS": [
        {"campo_crm": "first_name",             "campo_mybiros": "name"},
        {"campo_crm": "last_name",              "campo_mybiros": "surname"},
        {"campo_crm": "sesso_c",                "campo_mybiros": "sex"},
        {"campo_crm": "codice_fiscale_c",       "campo_mybiros": "fiscal_code"},
        {"campo_crm": "document_number",        "campo_mybiros": "id_number"},
        {"campo_crm": "release_date",           "campo_mybiros": "issue_date"},
        {"campo_crm": "expiration_date",        "campo_mybiros": "expire_date"},
        {"campo_crm": "birthdate",              "campo_mybiros": "birth_date"},
    ],

    "OBIS": [
        {"campo_crm": "codice_fiscale_c",       "campo_mybiros": "codice_fiscale"},
        {"campo_crm": "reddito_netto_mensile_c","campo_mybiros": "netto_obis"},
        {"campo_crm": "certificate_number_c",   "campo_mybiros": "chiave_pens"},
    ],

    "BP": [
        {"campo_crm": "first_name",                         "campo_mybiros": "nome"},
        {"campo_crm": "last_name",                          "campo_mybiros": "cognome"},
        {"campo_crm": "data_assunzione_c",                  "campo_mybiros": "data_assunzione"},
        {"campo_crm": "codice_fiscale_c",                   "campo_mybiros": "codice_fiscale"},
        {"campo_crm": "datore_lavoro_c",                    "campo_mybiros": "datore_lavoro"},
        {"campo_crm": "reddito_netto_mensile_c",            "campo_mybiros": "netto"},
        {"campo_crm": "vat_number_c",                       "campo_mybiros": "codice_fiscale_azienda"},
        {"campo_crm": "busta_paga_paga_oraria",             "campo_mybiros": "paga_oraria"},
        {"campo_crm": "busta_paga_mese_retribuzione",       "campo_mybiros": "mese_retribuzione"},
        {"campo_crm": "busta_paga_anno_retribuzione",       "campo_mybiros": "anno_retribuzione"},
        {"campo_crm": "busta_paga_totale_trattenute",       "campo_mybiros": "totale_trattenute"},
        {"campo_crm": "busta_paga_part_time",               "campo_mybiros": "part_time_percentuale"},
        {"campo_crm": "dipendente_reddito_lordo_mensile",   "campo_mybiros": "totale_competenze"},
        {"campo_crm": "cqs_rata_c",                         "campo_mybiros": "cessione"},
        {"campo_crm": "altri_prestiti_rata1_c",             "campo_mybiros": "prestito"},
        {"campo_crm": "delega_rata_c",                      "campo_mybiros": "delegazione_prestito"},
    ],

    "CP": [
        {"campo_crm": "first_name",                 "campo_mybiros": "nome"},
        {"campo_crm": "last_name",                  "campo_mybiros": "cognome"},
        {"campo_crm": "codice_fiscale_c",           "campo_mybiros": "codice_fiscale"},
        {"campo_crm": "reddito_netto_mensile_c",    "campo_mybiros": "netto"},
        {"campo_crm": "category_code_c",            "campo_mybiros": "categoria_pensione"},
        {"campo_crm": "altri_prestiti_rata1_c",     "campo_mybiros": "prestito"},
    ],

    "MC": [
        {"campo_crm": "codice_fiscale_c",           "campo_mybiros": "codice_fiscale"},
    ],

    "CUD": [
        {"campo_crm": "first_name",                         "campo_mybiros": "dipendente_nome"},
        {"campo_crm": "last_name",                          "campo_mybiros": "dipendente_cognome"},
        {"campo_crm": "datore_lavoro_c",                    "campo_mybiros": "azienda_denominazione"},
        {"campo_crm": "data_assunzione_c",                  "campo_mybiros": "data_inizio_rapporto"},
        {"campo_crm": "sesso_c",                            "campo_mybiros": "dipendente_genere"},
        {"campo_crm": "vat_number_c",                       "campo_mybiros": "azienda_codice_fiscale"},
        {"campo_crm": "codice_fiscale_c",                   "campo_mybiros": "dipendente_codice_fiscale"},
        {"campo_crm": "birthdate",                          "campo_mybiros": "dipendente_data_nascita"},
        {"campo_crm": "cud_anno_competenza",                "campo_mybiros": "anno_competenza"},
        {"campo_crm": "cud_reddito_t_indeterminato",        "campo_mybiros": "reddito_t._determ."},
        {"campo_crm": "cud_reddito_pensione",               "campo_mybiros": "reddito_pensione"},
        {"campo_crm": "cud_tfr_maturato_dal_112001_az",     "campo_mybiros": "tfr_(810)"},
        {"campo_crm": "cud_tfr_maturato_dal_112001_fondo",  "campo_mybiros": "tfr_(812)"},
        {"campo_crm": "cud_tfr_maturato_dall112007_fondo",  "campo_mybiros": "tfr_(813)"},
        {"campo_crm": "cud_tfr_maturato_al_3112200_fondo",  "campo_mybiros": "tfr_(811)"},
        {"campo_crm": "cud_tfr_maturato_al_3112200_az",     "campo_mybiros": "tfr_(809)"},
    ],

    "CS": [
        {"campo_crm": "datore_lavoro_c",            "campo_mybiros": "datore_lavoro"},
        {"campo_crm": "codice_fiscale_c",           "campo_mybiros": "codice_fiscale"},
        {"campo_crm": "data_assunzione_c",          "campo_mybiros": "data_inizio_rapporto"},
        {"campo_crm": "vat_number_c",               "campo_mybiros": "vat_azienda"},
        {"campo_crm": "professione_specifica_c",    "campo_mybiros": "qualifica"},
        {"campo_crm": "reddito_netto_mensile_c",    "campo_mybiros": "retribuzione_netta"},
        {"campo_crm": "birthdate",                  "campo_mybiros": "data_nascita_dipendente"},
        {"campo_crm": "cds_data_cds",               "campo_mybiros": "data_certificato"},
        {"campo_crm": "cds_tfr_accumulato",         "campo_mybiros": "tfr_accumulato"},
    ],
}

# Descrizioni codici documento
DOC_DESCR = {
    "CAI":              "Carta d'identità",
    "PAT":              "Patente di guida",
    "PAS":              "Passaporto",
    "TS":               "Tessera sanitaria",
    "PS":               "Permesso di soggiorno",
    "OBIS":             "Certificato Obis",
    "BP":               "Busta paga",
    "CP":               "Cedolino pensione",
    "MC":               "Merito creditizio",
    "CUD":              "CUD",
    "CS":               "Certificato Stipendio",
}
