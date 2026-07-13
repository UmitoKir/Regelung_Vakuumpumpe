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
p_anteil = []
i_anteil = []
d_anteil = []


def get_arrays_from_csv(dateipfad):
    global zeit, Druck, Ventilspannung_Durchlass, Ventilspannung_Einlass, Stellgröße, p_anteil, i_anteil, d_anteil
    try:
        spalten = ['Zeit_s', 'Druck_mBar', 'V_Durchlass', 'V_Einlass', 'Stellgröße', 'P-Anteil', 'I-Anteil', 'D-Anteil', 'response']
        df = pd.read_csv(dateipfad, sep=';', decimal=',', encoding='cp1252', on_bad_lines='skip', usecols=spalten)
        df.columns = df.columns.str.strip()  # Entfernt führende und nachfolgende Leerzeichen aus den Spaltennamen
        print("Gefundene Spalten in der CSV:", list(df.columns))
        # Helferfunktion, um Text-Spalten rigoros in echte Zahlen umzuwandeln
        def clean_to_nan_or_float(series):
            # Falls es schon Zahlen sind, direkt zurückgeben
            if np.issubdtype(series.dtype, np.number):
                return series.to_numpy(dtype=float)
            clean_str = series.astype(str).str.strip()
            return pd.to_numeric(clean_str, errors="coerce").to_numpy(dtype=float)
        
        zeit =clean_to_nan_or_float(df['Zeit_s'])
        Druck = clean_to_nan_or_float(df['Druck_mBar'])
        Ventilspannung_Durchlass = clean_to_nan_or_float(df['V_Durchlass'])
        Ventilspannung_Einlass = clean_to_nan_or_float(df['V_Einlass'])
        Stellgröße = clean_to_nan_or_float(df['Stellgröße'])
        p_anteil = clean_to_nan_or_float(df['P-Anteil'])
        i_anteil = clean_to_nan_or_float(df['I-Anteil'])
        d_anteil = clean_to_nan_or_float(df['D-Anteil'])
        print(f"Erfolgreich konvertiert! Datentyp von Druck jetzt: {Druck.dtype}")
        print(f"Erster Druckwert: {Druck[0]}, Letzter Druckwert: {Druck[-1]}")
    except Exception as e:
        print(f"Fehler beim Laden: {e}")
        return False
    return True

def main():
    global Druck, Ventilspannung_Durchlass, Ventilspannung_Einlass, zeit, Stellgröße, p_anteil, i_anteil, d_anteil
    
    Pfad = input("Geben Sie den Pfad zur CSV-Datei ein: ").strip().replace('"', '')
    flag = get_arrays_from_csv(Pfad)

    if not flag:
        print("Fehler beim Laden der CSV-Datei. Bitte überprüfen Sie den Pfad und die Datei.")
        return
    

    plt.figure(1,figsize=(10, 6))
    plt.plot(zeit, Druck, color='red', linewidth=1.5)
    plt.grid(True, which="both", ls="-", alpha=0.5)
    plt.title("Druckverlauf in mBar (lineare Y-Achse)")
    plt.xlabel("Zeit [s]")
    plt.ylabel("Druck [mbar]")

    plt.figure(2, figsize=(10, 6))
    plt.plot(zeit, Druck, color='red', linewidth=1.5)
    plt.yscale('log')
    plt.grid(True, which="both", ls="-", alpha=0.5)
    plt.title("Druckverlauf in mBar (logarithmische Y-Achse)")
    plt.xlabel("Zeit [s]")
    plt.ylabel("Druck [mbar]")


    plt.figure(3,figsize=(10, 6))
    plt.plot(zeit, Ventilspannung_Durchlass, color='blue', linewidth=1.5, label='Durchlassventil')
    plt.plot(zeit, Ventilspannung_Einlass, color='red', linewidth=1.5, label='Einlassventil')
    plt.grid(True, which="both", ls="-", alpha=0.5)
    plt.title("Ventilspannungen im Verlauf der Zeit")
    plt.xlabel("Zeit [s]")
    plt.ylabel("Spannung [V]")
    plt.legend()

    plt.figure(4,figsize=(10, 6))
    plt.plot(zeit, Stellgröße, color='black', linewidth=2.5, label="Gesamt-Stellgröße (U)")
    plt.plot(zeit, p_anteil, color='blue', linewidth=1.5, label="P-Anteil")
    plt.plot(zeit, i_anteil, color='green', linewidth=1.5, label="I-Anteil")
    plt.plot(zeit, d_anteil, color='red', linewidth=1.5, label="D-Anteil")
    plt.grid(True, which="both", ls="-", alpha=0.5)
    plt.title("Stellgrößen im Verlauf der Zeit")
    plt.xlabel("Zeit [s]")
    plt.ylabel("Stellgröße [V]")
    plt.legend(loc="best", fontsize="small")
    plt.tight_layout()

    plt.show()

main()
