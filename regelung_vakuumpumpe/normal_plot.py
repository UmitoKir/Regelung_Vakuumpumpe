#install the driver software NI-DAQ™mx
#install all the necessary libaries and debugger/compiler(python, python debugger, git etc.) to get it running on VS code
#install with py -m pip install in the terminal all the necessary packages
#matplotlib maybe also required

import pandas as pd 
import matplotlib.pyplot as plt
import numpy as np


Druck = []
zeit = []
Ventilspannung_Durchlass = []
Ventilspannung_Einlass = []
Stellgröße = []

def get_arrays_from_csv(dateipfad):
    global zeit, Druck, Ventilspannung_Durchlass, Ventilspannung_Einlass, Stellgröße
    try:
        df = pd.read_csv(dateipfad, sep=';', decimal=',', encoding='cp1252', on_bad_lines='skip')
        df.columns = df.columns.str.strip()  # Entfernt führende und nachfolgende Leerzeichen aus den Spaltennamen
        print("Gefundene Spalten in der CSV:", list(df.columns))
        # Helferfunktion, um Text-Spalten rigoros in echte Zahlen umzuwandeln
        def clean_to_nan_or_float(series):
            # Falls es schon Zahlen sind, direkt zurückgeben
            if np.issubdtype(series.dtype, np.number):
                return series.values
            # Falls es Text ist, Leerzeichen weg und zu numeric konvertieren
            return pd.to_numeric(series.astype(str).str.replace(',', '.'), errors='coerce').values
        
        zeit = clean_to_nan_or_float(df['Zeit_s'])
        Druck = clean_to_nan_or_float(df['Druck_mBar'])
        Ventilspannung_Durchlass = clean_to_nan_or_float(df['V_Durchlass'])
        Ventilspannung_Einlass = clean_to_nan_or_float(df['V_Einlass'])
        Stellgröße = clean_to_nan_or_float(df['Stellgröße'])
        print(f"Erfolgreich konvertiert! Datentyp von Druck jetzt: {Druck.dtype}")
        print(f"Erster Druckwert: {Druck[0]}, Letzter Druckwert: {Druck[-1]}")
    except Exception as e:
        print(f"Fehler beim Laden: {e}")
        return False
    return True

def main():
    global Druck, Ventilspannung_Durchlass, Ventilspannung_Einlass, zeit, Stellgröße
    
    Pfad = input("Geben Sie den Pfad zur CSV-Datei ein: ").strip().replace('"', '')
    flag = get_arrays_from_csv(Pfad)

    if not flag:
        print("Fehler beim Laden der CSV-Datei. Bitte überprüfen Sie den Pfad und die Datei.")
        return
    

    plt.figure(1,figsize=(10, 6))
    plt.plot(zeit, Druck, color='red', linewidth=1.5)
    plt.grid(True, which="both", ls="-", alpha=0.5)
    plt.title(f"Druckverlauf in mBar (lineare Y-Achse)")
    plt.xlabel("Zeit [s]")
    plt.ylabel("Druck [mbar]")

    plt.figure(2, figsize=(10, 6))
    plt.plot(zeit, Druck, color='red', linewidth=1.5)
    plt.yscale('log')
    plt.grid(True, which="both", ls="-", alpha=0.5)
    plt.title(f"Druckverlauf in mBar (logarithmische Y-Achse)")
    plt.xlabel("Zeit [s]")
    plt.ylabel("Druck [mbar]")


    plt.figure(3,figsize=(10, 6))
    plt.plot(zeit, Ventilspannung_Durchlass, color='blue', linewidth=1.5, label='Durchlassventil')
    plt.plot(zeit, Ventilspannung_Einlass, color='red', linewidth=1.5, label='Einlassventil')
    plt.grid(True, which="both", ls="-", alpha=0.5)
    plt.title(f"Ventilspannungen im Verlauf der Zeit")
    plt.xlabel("Zeit [s]")
    plt.ylabel("Spannung [V]")
    plt.legend()

    plt.figure(4,figsize=(10, 6))
    plt.plot(zeit, Stellgröße, color='blue', linewidth=1.5)
    plt.grid(True, which="both", ls="-", alpha=0.5)
    plt.title(f"Stellgröße im Verlauf der Zeit")
    plt.xlabel("Zeit [s]")
    plt.ylabel("Stellgröße [V]")
    plt.tight_layout()

    plt.show()

main()
