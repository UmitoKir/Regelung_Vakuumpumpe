#install the driver software NI-DAQ™mx
#install all the necessary libaries and debugger/compiler(python, python debugger, git etc.) to get it running on VS code
#install with py -m pip install in the terminal all the necessary packages
#matplotlib maybe also required

import pandas as pd 
import matplotlib.pyplot as plt
import numpy as np
from scipy.interpolate import CubicSpline
from scipy.interpolate import interp1d
from scipy.interpolate import PchipInterpolator

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
v_einlass_steigend = []
v_einlass_fallend = []
v_durchlass_steigend = []
v_durchlass_fallend = []
druck_einlass_steigend = []
druck_einlass_fallend = []
druck_durchlass_steigend = []
druck_durchlass_fallend = []


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
        StufenDauer = df['Dauer bis Druckstabilitaet_s'].values
    except Exception as e:
        print(f"Fehler beim Laden: {e}")
        return False
    return True
       

def logistische_funktion(x, L, k, x0):
    return L / (1 + np.exp(-k * (x - x0)))

def interpolation(ventilspannungen, druck):
    #interpolation
    x_interp, y_interp, y_interp2, y_interp_pchip = None, None, None, None


    if len(ventilspannungen) > 1:
        v_data = np.array(ventilspannungen)
        p_data = np.array(druck)
        idx = np.argsort(v_data)
        v_sorted = v_data[idx]
        p_sorted = p_data[idx]
        v_unique, unique_idx = np.unique(v_sorted, return_index=True)
        p_unique = p_sorted[unique_idx]
        
        if len(v_unique) > 1:
            cs = CubicSpline(v_unique, p_unique, bc_type='clamped')
            x_interp = np.linspace(min(v_unique), max(v_unique), 500)
            y_interp_cubic = cs(x_interp)

            pchip = PchipInterpolator(v_unique, p_unique)
            y_interp_pchip = pchip(x_interp)

        idx_inv = np.argsort(p_unique)
        p_inv_sorted = p_unique[idx_inv]
        v_inv_sorted = v_unique[idx_inv]
        p_inv_final, inv_unique_idx = np.unique(p_inv_sorted, return_index=True)
        v_inv_final = v_inv_sorted[inv_unique_idx]
        if len(p_inv_final) > 1:

            x_interp_pchip = PchipInterpolator(p_inv_final, v_inv_final)

            Druckwerte = [900, 800, 700, 600, 500, 400, 300, 200, 100, 90, 80, 70, 60, 50, 40, 30, 20, 10, 9, 8, 7, 6, 5, 4, 3, 2, 1, 0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.3, 0.2, 0.1, 0.09, 0.08, 0.07, 0.06, 0.05, 0.04, 0.03, 0.02, 0.01, 0.009, 0.008, 0.007, 0.006, 0.005, 0.004, 0.003, 0.002, 0.001]
            #nur Werte abfragen die auch gemessen werden konnten
            Druckwerte_valid = [p for p in Druckwerte if min(p_inv_final) <= p <= max(p_inv_final)]
            Ventilspannungen_interp = x_interp_pchip(Druckwerte_valid)

            print("\n--- Interpolierte Sollwerte (PCHIP Invers) ---")
            print("Druck [mBar]  ->  Benötigte Spannung [V]")
            for p, v in zip(Druckwerte, Ventilspannungen_interp):
                print(f"{p:12.4f}  ->  {v:6.3f} V")
            
        if len(v_unique) > 2:
            # 'quadratic' entspricht dem 2. Grad
            f_quad = interp1d(v_unique, p_unique, kind='quadratic', fill_value="extrapolate")
            y_interp_2 = f_quad(x_interp)
        return x_interp, y_interp_cubic, y_interp_2, y_interp_pchip
    else:
        return None, None, None, None


def main():
    global Ableitung, Druck, Ventilspannung_Durchlass, Ventilspannung_Einlass, zeit, StufenDauer, stab_druck
    global v_einlass_steigend, v_einlass_fallend, druck_einlass_steigend, druck_einlass_fallend,  v_durchlass_steigend, v_durchlass_fallend, druck_durchlass_steigend, druck_durchlass_fallend
    Pfad = input("Geben Sie den Pfad zur CSV-Datei ein: ").strip().replace('"', '')

    if not get_arrays_from_csv(Pfad):
        return

    for i in range(len(Druck)-1):
        tangente = (Druck[i+1] - Druck[i]) / (zeit[i+1] - zeit[i])
        Ableitung.append(tangente)
    
    for i in range(len(StufenDauer)):
        if not pd.isna(StufenDauer[i]):
            stab_ventilspannung_einlass.append(Ventilspannung_Einlass[i])
            stab_ventilspannung_durchlass.append(Ventilspannung_Durchlass[i])
            stab_druck.append(Druck[i])

    for i in range(1, len(stab_ventilspannung_einlass)):
        v_aktuell = stab_ventilspannung_einlass[i]
        v_vorher = stab_ventilspannung_einlass[i-1]
        
        if stab_ventilspannung_durchlass[i] == 10:
            if v_aktuell > v_vorher:
                v_einlass_steigend.append(v_aktuell)
                druck_einlass_steigend.append(stab_druck[i])
            elif v_aktuell < v_vorher:
                v_einlass_fallend.append(v_aktuell)
                druck_einlass_fallend.append(stab_druck[i])

    for i in range(1, len(stab_ventilspannung_durchlass)):
        v_aktuell = stab_ventilspannung_durchlass[i]
        v_vorher = stab_ventilspannung_durchlass[i-1]
        
        if stab_ventilspannung_einlass[i] == 0:
            if v_aktuell > v_vorher:
                v_durchlass_steigend.append(v_aktuell)
                druck_durchlass_steigend.append(stab_druck[i])
            elif v_aktuell < v_vorher:
                v_durchlass_fallend.append(v_aktuell)
                druck_durchlass_fallend.append(stab_druck[i])

    #interpolation
    x_interp_f_ein, y_interp_f_ein, y_interp2_f_ein, y_interp_pchip_f_ein = None, None, None, None
    x_interp_s_ein, y_interp_s_ein, y_interp2_s_ein, y_interp_pchip_s_ein = None, None, None, None
    x_interp_f_durch, y_interp_f_durch, y_interp2_f_durch, y_interp_pchip_f_durch = None, None, None, None
    x_interp_s_durch, y_interp_s_durch, y_interp2_s_durch, y_interp_pchip_s_durch = None, None, None, None


    if len(v_einlass_fallend) > 1:
        v_data = np.array(v_einlass_fallend)
        p_data = np.array(druck_einlass_fallend)
        idx = np.argsort(v_data)
        v_sorted = v_data[idx]
        p_sorted = p_data[idx]
        v_unique, unique_idx = np.unique(v_sorted, return_index=True)
        p_unique = p_sorted[unique_idx]
        
        if len(v_unique) > 1:
            cs = CubicSpline(v_unique, p_unique, bc_type='clamped')
            x_interp_f_ein = np.linspace(min(v_unique), max(v_unique), 500)
            y_interp_f_ein = cs(x_interp_f_ein)

            pchip = PchipInterpolator(v_unique, p_unique)
            y_interp_pchip_f_ein = pchip(x_interp_f_ein)

        idx_inv = np.argsort(p_unique)
        p_inv_sorted = p_unique[idx_inv]
        v_inv_sorted = v_unique[idx_inv]
        p_inv_final, inv_unique_idx = np.unique(p_inv_sorted, return_index=True)
        v_inv_final = v_inv_sorted[inv_unique_idx]
        if len(p_inv_final) > 1:

            x_interp_pchip_f_ein = PchipInterpolator(p_inv_final, v_inv_final)

            Druckwerte = [900, 800, 700, 600, 500, 400, 300, 200, 100, 90, 80, 70, 60, 50, 40, 30, 20, 10, 9, 8, 7, 6, 5, 4, 3, 2, 1, 0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.3, 0.2, 0.1, 0.09, 0.08, 0.07, 0.06, 0.05, 0.04, 0.03, 0.02, 0.01, 0.009, 0.008, 0.007, 0.006, 0.005, 0.004, 0.003, 0.002, 0.001]
            #nur Werte abfragen die auch gemessen werden konnten
            Druckwerte_valid = [p for p in Druckwerte if min(p_inv_final) <= p <= max(p_inv_final)]
            Ventilspannungen_interp = x_interp_pchip_f_ein(Druckwerte_valid)

            print("\n--- Interpolierte Sollwerte (PCHIP Invers) ---")
            print("Druck [mBar]  ->  Benötigte Spannung [V]")
            for p, v in zip(Druckwerte, Ventilspannungen_interp):
                print(f"{p:12.4f}  ->  {v:6.3f} V")
            
        if len(v_unique) > 2:
            # 'quadratic' entspricht dem 2. Grad
            f_quad = interp1d(v_unique, p_unique, kind='quadratic', fill_value="extrapolate")
            y_interp2_f_ein = f_quad(x_interp_f_ein)
     


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

    """
    plt.figure(3, figsize=(10, 6))
    plt.plot(zeit[:-1], Ableitung, color='red', linewidth=1.5)
    plt.grid(True, which="both", ls="-", alpha=0.5)
    plt.title(f"Ableitung des Drucks mBar")
    plt.xlabel("Zeit [s]")
    plt.ylabel("Druckableitung [mbar/s]")
    """
    
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
    plt.plot(v_einlass_fallend, druck_einlass_fallend, 'o-', color='blue', linewidth=1.5, label='Messpunkte fallend')
    plt.plot(v_einlass_steigend, druck_einlass_steigend, 'o-', color='green', linewidth=1.5, label='Messpunkte steigend')
    plt.plot(x_interp_f, y_interp_f, color='red', linewidth=1.5, label='Kubische Spline-Interpolation')
    plt.plot(x_interp_f, y_interp2_f, color='pink', linewidth=1.5, label='quadratische-Interpolation')
    plt.plot(x_interp_f, y_interp_pchip_f, color='orange', linewidth=1.5, label='PCHIP-Interpolation')
    plt.gca().invert_xaxis()
    plt.grid(True, which="both", ls="-", alpha=0.5)
    plt.title(f"Eingeschwungener Druck in mBar (lin)")
    plt.xlabel("Einlassventilspannung [V]")
    plt.ylabel("Druck [mbar]")
    plt.legend()

    plt.figure(6,figsize=(10, 6))
    plt.plot(v_einlass_fallend, druck_einlass_fallend, 'o-', color='blue', linewidth=1.5, label='Messpunkte fallend')
    plt.plot(v_einlass_steigend, druck_einlass_steigend, 'o-', color='green', linewidth=1.5, label='Messpunkte steigend')
    plt.plot(x_interp_f, y_interp_f, color='red', linewidth=1.5, label='Kubische Spline-Interpolation')
    plt.plot(x_interp_f, y_interp2_f, color='pink', linewidth=1.5, label='quadratische-Interpolation')
    plt.plot(x_interp_f, y_interp_pchip_f, color='orange', linewidth=1.5, label='PCHIP-Interpolation')
    plt.gca().invert_xaxis()
    plt.yscale('log')
    plt.grid(True, which="both", ls="-", alpha=0.5)
    plt.title(f"Eingeschwungener Druck in mBar (log)")
    plt.xlabel("Einlassventilspannung [V]")
    plt.ylabel("Druck [mbar]")
    plt.legend()

    plt.figure(7,figsize=(10, 6))
    plt.plot(v_durchlass_fallend, druck_durchlass_fallend, 'o-', color='blue', linewidth=1.5, label='Messpunkte fallend')
    plt.plot(v_durchlass_steigend, druck_durchlass_steigend, 'o-', color='green', linewidth=1.5, label='Messpunkte steigend')
    #plt.plot(x_interp_f, y_interp_f, color='red', linewidth=1.5, label='Kubische Spline-Interpolation')
    #plt.plot(x_interp_f, y_interp2_f, color='pink', linewidth=1.5, label='quadratische-Interpolation')
    #plt.plot(x_interp_f, y_interp_pchip_f, color='orange', linewidth=1.5, label='PCHIP-Interpolation')
    plt.gca().invert_xaxis()
    plt.grid(True, which="both", ls="-", alpha=0.5)
    plt.title(f"Eingeschwungener Druck in mBar (lin)")
    plt.xlabel("Durchlassventilspannung [V]")
    plt.ylabel("Druck [mbar]")
    plt.legend()

    plt.figure(8,figsize=(10, 6))
    plt.plot(v_durchlass_fallend, druck_durchlass_fallend, 'o-', color='blue', linewidth=1.5, label='Messpunkte fallend')
    plt.plot(v_durchlass_steigend, druck_durchlass_steigend, 'o-', color='green', linewidth=1.5, label='Messpunkte steigend')
    #plt.plot(x_interp_f, y_interp_f, color='red', linewidth=1.5, label='Kubische Spline-Interpolation')
    #plt.plot(x_interp_f, y_interp2_f, color='pink', linewidth=1.5, label='quadratische-Interpolation')
    #plt.plot(x_interp_f, y_interp_pchip_f, color='orange', linewidth=1.5, label='PCHIP-Interpolation')
    plt.gca().invert_xaxis()
    plt.yscale('log')
    plt.grid(True, which="both", ls="-", alpha=0.5)
    plt.title(f"Eingeschwungener Druck in mBar (log)")
    plt.xlabel("Durchlassventilspannung [V]")
    plt.ylabel("Druck [mbar]")
    plt.legend()

    plt.tight_layout()

    plt.show()

main()
