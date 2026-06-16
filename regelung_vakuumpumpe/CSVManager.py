#install the driver software NI-DAQ™mx
#install all the necessary libaries and debugger/compiler(python, python debugger, git etc.) to get it running on VS code
#install with py -m pip install in the terminal all the necessary packages
#matplotlib maybe also required

import csv
import time
import pandas as pd 
import numpy as np

from regelung_vakuumpumpe.labortest3 import Druck

class CSVReader:
    def __init__(self, pfad, sep=';', decimal=',', encoding='cp1252', on_bad_lines='skip'):
        self.path = pfad
        self.sep = sep
        self.decimal = decimal
        self.encoding = encoding
        self.on_bad_lines = on_bad_lines
        self.zeit = []
        self.Druck = []
        self.Ventilspannung_Durchlass = []
        self.Ventilspannung_Einlass = []
        self.Stellgröße = []
        self.StufenDauer = []
        self.stab_ventilspannung_einlass = []
        self.stab_ventilspannung_durchlass = []
        self.stab_druck = []
        self.stab_stufendauer = []
        self.stab_v_durchlass_steigend = []
        self.stab_druck_durchlass_steigend = []
        self.stab_v_durchlass_fallend = []
        self.stab_druck_durchlass_fallend = []
        self.stab_v_einlass_steigend = []
        self.stab_druck_einlass_steigend = []
        self.stab_v_einlass_fallend = []
        self.stab_druck_einlass_fallend = []

    def extractData(self):
        try:
            data = pd.read_csv(self.path, sep=self.sep, decimal=self.decimal, encoding=self.encoding, on_bad_lines=self.on_bad_lines)
            data.columns = data.columns.str.strip()  # Entfernt führende und nachfolgende Leerzeichen aus den Spaltennamen
            print("Gefundene Spalten in der CSV:", list(data.columns))
            
            def clean_to_nan_or_float(series):
                # Falls es schon Zahlen sind, direkt zurückgeben
                if np.issubdtype(series.dtype, np.number):
                    return series.values
                # Falls es Text ist, Leerzeichen weg und zu numeric konvertieren
                return pd.to_numeric(series.astype(str).str.replace(',', '.'), errors='coerce').values
        
            self.zeit = clean_to_nan_or_float(data['Zeit_s'])
            self.Druck = clean_to_nan_or_float(data['Druck_mBar'])
            self.Ventilspannung_Durchlass = clean_to_nan_or_float(data['V_Durchlass'])
            self.Ventilspannung_Einlass = clean_to_nan_or_float(data['V_Einlass'])
            self.Stellgröße = clean_to_nan_or_float(data['Stellgröße']) if 'Stellgröße' in data.columns else None
            self.StufenDauer = data['Dauer bis Druckstabilitaet_s'].values if 'Dauer bis Druckstabilitaet_s' in data.columns else None
            # print(f"Erfolgreich konvertiert! Datentyp von Druck jetzt: {self.Druck.dtype}")
            # print(f"Erster Druckwert: {self.Druck[0]}, Letzter Druckwert: {self.Druck[-1]}")

            for i in range(len(self.StufenDauer)):
                if not pd.isna(self.StufenDauer[i]):
                    self.stab_ventilspannung_einlass.append(self.Ventilspannung_Einlass[i])
                    self.stab_ventilspannung_durchlass.append(self.Ventilspannung_Durchlass[i])
                    self.stab_druck.append(self.Druck[i])
                    self.stab_stufendauer.append(self.StufenDauer[i])

            for i in range(1, len(self.stab_ventilspannung_einlass)):
                v_aktuell = self.stab_ventilspannung_einlass[i]
                v_vorher = self.stab_ventilspannung_einlass[i-1]

                if self.stab_ventilspannung_durchlass[i] == 10:
                    if v_aktuell > v_vorher:
                        self.stab_v_einlass_steigend.append(v_aktuell)
                        self.stab_druck_einlass_steigend.append(self.stab_druck[i])
                    elif v_aktuell < v_vorher:
                        self.stab_v_einlass_fallend.append(v_aktuell)
                        self.stab_druck_einlass_fallend.append(self.stab_druck[i])

            for i in range(1, len(self.stab_ventilspannung_durchlass)):
                v_aktuell = self.stab_ventilspannung_durchlass[i]
                v_vorher = self.stab_ventilspannung_durchlass[i-1]

                if self.stab_ventilspannung_einlass[i] == 0:
                    if v_aktuell > v_vorher:
                        self.stab_v_durchlass_steigend.append(self.stab_ventilspannung_durchlass[i])
                        self.stab_druck_durchlass_steigend.append(self.stab_druck[i])
                    elif v_aktuell < v_vorher:
                        self.stab_v_durchlass_fallend.append(self.stab_ventilspannung_durchlass[i])
                        self.stab_druck_durchlass_fallend.append(self.stab_druck[i])

            print("Erfolgreich Daten extrahiert!")
            return True
        except Exception as e:
            print(f"Fehler beim Laden: {e}")
            return False
        
    def inputPath(self):
        pfad = input("Geben Sie den Pfad zur CSV-Datei ein: ").strip().replace('"', '')
        self.path = pfad
        
        


        #Pfad = r"C:\Users\labor\Documents\messung_ventil_mehr_stützpunkte_gut.csv"
class CreateCSV:
    def __init__(self):
        self.filename = None
        self.path = None
        self.full_path = None
        self.buffer = []

    def pathRequest(self):
        pfad = input("Geben Sie den Pfad/Ort an, an der die CSV-Datei gespeichert werden soll: ").strip().replace('"', '')
        self.path = pfad
        if self.path != "." and not self.path.endswith('\\') and not self.path.endswith('/'):
            self.path += '\\'
        
    def allocateCSV(self):
        self.filename = f"messung_{time.strftime('%Y%m%d-%H%M%S')}.csv"
        self.pathRequest()
        if self.path == ".":
            self.full_path = self.filename
        else:
            self.full_path = self.path + self.filename

        with open(self.full_path, mode='w', newline='') as f:
            writer = csv.writer(f, delimiter=';')
            writer.writerow(['Zeit_s', 'Druck_mBar', 'V_Durchlass', 'V_Einlass', 'Stellgröße', 'response'])

    def writeToCSV(self, zeit, druck, v_durchlass, v_einlass, stellgröße, response):
        t_str = f"{zeit:.3f}".replace('.', ',')
        p_str = f"{druck:.5f}".replace('.', ',')
        vd_str = f"{v_durchlass:.2f}".replace('.', ',')
        ve_str = f"{v_einlass:.2f}".replace('.', ',')
        stellgröße_str = f"{stellgröße:.5f}".replace('.', ',')
        response_str = f"{response}".replace('.', ',')
        self.buffer.append([t_str, p_str, vd_str, ve_str, stellgröße_str]) 
        try:
            with open(self.full_path, mode='a', newline='') as f:
                writer = csv.writer(f, delimiter=';')
                while self.buffer:
                    writer,writerrow(self.buffer[0])
                    self.buffer.pop(0)
        except PermissionError:
            print("Fehler: CSV Datei konnte nicht geöffnet werden. (Ist die Datei parallel geöffnet?)")
            pass
        





if __name__ == "__main__":
    csv_reader = CSVReader(pfad=r"C:\Users\labor\Documents\messung_ventil_mehr_stützpunkte_gut.csv")
    if csv_reader.get_arrays_from_csv():
        print("Arrays erfolgreich geladen.")
    else:
        print("Fehler beim Laden der Arrays.")
