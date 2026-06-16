#install the driver software NI-DAQ™mx
#install all the necessary libaries and debugger/compiler(python, python debugger, git etc.) to get it running on VS code
#install with py -m pip install in the terminal all the necessary packages
#matplotlib maybe also required

import pandas as pd 
import numpy as np
from scipy.interpolate import PchipInterpolator

# kp=0.1 #0.1152; 0.2 für 400mBar
# ki= 0.01 #0.0002 #0.2 standartmäßig; 0.02 für 400mBar
# dt = 1
# old_pressure = 1000

# counter_limit = 100
# Dauer = 300
# Max_dauer = 1500

# raw_array = b""
# resp_array = ""
# response_array = ""


# Druck = []
# zeit = []
# Ventilspannung_Durchlass = []
# Ventilspannung_Einlass = []
# StufenDauer = []
# stab_druck = []
# stab_ventilspannung_einlass = []
# stab_ventilspannung_durchlass = []
# lut_v_einlass_steigend = []
# lut_v_einlass_fallend = []
# lut_v_durchlass_steigend = []
# lut_v_durchlass_fallend = []
# druck_einlass_steigend = []
# druck_einlass_fallend = []
# druck_durchlass_steigend = []
# druck_durchlass_fallend = []
# fehler_historie = []

# untere_hystere = False
# obere_hystere = False
# history_hp = []

# csv_buffer = [] 

"""
def find_device():
    ports = list(serial.tools.list_ports.comports()) #ruft eine Liste mit allen existierenden Anschlüssen an Ihrem Computer ab
    sp=None
    #durch Vergleichen der Namen von allen Anschlüssen mit dem Namen vom Adapter RS232 zu usb wählt es den richtigen Port aus.
    print(f'Liste der angeschlossenen Geräte: {ports}')
    for p in ports:
        print(p)
        if 'ATEN'in p.description:
            print(f'this is the Device: {p.device}')
            sp=p.device
        if sp is None:
            print('Das Gerät wurde nicht gefunden.')
    return sp


def getpressure(ser): #"Druckauslesebefehl"
    try:
        raw = ser.readline()
        raw_array = raw
        resp = raw.decode('utf-8', errors='ignore') #liest die Werte vom CenterThree
        resp_array = resp
        response = resp.strip()
        response_array = response

        #response = ser.readline().decode('utf-8').strip() #liest die Werte vom CenterThree
        if response:
            #print(f'Antwort: {response}')
            values = response.split(",")
            values = [float(values[i]) for i in (1,3)]
            #print(f"Druckwerte: {values}")
            return values, raw_array, resp_array, response_array
        else:
            print('keine Antwort. ')
            ser.flushInput()
            return None, None, None, None
    except (ValueError, UnicodeDecodeError, IndexError) as e:
        print(f"Fehler bei der Druckauslesung: {e} | {response if 'response' in locals() else 'unbekannt'}" )
        ser.flushInput() # Puffer leeren 
        return None, None, None, None
    
def sensorwahl_mit_hysterese(pressure, untere_hystere, obere_hystere, old_pressure):

    if pressure[0]>= 1.0: # ab >= 1mBar immer sensor 1 verwenden
        istWert = pressure[0] #round(pressure[0], 2) #round(hp_smooth, 2)
        untere_hystere = False
    elif pressure[1]< 0.5: #ab <0.5mBar immer sensor 2 verwenden
        istWert = pressure[1]
        obere_hystere = False
    elif pressure[1] >= 0.5 and old_pressure < pressure[1] and old_pressure < 0.5: #wenn man von < 0.5mBar kommt und < 1.0mBar ist. -> sensor 2 verwenden
        istWert = pressure[1]
        untere_hystere = True
    elif pressure[1] >= 0.5 and untere_hystere == True: #wenn man von < 0.5mBar kommt und < 1.0mBar ist. -> sensor 2 verwenden
        istWert = pressure[1]
    elif pressure[0] < 1.0 and old_pressure >= pressure[0] and old_pressure >=1.0: #wenn man von > 1.0mBar kommt und > 0.1mBar ist. -> sensor 1 verwenden
        istWert = pressure[0]
        obere_hystere = True
    elif pressure[0] < 1.0 and obere_hystere == True: #wenn man
        istWert = pressure[0]
    if istWert <=0:
        istWert = 1e-4
    return istWert


def pressure_error_handler(ser, pressure, filename, Startzeit):
    retry_count = 0
    while pressure is None and retry_count < 20:
            pressure = getpressure(ser)
            if pressure is None:
                retry_count += 1
                time.sleep(0.1)
        
    if pressure is None: 
        print("Kritischer Fehler: Antwort vom Sensor auch nach 20 versuchen nicht sauber")
        try: 
            with open (filename, mode='a', newline='') as f:
                writer = csv.writer(f, delimiter=';')
                writer.writerow([f"{Startzeit:.3f}".replace('.', ','), "ERROR", 0, 0, "Sensor Timeout", "", "", ""])
        except PermissionError :
            print("Fehler: CSV Datei konnte nicht geöffnet werden. (Datei offen?)")
            pass
        return False
    return pressure
"""

def get_arrays_from_csv(dateipfad):
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
        Stellgröße = clean_to_nan_or_float(df['Stellgröße']) if 'Stellgröße' in df.columns else None
        StufenDauer = df['Dauer bis Druckstabilitaet_s'].values if 'Dauer bis Druckstabilitaet_s' in df.columns else None
        print(f"Erfolgreich konvertiert! Datentyp von Druck jetzt: {Druck.dtype}")
        print(f"Erster Druckwert: {Druck[0]}, Letzter Druckwert: {Druck[-1]}")
        return zeit, Druck, Ventilspannung_Durchlass, Ventilspannung_Einlass, Stellgröße, StufenDauer
    except Exception as e:
        print(f"Fehler beim Laden: {e}")
        return None, None, None, None, None





def max_fehler_bestimmung(istWert):
    if istWert < 7.5 * 1e-4:
        fehler_grenze = 0.02
    elif istWert < 1e-3:
        fehler_grenze = 0.0134
    elif istWert < 2.5*1e-3:
        fehler_grenze = 0.01
    elif istWert < 5*1e-3:
        fehler_grenze = 0.004
    elif istWert < 7.5*1e-3:
        fehler_grenze = 0.002
    elif istWert < 1e-2:
        fehler_grenze = 0.0015
    elif istWert >= 1*1e-2 and istWert < 5*1e-1:
        fehler_grenze = 0.001
    elif istWert >= 5*1e-1 and istWert < 7.5*1e-1:
        fehler_grenze = 0.02
    elif istWert >= 7.5 * 1e-1 and istWert < 1.0:
        fehler_grenze = 0.014
    elif istWert >= 1.0 and istWert < 2.5:
        fehler_grenze = 0.01
    elif istWert >= 2.5 and istWert < 5:
        fehler_grenze = 0.004
    elif istWert >= 5 and istWert < 7.5:
        fehler_grenze = 0.002
    elif istWert >= 7.5 and istWert < 10:
        fehler_grenze = 0.0014
    elif istWert >= 10:
        fehler_grenze = 0.001   
    return fehler_grenze


def interpolierte_Funktion(ventilspannungen, druck):
    v_data = np.array(ventilspannungen)
    p_data = np.array(druck)
    idx_inv = np.argsort(p_data)
    p_inv_sorted = p_data[idx_inv]
    v_inv_sorted = v_data[idx_inv]
    p_inv_final, inv_unique_idx = np.unique(p_inv_sorted, return_index=True)
    v_inv_final = v_inv_sorted[inv_unique_idx]

    if len(p_inv_final) > 1:
        x_interp_pchip = PchipInterpolator(p_inv_final, v_inv_final)
        return x_interp_pchip
    else: 
        return None
    
def x_interpoliert(ventilspannungen, druck):
    v_data = np.array(ventilspannungen)
    p_data = np.array(druck)
    idx = np.argsort(v_data)
    v_sorted = v_data[idx]
    p_sorted = p_data[idx]
    v_unique, unique_idx = np.unique(v_sorted, return_index=True)
    p_unique = p_sorted[unique_idx]
    if len(v_unique) > 1:
        x_interp = np.linspace(min(v_unique), max(v_unique), 100)
        pchip = PchipInterpolator(v_unique, p_unique)
        y_pchip = pchip(x_interp)
        return  x_interp, y_pchip
    else:
        print("Fehler bei der Interpolation")
        return None, None


def steigung(ventilspannungen, druck, pressure, v_ein):
    if len(ventilspannungen) > 1:
        x_interp, y_pchip = x_interpoliert(ventilspannungen, druck)
        if x_interp is None or y_pchip is None:
            print("Fehler bei der Interpolation. Steigungsberechnung nicht möglich.")
            return None, None

        dp_dV = []
        for i in range(len(x_interp)-1):
            delta_v = x_interp[i+1] - x_interp[i]
            delta_p = y_pchip[i+1] - y_pchip[i]
            sekante = abs(delta_p / delta_v)
            dp_dV.append(sekante)
        
        dp_dV.append(dp_dV[-1])
        
        max_idx = np.argmax(dp_dV)
        max_steigung = abs(dp_dV[max_idx])
        max_volt = x_interp[max_idx]
        max_druck = y_pchip[max_idx]

        idx_v_ein = np.abs(x_interp - v_ein).argmin()
        steigung_v_ein = abs(dp_dV[idx_v_ein])

        print("\n=======================================================")
        print(f"-> Höchste Steigung:  {max_steigung:.4f} mBar/V")
        print(f"-> Bei Spannung:      {max_volt:.6f} V")
        print(f"-> Bei Druck:         {max_druck:.4f} mBar")
        print(f"-> Steigung Sollwert: {steigung_v_ein:.4f} mBar/V")
        print(f"-> Bei Spannung:      {v_ein:.6f} V")
        print(f"-> Bei Druck:         {pressure:.4f} mBar")
        return max_steigung, steigung_v_ein
    else:
        print("Nicht genügend Datenpunkte für die Steigungsberechnung.")
        return None, None



def druckeingabe ():
    Solldruck = input("Bitte geben Sie den gewünschten Solldruck in mBar ein: ")
    try:
        return float(Solldruck)
    except ValueError:
        print("Ungültige Eingabe. Bitte geben Sie eine Zahl ein.")
        return druckeingabe()

def PID(sollwert, istwert, prev_error, kp, ki, kd, dt, integral):
    safe_sollwert = max(sollwert, 1e-4)
    safe_istwert = max(istwert, 1e-4)
    
    error = np.log10(safe_sollwert) - np.log10(safe_istwert)
    rel_error = (sollwert - istwert) / sollwert

    integral = integral + (error*dt)    
    derivative = (error - prev_error)/dt
    output = (kp*error)+(ki*integral)+(kd*derivative)
    prev_error = error
    return output, rel_error, derivative, integral


