#install the driver software NI-DAQ™mx
#install all the necessary libaries and debugger/compiler(python, python debugger, git etc.) to get it running on VS code
#install with py -m pip install in the terminal all the necessary packages
#matplotlib maybe also required

import time
import nidaqmx
import serial
import serial.tools.list_ports
import csv
import pandas as pd 
import numpy as np
from scipy.interpolate import PchipInterpolator


#der folgende Absatz sucht den usb port aus an dem sie die Vakuumpumpe aneschlossen haben
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

br = 38400
to = 1

kp=0.1152
ki=0  # 0.2 #standartmäßig
dt = 1
old_pressure = 1000

counter_limit = 150
Dauer = 300

raw_array = b""
resp_array = ""
response_array = ""


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
#v_durchlass_steigend = []
#v_durchlass_fallend = []
druck_einlass_steigend = []
druck_einlass_fallend = []
#druck_durchlass_steigend = []
#druck_durchlass_fallend = []
fehler_historie = []

untere_hystere = False
obere_hystere = False

csv_buffer = [] 

def getpressure(ser): #"Druckauslesebefehl"
    global raw_array, resp_array, response_array
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
            return values
        else:
            print('keine Antwort. ')
            ser.flushInput()
            return None
        return None
    except (ValueError, UnicodeDecodeError, IndexError) as e:
        print(f"Fehler bei der Druckauslesung: {e} | {response if 'response' in locals() else 'unbekannt'}" )
        ser.flushInput() # Puffer leeren 
        return None

def sensorwahl_mit_hysterese(pressure):
    global untere_hystere, obere_hystere, old_pressure

    istWert = old_pressure

    if pressure[0]>= 1.0: # ab >= 1mBar immer sensor 1 verwenden
        istWert = pressure[0] 
        untere_hystere = False
        #print("Sensor HP")
    elif pressure[1]< 0.5: #ab <0.5mBar immer sensor 2 verwenden
        istWert = pressure[1]
        obere_hystere = False
        #print("Sensor LP")
    elif pressure[1] >= 0.5 and old_pressure < pressure[1] and old_pressure < 0.5: #wenn man von < 0.5mBar kommt und < 1.0mBar ist. -> sensor 2 verwenden
        istWert = pressure[1]
        untere_hystere = True
        #print("Sensor LP")
    elif pressure[1] >= 0.5 and untere_hystere == True: #wenn man von < 0.5mBar kommt und < 1.0mBar ist. -> sensor 2 verwenden
        istWert = pressure[1]
        #print("Sensor LP")
    elif pressure[0] < 1.0 and old_pressure >= pressure[0] and old_pressure >=1.0: #wenn man von > 1.0mBar kommt und > 0.1mBar ist. -> sensor 1 verwenden
        istWert = pressure[0]
        obere_hystere = True
        #print("Sensor HP")
    elif pressure[0] < 1.0 and obere_hystere == True: #wenn man
        istWert = pressure[0]
        #print("Sensor HP")
    if istWert <=0:
        istWert = 1e-4
    return istWert

       

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


# noch unvollständig 
def regelung(ser,task, dt, v_durch, v_ein, Startzeit, Startzeit_neuer_Druck, lokale_zeit, filename):
        
        global old_pressure, csv_buffer, raw_array, resp_array, response_array, counter_limit, Dauer
        
        tangent_counter = 0
        Endzeit = 3600
        
        task.write([v_durch, v_ein])
        
        retry_count = 0 
        pressure = getpressure(ser)
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
                    writer.writerow([f"{lokale_zeit:.3f}".replace('.', ','), "ERROR", 0, 0, "Sensor Timeout", "", "", ""])
            except PermissionError :
                print("Fehler: CSV Datei konnte nicht geöffnet werden. (Datei offen?)")
                pass
            return

        istWert = sensorwahl_mit_hysterese(pressure)
        compare_pressure =  istWert
        Stellgröße, rel_fehler, I_Anteil= PI_regler_step(sollWert, istWert, dt, kp, ki)

        while(lokale_zeit < Endzeit) and (istWert >= 0.001):
            retry_count = 0 
            pressure = getpressure(ser)
            while pressure is None and retry_count < 20:
                retry_count += 1
                time.sleep(0.1)
                pressure = getpressure(ser)
        
            if pressure is None: 
                print("Kritischer Fehler: Antwort vom Sensor auch nach 20 versuchen nicht sauber")
                try: 
                    with open (filename, mode='a', newline='') as f:
                        writer = csv.writer(f, delimiter=';')
                        writer.writerow([f"{lokale_zeit:.3f}".replace('.', ','), "ERROR", 0, 0, "Sensor Timeout", "", "", ""])
                except PermissionError :
                    print("Fehler: CSV Datei konnte nicht geöffnet werden. (Datei offen?)")
                return

            istWert = sensorwahl_mit_hysterese(pressure) 
            
            #Stabilitätscheck
            schwankung = (istWert - old_pressure)/old_pressure
            schwankung_in_relation_zum_vergleich = (istWert - compare_pressure)/compare_pressure

            
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
            elif istWert < 2.5*1e-2:
                fehler_grenze = 0.001
            else: 
                fehler_grenze = 0.0004

            rel_fehler_grenze = 5 * fehler_grenze
            druckeinstelldauer = lokale_zeit - Startzeit_neuer_Druck

            if abs(schwankung) <= fehler_grenze and abs(schwankung_in_relation_zum_vergleich) <= rel_fehler_grenze and tangent_counter <counter_limit:  # Nur wenn die Ableitung signifikant ist
                tangent_counter += 1
                dur_str = ""
            elif (abs(schwankung) > fehler_grenze or abs(schwankung_in_relation_zum_vergleich) > rel_fehler_grenze) and tangent_counter >=0:
                tangent_counter = 0
                compare_pressure = istWert
                dur_str = ""
            elif (tangent_counter == counter_limit):
                Stab_Startzeit = lokale_zeit
                Endzeit = Stab_Startzeit + Dauer
                dur_str = f"{(druckeinstelldauer):.3f}".replace('.', ',')

                
            
            
            
            t_str = f"{lokale_zeit:.3f}".replace('.', ',')
            p_str = f"{istWert:.5f}".replace('.', ',')
            vd_str = f"{v_durch:.2f}".replace('.', ',')
            ve_str = f"{v_ein:.2f}".replace('.', ',')
                
            response_str = str(response_array).replace('.', ',')  if response_array else ''

            csv_buffer.append([t_str, p_str, vd_str, ve_str, dur_str, response_str])

            try: 
                with open (filename, mode='a', newline='') as f:
                    writer = csv.writer(f, delimiter=';')
                    while csv_buffer:
                        writer.writerow(csv_buffer[0])
                        csv_buffer.pop(0)
            except PermissionError :
                print("Fehler: CSV Datei konnte nicht geöffnet werden. (Datei offen?)")
                pass
            
            old_pressure = istWert
            print(f" V_Einlass: {v_ein:.2f} V | V_Durch: {v_durch:.2f} V | Druck: {istWert:.5f} mBar | Dauer der Stufe: {druckeinstelldauer:.3f} s")
            print(f"Tangent Counter: {tangent_counter} | Schwankung: {schwankung:.5f} | rel. Schwankung zu Vergleichswert: {schwankung_in_relation_zum_vergleich:.5f}") 
            print()

            while time.time() - Startzeit - lokale_zeit < dt:
                time.sleep(0.001)
            lokale_zeit = time.time() - Startzeit


def interpolation(ventilspannungen, druck):
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

def druckeingabe ():
    Solldruck = input("Bitte geben Sie den gewünschten Solldruck in mBar ein: ")
    try:
        return float(Solldruck)
    except ValueError:
        print("Ungültige Eingabe. Bitte geben Sie eine Zahl ein.")
        return druckeingabe()

def PI_regler_step(sollWert, istWert):
    global I_Anteil, kp, ki, dt, fehler_historie
    
    fehler = istWert - sollWert
    rel_fehler = fehler /(sollWert) if sollWert != 0 else 0
    if abs(rel_fehler) <0.15: #I-Anteil erst einschalten wenn rel-fehler unter 15% ist
        fehler_historie.append(fehler)

    else:
        fehler_historie.clear()
    I_Anteil = sum(fehler_historie) * dt
    Stellgröße = kp * fehler + ki * I_Anteil
    print(f"Fehler: {fehler:.2f} | Relativer Fehler: {rel_fehler:.4f} | Stellgröße: {Stellgröße:.2f}")
    return (Stellgröße, rel_fehler, I_Anteil)

#muss noch mit def regelung fusionieren
def PI_regler_kopplung(ser,task, sollWert, dt, kp, ki, jetzt, Dauer, tangente,  ):
    rel_fehler = 1
    tangente = 1
    Start_zeit = 10e6
    global old_pressure
    while abs(rel_fehler) > 0.01 or abs(tangente)>0.001 or zeit_jetzt - Start_zeit < Dauer: #relativer Fehler kleiner 1%
        zeit_jetzt = time.time()
        pressure1 = getpressure(ser)
        while (pressure1 is None):
                print("warte auf Druckwerte...")
                pressure1= getpressure(ser)
                time.sleep(0.1)
        
        Stellgröße, rel_fehler, I_Anteil= PI_regler_step(sollWert, istWert, dt, kp, ki)
        
        ventilspannung1 = 10.0/(1+abs(Stellgröße))
        ventilspannung2 = abs(Stellgröße)
        if Stellgröße>=0:
            if ventilspannung1 > 7.5: ventilspannung1 = 7.5               
            task.write([10.0, ventilspannung1])
            Ventilspannung_Durchlass.append(10.0)
            Ventilspannung_Einlass.append(ventilspannung1)
            print(f"Ist {istWert:.2f} | Soll {sollWert:.2f} | U-Durchlassventil: 10.0 V| U-Einlassventil: {ventilspannung1:.2f} V")
        elif Stellgröße < 0:
            if ventilspannung2 > 7.3: ventilspannung2 = 7.3
            task.write([10.0, ventilspannung2])
            Ventilspannung_Durchlass.append(10.0)
            Ventilspannung_Einlass.append(ventilspannung2)
            print(f"Ist {istWert:.2f} | Soll {sollWert:.2f} | U-Durchlassventil:10.0 V| U-Einlassventil: {ventilspannung1:.2f} V ")
        print(f"Kp: {kp:.4f} | I-Anteil: {I_Anteil:.4f}")
        time.sleep(dt)

        Druck.append(istWert)
        zeit.append(zeit_jetzt - jetzt)
        tangente = (old_pressure - istWert) / dt
        #print(f"Tangente: {tangente:.4f} mBar/s")
        old_pressure = istWert
        if abs(rel_fehler) > 0.01 or abs(tangente)>0.001:
            Start_zeit = zeit_jetzt

    print("Ziel erreicht.")


def main():
    global Druck, Ventilspannung_Durchlass, Ventilspannung_Einlass, zeit, StufenDauer, stab_druck
    global v_einlass_steigend, v_einlass_fallend, druck_einlass_steigend, druck_einlass_fallend 
    #global v_durchlass_steigend, v_durchlass_fallend, druck_durchlass_steigend, druck_durchlass_fallend

    #Pfad = input("Geben Sie den Pfad zur CSV-Datei ein: ").strip().replace('"', '')
    Pfad = "C:\\Users\\labor\\Documents\\messung_20260409-184758.csv"
    if not get_arrays_from_csv(Pfad):
        return

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

    V_ein_fallend = interpolation(v_einlass_fallend, druck_einlass_fallend)
    V_ein_steigend = interpolation(v_einlass_steigend, druck_einlass_steigend)

    Solldruck = druckeingabe()


    V_ein = V_ein_fallend(Solldruck * 0.95)
    V_ein = V_ein_steigend(Solldruck * 0.95)


    

    
