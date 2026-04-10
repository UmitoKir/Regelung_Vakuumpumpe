#install the driver software NI-DAQ™mx
#install all the necessary libaries and debugger/compiler(python, python debugger, git etc.) to get it running on VS code
#install with py -m pip install in the terminal all the necessary packages
#matplotlib maybe also required

import pandas as pd 
import matplotlib.pyplot as plt
from matplotlib import cm
import numpy as np
from scipy.interpolate import griddata
#from matplotlib.colors import LogNorm



Druck = []
zeit = []
Ventilspannung_Durchlass = []
Ventilspannung_Einlass = []
StufenDauer = []
stab_druck = []
stab_ventilspannung_einlass = []
stab_ventilspannung_durchlass = []
stab_dauer = []

Dauer = 1200.0

untere_hystere = False
obere_hystere = False

csv_buffer = []

def get_arrays_from_csv(dateipfad):
    global zeit, Druck, Ventilspannung_Durchlass, Ventilspannung_Einlass, StufenDauer
    try:
        df = pd.read_csv(dateipfad, sep=';', decimal=',', encoding='cp1252')
        df.columns = df.columns.str.strip()  # Entfernt führende und nachfolgende Leerzeichen aus den Spaltennamen
        zeit = df['Zeit_s'].values
        Druck = df['Druck_mBar'].values
        Ventilspannung_Durchlass = df['V_Durchlass'].values
        Ventilspannung_Einlass = df['V_Einlass'].values
        StufenDauer = df['Dauer bis Druckstabilitaet_s'].values
    except Exception as e:
        print(f"Fehler beim Laden: {e}")
        return

       



def main():
    global Ableitung, Druck, Ventilspannung_Durchlass, Ventilspannung_Einlass, zeit, StufenDauer, stab_druck, stab_dauer
    Pfad = input("Geben Sie den Pfad zur CSV-Datei ein: ").strip().replace('"', '')

    get_arrays_from_csv(Pfad)
    
    for i in range(len(StufenDauer)):
        if not pd.isna(StufenDauer[i]):
            stab_ventilspannung_einlass.append(Ventilspannung_Einlass[i])
            stab_ventilspannung_durchlass.append(Ventilspannung_Durchlass[i])
            stab_druck.append(Druck[i])
            stab_dauer.append(StufenDauer[i])

    x_unique = np.unique(stab_ventilspannung_einlass)
    y_unique = np.unique(stab_ventilspannung_durchlass)
    X, Y = np.meshgrid(x_unique, y_unique)

    points = (stab_ventilspannung_einlass, stab_ventilspannung_durchlass)
    Z = griddata(points, stab_druck, (X,Y), method = 'linear')
    F_achse = griddata(points, stab_dauer, (X,Y), method = 'linear')
    
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

    fig = plt.figure(7, figsize=(14, 9))
    ax = fig.add_subplot(111, projection='3d')
    min_d, max_d = np.nanmin(F_achse), np.nanmax(F_achse)
    norm = plt.Normalize(min_d, max_d)
    colors = cm.viridis(norm(F_achse))

    surf = ax.plot_surface(X, Y, Z, facecolors=colors, shade=False, linewidth=0, antialiased=True, alpha=0.9)
    m = cm.ScalarMappable(cmap=cm.viridis, norm=norm)
    m.set_array(F_achse)
    cbar = fig.colorbar(m, ax=ax, shrink=0.5, aspect=10)
    cbar.set_label('Dauer bis stabiler Druckwert (s)')

    # Beschriftung
    ax.set_xlabel('V_Einlass (V)')
    ax.set_ylabel('V_Durchlass (V)')
    ax.set_zlabel('Druck (mBar)')
    ax.set_title('4D-Analyse: Einschwingdauer vs. Druckzustand')

    fig = plt.figure(8, figsize=(14, 9))
    ax = fig.add_subplot(111, projection='3d')

    # 1. Z-Achse: Druck logarithmisch transformieren
    # Wir nutzen log10(Druck). 1000 mBar -> 3, 1 mBar -> 0, 0.001 mBar -> -3
    Z_log = np.log10(np.maximum(Z, 1e-4)) 

    # 2. Farbe: Dauer (F_achse) normieren
    min_f, max_f = np.nanmin(F_achse), np.nanmax(F_achse)
    norm_dauer = plt.Normalize(min_f, max_f)
    colors = cm.plasma(norm_dauer(F_achse)) # 'plasma' ist oft gut für Zeitwerte

    # 3. Surface Plot
    surf = ax.plot_surface(X, Y, Z_log, facecolors=colors, 
                           shade=False, linewidth=0, antialiased=True, alpha=0.9)

    # 4. Z-Achsen-Beschriftung manuell auf Log-Werte setzen
    # Wir definieren die Drücke, die wir als Beschriftung sehen wollen
    z_ticks_mbar = [1000, 100, 10, 1, 0.1, 0.01, 0.001, 0.0001]
    ax.set_zticks(np.log10(z_ticks_mbar))
    ax.set_zticklabels([str(t) for t in z_ticks_mbar])
    ax.set_zlabel('Druck [mBar] (logarithmische Skala)')

    # 5. Colorbar für die DAUER
    m = cm.ScalarMappable(cmap=cm.plasma, norm=norm_dauer)
    m.set_array(F_achse)
    cbar = fig.colorbar(m, ax=ax, shrink=0.5, aspect=10)
    cbar.set_label('Dauer bis Stabilität (s)')

    ax.set_xlabel('V_Einlass (V)')
    ax.set_ylabel('V_Durchlass (V)')
    ax.set_title('Charakteristik: Druckzustand (Höhe) vs. Einstellzeit (Farbe)')

    plt.tight_layout()

    plt.show()

main()
