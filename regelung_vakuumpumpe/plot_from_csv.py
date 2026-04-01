#install the driver software NI-DAQ™mx
#install all the necessary libaries and debugger/compiler(python, python debugger, git etc.) to get it running on VS code
#install with py -m pip install in the terminal all the necessary packages
#matplotlib maybe also required

import pandas as pd 
import matplotlib.pyplot as plt
import numpy as np



Druck = []
Ableitung = []
zeit = []
Ventilspannung_Durchlass = []
Ventilspannung_Einlass = []
modus = []
StufenDauer = []
stab_druck = []
stab_ventilspannung_einlass = []
stab_ventilspannung_durchlass = []

Dauer = 1200.0

ventilspannungen1 = [10, 9.5, 9, 8.5, 8, 7.5, 7, 6.5, 6, 5.5, 5, 4.5, 4, 3.5, 3, 2.5, 2, 1.5, 1, 0.5, 0]
ventilspannungen2 = [0, 0.5, 1, 1.5, 2, 2.5, 3, 3.5, 4, 4.5, 5, 5.5, 6, 6.5, 7, 7.5, 8, 8.5, 9, 9.5, 10]
test_konfigurationen = [
    ("Einlass", ventilspannungen1),
    ("Einlass", ventilspannungen2),
    ("Durchlass", ventilspannungen2),
    ("Durchlass", ventilspannungen1)
]

untere_hystere = False
obere_hystere = False

csv_buffer = []

def get_arrays_from_csv(dateipfad):
    global zeit, Druck, Ventilspannung_Durchlass, Ventilspannung_Einlass, modus, StufenDauer
    try:
        df = pd.read_csv(dateipfad, sep=';', decimal=',', encoding='cp1252')
        df.columns = df.columns.str.strip()  # Entfernt führende und nachfolgende Leerzeichen aus den Spaltennamen
        zeit = df['Zeit_s'].values
        Druck = df['Druck_mBar'].values
        Ventilspannung_Durchlass = df['V_Durchlass'].values
        Ventilspannung_Einlass = df['V_Einlass'].values
        modus = df['Modus'].values
        StufenDauer = df['Dauer bis Druckstabilitaet_s'].values
    except Exception as e:
        print(f"Fehler beim Laden: {e}")
        return

       



def main():
    global Ableitung, Druck, Ventilspannung_Durchlass, Ventilspannung_Einlass, zeit, StufenDauer, stab_druck
    Pfad = input("Geben Sie den Pfad zur CSV-Datei ein: ").strip().replace('"', '')

    get_arrays_from_csv(Pfad)

    for i in range(len(Druck)-1):
        tangente = (Druck[i+1] - Druck[i]) / (zeit[i+1] - zeit[i])
        Ableitung.append(tangente)
    
    for i in range(len(StufenDauer)):
        if not pd.isna(StufenDauer[i]):
            stab_ventilspannung_einlass.append(Ventilspannung_Einlass[i])
            stab_ventilspannung_durchlass.append(Ventilspannung_Durchlass[i])
            stab_druck.append(Druck[i])
    
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

    plt.figure(3, figsize=(10, 6))
    plt.plot(zeit[:-1], Ableitung, color='red', linewidth=1.5)
    plt.grid(True, which="both", ls="-", alpha=0.5)
    plt.title(f"Ableitung des Drucks mBar")
    plt.xlabel("Zeit [s]")
    plt.ylabel("Druckableitung [mbar/s]")
    
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 6))
    ax1.plot(zeit, Ventilspannung_Durchlass, color='blue', linewidth=1.5, label='Durchlassventil')
    ax1.set_title(f"Ventilspannung Durchlassventil")
    ax1.set_xlabel("Zeit [s]")
    ax1.set_ylabel("Spannung [V]")
    ax1.grid(True, which="both", ls="-", alpha=0.5)

    ax2.plot(zeit, Ventilspannung_Einlass, color='red', linewidth=1.5, label='Einlassventil')
    ax2.set_title(f"Ventilspannung Einlassventil")
    ax2.set_xlabel("Zeit [s]")
    ax2.set_ylabel("Spannung [V]")
    ax2.grid(True, which="both", ls="-", alpha=0.5)

    plt.figure(5,figsize=(10, 6))
    plt.plot(stab_ventilspannung_einlass, stab_druck, 'o-', color='blue', linewidth=1.5)
    plt.gca().invert_xaxis()
    plt.grid(True, which="both", ls="-", alpha=0.5)
    plt.title(f"Eingeschwungener Druck in mBar (lin)")
    plt.xlabel("Ventilspannung [V]")
    plt.ylabel("Druck [mbar]")

    plt.figure(6,figsize=(10, 6))
    plt.plot(stab_ventilspannung_einlass, stab_druck, 'o-', color='blue', linewidth=1.5)
    plt.gca().invert_xaxis()
    plt.yscale('log')
    plt.grid(True, which="both", ls="-", alpha=0.5)
    plt.title(f"Eingeschwungener Druck in mBar (log)")
    plt.xlabel("Ventilspannung [V]")
    plt.ylabel("Druck [mbar]")

    plt.tight_layout()

    plt.show()

main()
