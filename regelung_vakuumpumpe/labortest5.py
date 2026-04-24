#install the driver software NI-DAQ™mx
#install all the necessary libaries and debugger/compiler(python, python debugger, git etc.) to get it running on VS code
#install with py -m pip install in the terminal all the necessary packages
#matplotlib maybe also required

import time
import numpy as np
import nidaqmx
import serial
import serial.tools.list_ports
import matplotlib.pyplot as plt
import csv

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

dt = 1
old_pressure = 1000

raw_array =b""
resp_array = ""
response_array = ""

Dauer = 2400.0
counter_limit = 150


einlassventil_fallend = [10.0, 9, 8, 7.538, 7.411, 7.333, 7.267, 7.204, 7.033, 6.633, 6.122, 6.058, 
                     5.997, 5.940, 5.873, 5.793, 5.711, 5.620, 5.515, 5.358, 5.323, 
                     5.296, 5.268, 5.230, 5.184, 5.149, 5.104, 5.051, 5.003, 5.000, 
                     4.998, 4.995, 4.992, 4.987, 4.980, 4.971, 4.958, 4.942, 4.940, 
                     4.938, 4.936, 4.934, 4.932, 4.930, 4.5, 4, 3, 2, 1, 0]
durchlassventil_fallend = [0, 1, 2, 3, 3.483, 3.738, 3.882, 4.022, 4.161, 4.294, 4.462, 4.664,
                     4.692, 4.723, 4.758, 4.799, 4.845, 4.897, 4.956, 5.018, 5.113, 5.134, 5.159, 5.187,
                     5.219, 5.255, 5.295, 5.341, 5.392, 5.448, 5.454, 5.460, 5.466, 5.472, 5.478, 5.484,
                     5.491, 5.497, 5.657, 5.720, 5.795, 5.882, 5.980, 6.181, 6.597, 7, 8, 9, 10]
durchlassventil_steigend = [10, 9, 8, 7, 6.643, 5.931, 5.706, 5.601, 5.484, 5.432, 5.390, 5.219, 5.165,
                    5.131, 5.124, 5.121, 5.119, 5.117, 5.114, 5.109, 4.978, 4.917,
                    4.871, 4.841, 4.823, 4.809, 4.796, 4.783, 4.772, 4.709, 4.685,
                    4.671, 4.650, 4.611, 4.562, 4.511, 4.467, 4.435, 4.219, 4.088,
                    3.981, 3.890, 3.810, 3.710, 3.532, 3, 2, 1, 0]
einlassventil_steigend = [0, 1, 2, 3, 3.5, 3.899, 4.014, 4.094, 4.151, 4.182, 4.206, 4.226, 4.352, 4.440,
                    4.479, 4.507, 4.529, 4.548, 4.563, 4.576, 4.588, 4.738, 4.880,
                    4.972, 5.038, 5.105, 5.180, 5.242, 5.307, 5.360, 5.549, 5.650,
                    5.733, 5.820, 5.896, 5.969, 6.036, 6.098, 6.158, 6.682, 7.056,
                    7.222, 7.304, 7.366, 7.474, 7.694, 7.5, 7, 8, 9, 10]

test_konfigurationen = [
    ("Einlass", einlassventil_fallend),
    ("Einlass", einlassventil_steigend),
    ("Durchlass", durchlassventil_fallend),
    ("Durchlass", durchlassventil_steigend)
]

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

def Druck_abfahren(ser,task, dt, wahl, ventilspannung, Startzeit, Startzeit_neuer_Druck, lokale_zeit, filename):
        
        global old_pressure, Dauer, csv_buffer, raw_array, resp_array, response_array, counter_limit
        Endzeit = Startzeit_neuer_Druck + Dauer
        tangent_counter = 0
        
        if wahl == "Einlass":
            task.write([10, ventilspannung])
            v_durch, v_ein = 10, ventilspannung
        elif wahl == "Durchlass":
            task.write([ventilspannung, 0])
            v_durch, v_ein = ventilspannung, 0
        
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

        while(tangent_counter < counter_limit) and (lokale_zeit < Endzeit) and (istWert >= 0.0001):
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
            schwankung = (istWert - old_pressure)/old_pressure if old_pressure != 0 else 0
            schwankung_in_relation_zum_vergleich = (istWert - compare_pressure)/compare_pressure if compare_pressure != 0 else 0

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
            else: 
                fehler_grenze = 0.001 

            rel_fehler_grenze = 3 * fehler_grenze

            if abs(schwankung) <= fehler_grenze and abs(schwankung_in_relation_zum_vergleich) <= rel_fehler_grenze and tangent_counter <counter_limit:  # Nur wenn die Ableitung signifikant ist
                tangent_counter += 1
            elif ((abs(schwankung) > fehler_grenze or abs(schwankung_in_relation_zum_vergleich) > rel_fehler_grenze)) and tangent_counter >=0:
                tangent_counter = 0
                compare_pressure = istWert
            
            druckeinstelldauer = lokale_zeit - Startzeit_neuer_Druck
            
            t_str = f"{lokale_zeit:.3f}".replace('.', ',')
            p_str = f"{istWert:.5f}".replace('.', ',')
            vd_str = f"{v_durch:.2f}".replace('.', ',')
            ve_str = f"{v_ein:.2f}".replace('.', ',')
            if tangent_counter >= counter_limit:
                dur_str = f"{(druckeinstelldauer):.3f}".replace('.', ',')  
            elif lokale_zeit > Endzeit - 1.5:
                dur_str = "0"
            else:
                dur_str = ""
            
            raw_str = str(raw_array).replace('.', ',')
            resp_str = str(resp_array).replace('.', ',') if resp_array else ''
            response_str = str(response_array).replace('.', ',')  if response_array else ''

            csv_buffer.append([t_str, p_str, vd_str, ve_str, wahl, dur_str, raw_str, resp_str, response_str])

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
            print(f"Wahl des Ventils: {wahl} | Ventil: {ventilspannung:.2f} V | Druck: {istWert:.5f} mBar | Dauer der Stufe: {druckeinstelldauer:.3f} s | Tangent Counter: {tangent_counter} | Schwankung: {schwankung:.5f} | rel. Schwankung zu Vergleichswert: {schwankung_in_relation_zum_vergleich:.5f}")
            print()

            while time.time() - Startzeit - lokale_zeit < dt:
                time.sleep(0.001)
            lokale_zeit = time.time() - Startzeit


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

       



def main():
    global einlassventil_fallend, durchlassventil_fallend
    global test_konfigurationen
    filename = f"messung_{time.strftime('%Y%m%d-%H%M%S')}.csv"
    with open(filename, mode='w', newline='') as f:
        writer = csv.writer(f, delimiter=';')
        writer.writerow(['Zeit_s', 'Druck_mBar', 'V_Durchlass', 'V_Einlass', 'Modus', 'Dauer bis Druckstabilitaet_s', 'raw', 'resp', 'response'])

    try:
        ser = serial.Serial(port=sp, baudrate=br, timeout=to) #stellt Verbindung mit der Vakuumpumpe her (öffnet Chanel)
        print(f'Verbindung hergestellt mit {sp}')

        system = nidaqmx.system.System.local()
        for dev in system.devices:
            print(dev.name, "-", dev.product_type)
        
        print("neu start:")
        with nidaqmx.Task() as task:
            task.ao_channels.add_ao_voltage_chan(f"Dev1_MSA/ao0") 
            task.ao_channels.add_ao_voltage_chan(f"Dev1_MSA/ao1")
            task.start()
           
            Startzeit = time.time()

            for wahl, spannungs_liste in test_konfigurationen:
                for spannung in spannungs_liste[:]:
                    Startzeit_neuer_Druck = time.time() - Startzeit
                    Druck_abfahren(ser,task, dt, wahl, spannung, Startzeit, Startzeit_neuer_Druck, Startzeit_neuer_Druck, filename)
            task.stop()
        #input("Enter drücken zum Beenden...")
    except KeyboardInterrupt:
        print("Programm unterbrochen.")
    except serial.SerialException as e:
        print(f'Fehler: {e}')
    except UnicodeDecodeError as e:
        print(f'Fehler bei der Dekodierung: {e}')
    finally:
        try:
            if 'task' in locals(): 
                task.write([0.0, 0.0])  # Alle Ausgänge auf 0 setzen
                task.stop()
            if 'ser' in locals() and ser.is_open:
                ser.close()
                print('Verbindung closed. ')
        except Exception:
            pass



main()
