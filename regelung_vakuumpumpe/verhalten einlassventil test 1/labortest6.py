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

kp=0.001 #0.1152
ki= 0.0005 #0.0002 #0.2 standartmäßig
dt = 1
old_pressure = 1000

counter_limit = 100
Dauer = 300
Max_dauer = 1500

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
lut_v_einlass_steigend = []
lut_v_einlass_fallend = []
lut_v_durchlass_steigend = []
lut_v_durchlass_fallend = []
druck_einlass_steigend = []
druck_einlass_fallend = []
druck_durchlass_steigend = []
druck_durchlass_fallend = []
fehler_historie = []

untere_hystere = False
obere_hystere = False
history_hp = []

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
    global untere_hystere, obere_hystere, old_pressure, history_hp
    
    istWert = old_pressure
    # hp_smooth = old_pressure
    # if pressure[0] > 0.1:
    #     history_hp.append(pressure[0])
    #     if len(history_hp) > 5:
    #         history_hp.pop(0)
    #     hp_smooth = sum(history_hp) / len(history_hp)

    if pressure[0]>= 1.0: # ab >= 1mBar immer sensor 1 verwenden
        istWert = pressure[0] #round(pressure[0], 2) #round(hp_smooth, 2)
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
        istWert = pressure[0] #round(pressure[0], 2) #round(hp_smooth, 2)
        obere_hystere = True
        #print("Sensor HP")
    elif pressure[0] < 1.0 and obere_hystere == True: #wenn man
        istWert = pressure[0] #round(pressure[0], 2) #round(hp_smooth, 2)
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


# noch unvollständig 
def regelung(ser,task, dt, Startzeit, filename, Solldruck):
        
        global old_pressure, csv_buffer, raw_array, resp_array, response_array, counter_limit, Dauer, Max_dauer

        tangent_counter = 0
        Endzeit = 3600
        lokale_zeit = 0
        
        pressure = getpressure(ser)
        result = pressure_error_handler(ser, pressure, filename, Startzeit)
        if result == False:
            return
        else: 
            pressure = result
        
        istWert = sensorwahl_mit_hysterese(pressure)
        compare_pressure =  istWert

        V_ein_fallend = interpolation(lut_v_einlass_fallend, druck_einlass_fallend)
        #V_ein_steigend = interpolation(lut_v_einlass_steigend, druck_einlass_steigend)
        V_durch_fallend = interpolation(lut_v_durchlass_fallend, druck_durchlass_fallend)
        #V_durch_steigend = interpolation(lut_v_durchlass_steigend, druck_durchlass_steigend)
        if V_ein_fallend is None or V_durch_fallend is None:
            print("Fehler: Interpolation fehlgeschlagen, LUT leer?")
            return
        V_ein = V_ein_fallend(Solldruck * 0.97)
        V_ein_genau = V_ein_fallend(Solldruck)
        #V_ein = V_ein_steigend(Solldruck * 0.97)
        V_durch = V_durch_fallend(Solldruck)
        print(f"Anfangs Stellgröße: {V_ein:.2f} V")
        task.write([10.0, V_ein])
        
        relativer_fehler = abs(Solldruck - istWert) / Solldruck
        while (relativer_fehler >=0.075 and lokale_zeit < Max_dauer):
            print(f"relativer Fehler:{relativer_fehler: .3} | Solldruck:{Solldruck:.2} | Istdruck: {istWert:.2} | V_Einlass: {V_ein:.2f} V")
            pressure = getpressure(ser)
            result = pressure_error_handler(ser, pressure, filename, Startzeit)
            if result == False:
                return
            else: 
                pressure = result
            old_pressure = istWert
            istWert = sensorwahl_mit_hysterese(pressure)
            relativer_fehler = abs(Solldruck - istWert) / Solldruck

            dur_str = ""
            t_str = f"{lokale_zeit:.3f}".replace('.', ',')
            p_str = f"{istWert:.5f}".replace('.', ',')
            vd_str = "10,0"
            ve_str = f"{V_ein:.2f}".replace('.', ',')
            
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
            while time.time() - Startzeit - lokale_zeit < dt:
                time.sleep(0.01)
            lokale_zeit = time.time() - Startzeit
        
        #eine funktion shreiben, die abhängig vom Fehler zwischen ist und sollwert den durchlassventil einstellt. 
        #je kleiner der fehler desto langsamer soll es reagieren aber ventil darf nicht zu weit zu gehen, 
        #weil ansonsonsten kann es den solldruck nicht halten. 
        Stellgröße, rel_fehler, I_Anteil= PI_regler_step(Solldruck, istWert)
        compare_pressure = istWert
        while ((tangent_counter < counter_limit and lokale_zeit < Max_dauer) or lokale_zeit < Endzeit) and istWert >= 0.001: #relativer Fehler kleiner 1%            
            pressure = getpressure(ser)
            result = pressure_error_handler(ser, pressure, filename, Startzeit)
            if result == False:
                return
            else: 
                pressure = result
            old_pressure = istWert
            istWert = sensorwahl_mit_hysterese(pressure)
            Stellgröße, rel_fehler, I_Anteil= PI_regler_step(Solldruck, istWert)
            
            v_ein = np.clip(V_ein_genau + (Stellgröße), 0, 10)
            v_durch = np.clip((1 + rel_fehler) * V_durch, 0, 10)

            task.write([v_durch, v_ein])

            #Stabilitätscheck
            schwankung = (istWert - old_pressure)/old_pressure
            schwankung_in_relation_zum_vergleich = (istWert - compare_pressure)/compare_pressure
            
            fehler_grenze = max_fehler_bestimmung(istWert)
            rel_fehler_grenze = 5 * fehler_grenze

            if abs(schwankung) <= fehler_grenze and abs(schwankung_in_relation_zum_vergleich) <= rel_fehler_grenze:  # Nur wenn die Ableitung signifikant ist
                if (tangent_counter == counter_limit) or lokale_zeit > Max_dauer - 1.5:
                    Stab_Startzeit = lokale_zeit
                    Endzeit = Stab_Startzeit + Dauer
                    dur_str = f"{(lokale_zeit):.3f}".replace('.', ',')
                elif tangent_counter > counter_limit and lokale_zeit > Endzeit -1.5:
                    dur_str = "300,0"
                else:
                    dur_str = ""
                tangent_counter += 1
            elif (abs(schwankung) > fehler_grenze or abs(schwankung_in_relation_zum_vergleich) > rel_fehler_grenze):
                tangent_counter = 0
                compare_pressure = istWert
                dur_str = ""
            
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
            print(f"relativer Fehler:{rel_fehler: .3} | Druck: {istWert:.5f} mBar | I-Anteil: {I_Anteil:.4f} | Stellgröße: {Stellgröße: .4f}")
            print(f" V_Einlass: {v_ein:.2f} V | V_Durch: {v_durch:.2f} V | Dauer der Stufe: {lokale_zeit:.3f} s")
            print(f"Tangent Counter: {tangent_counter} | Schwankung: {schwankung:.5f} | rel. Schwankung zu Vergleichswert: {schwankung_in_relation_zum_vergleich:.5f}") 
            print()

            while time.time() - Startzeit - lokale_zeit < dt:
                time.sleep(0.01)
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
    global kp, ki, dt, fehler_historie
    
    fehler = sollWert - istWert
    rel_fehler = fehler /(sollWert) if sollWert != 0 else 0
    if abs(rel_fehler) <0.05: #I-Anteil erst einschalten wenn rel-fehler unter 5% ist
        fehler_historie.append(fehler)

    else:
        fehler_historie.clear()
    I_Anteil = sum(fehler_historie) * dt
    Stellgröße = kp * fehler + ki * I_Anteil
    print(f"Fehler: {fehler:.2f} | Relativer Fehler: {rel_fehler:.4f} | Stellgröße: {Stellgröße:.2f}")
    return (Stellgröße, rel_fehler, I_Anteil)


def main():
    global Druck, Ventilspannung_Durchlass, Ventilspannung_Einlass, zeit, StufenDauer, stab_druck
    global lut_v_einlass_steigend, lut_v_einlass_fallend, druck_einlass_steigend, druck_einlass_fallend 
    global lut_v_durchlass_steigend, lut_v_durchlass_fallend, druck_durchlass_steigend, druck_durchlass_fallend

    #Pfad = input("Geben Sie den Pfad zur CSV-Datei ein: ").strip().replace('"', '')
    Pfad = "C:\\Users\\labor\\Documents\\messung_ein_durcchlassventil_mehr_stützpunkte.csv"
    if not get_arrays_from_csv(Pfad):
        return
    
    filename = f"messung_{time.strftime('%Y%m%d-%H%M%S')}.csv"
    with open(filename, mode='w', newline='') as f:
        writer = csv.writer(f, delimiter=';')
        writer.writerow(['Zeit_s', 'Druck_mBar', 'V_Durchlass', 'V_Einlass', 'Dauer bis Druckstabilitaet_s', 'response'])

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
                lut_v_einlass_steigend.append(v_aktuell)
                druck_einlass_steigend.append(stab_druck[i])
            elif v_aktuell < v_vorher:
                lut_v_einlass_fallend.append(v_aktuell)
                druck_einlass_fallend.append(stab_druck[i])

        if stab_ventilspannung_einlass[i] == 0:
            if v_aktuell > v_vorher:
                lut_v_durchlass_steigend.append(stab_ventilspannung_durchlass[i])
                druck_durchlass_steigend.append(stab_druck[i])
            elif v_aktuell < v_vorher:
                lut_v_durchlass_fallend.append(stab_ventilspannung_durchlass[i])
                druck_durchlass_fallend.append(stab_druck[i])
            
    task_completed = False
    try:
        ser = serial.Serial(port=sp, baudrate=br, timeout=to) #stellt Verbindung mit der Vakuumpumpe her (öffnet Chanel)
        print(f'Verbindung hergestellt mit {sp}')

        system = nidaqmx.system.System.local()
        for dev in system.devices:
            print(dev.name, "-", dev.product_type)
        with nidaqmx.Task() as task:
                task.ao_channels.add_ao_voltage_chan(f"Dev1_MSA/ao0") 
                task.ao_channels.add_ao_voltage_chan(f"Dev1_MSA/ao1")
                task.start()

                Solldruck = druckeingabe()
                
                regelung(ser, task, dt, Startzeit=time.time(), filename=filename, Solldruck=Solldruck)
                
                
                task.write([0.0, 0.0])  # Alle Ausgänge auf 0 setzen
                task_completed = True
                print('Erfolgreich abgeschlossen. Verbindung wird beendet')
                task.stop()
    except KeyboardInterrupt:
        print("Programm unterbrochen.")
    except serial.SerialException as e:
        print(f'Fehler: {e}')
    except UnicodeDecodeError as e:
        print(f'Fehler bei der Dekodierung: {e}')
    finally:
        if not task_completed:
            try: 
                with nidaqmx.Task() as task:
                    task.ao_channels.add_ao_voltage_chan(f"Dev1_MSA/ao0") 
                    task.ao_channels.add_ao_voltage_chan(f"Dev1_MSA/ao1")
                    task.start()
                    task.write([0.0, 0.0])  # Alle Ausgänge auf 0 setzen
                    if 'ser' in locals() and ser.is_open:
                        ser.close()
                        print('Verbindung closed. ')
                    task.stop()
            except Exception as e:
                pass
        else: 
            try:
                if 'ser' in locals() and ser.is_open:
                    ser.close()
                    print('Verbindung closed. ')
            except Exception as e:
                pass
main()
