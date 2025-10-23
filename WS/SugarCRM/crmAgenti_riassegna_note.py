import crmAgenti as lions
import glob
import os
import pandas as pd
import sys

# Apertura file e caricamento Excel
dirFiles = glob.glob("./*.xlsx")
newFile = max(dirFiles, key = os.path.getctime)
if input("Caricare il file " + os.path.split(newFile)[1] + "? (y/N) ") != "y": sys.exit(0)
df = pd.DataFrame(pd.read_excel(newFile))

for row in df.values.tolist():
    if lions.aggiornaNotaContacts(row[0], row[1]): print(row[0] + " OK")
    else: print(row[0] + " ERRORE")