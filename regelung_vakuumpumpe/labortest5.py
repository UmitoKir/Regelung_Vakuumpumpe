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

dt = 0.1
old_pressure = 1000
Druck = []
Ableitung = []
zeit = []
Ventilspannung_Durchlass = []
Ventilspannung_Einlass = []
Dauer = 1800.0

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

def getpressure(ser): #"Druckauslesebefehl"
    response = ser.readline().decode('utf-8').strip() #liest die Werte vom CenterThree
    if response:
        #print(f'Antwort: {response}')
        values = response.split(",")
        values = [float(values[i]) for i in (1,3)]
        #print(f"Druckwerte: {values}")
        return values
    else:
        print('keine Antwort. ')
        return None


def Druck_abfahren(ser,task, dt, wahl, ventilspannung, Startzeit, Startzeit_neuer_Druck, lokale_zeit, filename):
        global old_pressure
        global Dauer
        global zeit, Druck, Ventilspannung_Durchlass, Ventilspannung_Einlass
        Endzeit = Startzeit_neuer_Druck + Dauer
        tangent_counter = 0
        compare_pressure = 0.0
        global csv_buffer
        
        if wahl == "Einlass":
            task.write([10, ventilspannung])
            v_durch, v_ein = 10, ventilspannung
        elif wahl == "Durchlass":
            task.write([ventilspannung, 0])
            v_durch, v_ein = ventilspannung, 0

        while(tangent_counter < 100) and (lokale_zeit < Endzeit):
            pressure = getpressure(ser)
            while (pressure is None):
                    print("warte auf Druckwerte...")
                    time.sleep(0.01)
                    pressure = getpressure(ser)

            istWert = sensorwahl_mit_hysterese(pressure)   
            Ventilspannung_Durchlass.append(v_durch)
            Ventilspannung_Einlass.append(v_ein)
            Druck.append(istWert)
            zeit.append(lokale_zeit)

           
            
            schwankung = (istWert - old_pressure)/old_pressure
            schwankung_in_relation_zum_vergleich = (istWert - compare_pressure)/compare_pressure if compare_pressure != 0 else 1
            
            if abs(schwankung) < 0.001 and abs(schwankung_in_relation_zum_vergleich) < 0.005 and tangent_counter <100:  # Nur wenn die Ableitung signifikant ist
                tangent_counter += 1
            elif (abs(schwankung) > 0.001 or abs(schwankung_in_relation_zum_vergleich) > 0.005) and tangent_counter >0:
                tangent_counter = 0
                compare_pressure = istWert
            
            druckeinstelldauer = lokale_zeit - Startzeit_neuer_Druck

            if tangent_counter >= 100:
                aktuelle_zeile =[f"{lokale_zeit: .3f}", f"{istWert: .5f}", f"{v_durch: .2f}", f"{v_ein: .2f}", wahl, f"{druckeinstelldauer: .3f}"]
            else :
                aktuelle_zeile =[f"{lokale_zeit: .3f}", f"{istWert: .5f}", f"{v_durch: .2f}", f"{v_ein: .2f}", wahl, ""]
            
            csv_buffer.append(aktuelle_zeile)

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
            print(f"Wahl des Ventils: {wahl} | Ventil: {ventilspannung:.2f} V | Druck: {istWert:.5f} mBar | Dauer der Stufe: {druckeinstelldauer:.3f} s | Tangent Counter: {tangent_counter}")
            
            while time.time()-Startzeit-lokale_zeit < dt:
                time.sleep(0.005)
            lokale_zeit = time.time() - Startzeit


def sensorwahl_mit_hysterese(pressure):
    global untere_hystere, obere_hystere, old_pressure

    istWert = old_pressure

    if pressure[0]>= 1.0: # ab >= 1mBar immer sensor 1 verwenden
        istWert = pressure[0] 
        untere_hystere = False
        print("Sensor HP")
    elif pressure[1]< 0.1: #ab <0.1mBar immer sensor 2 verwenden
        istWert = pressure[1]
        obere_hystere = False
        print("Sensor LP")
    elif pressure[1] >= 0.1 and old_pressure < pressure[1] and old_pressure < 0.1: #wenn man von < 0.1mBar kommt und < 1.0mBar ist. -> sensor 2 verwenden
        istWert = pressure[1]
        untere_hystere = True
        print("Sensor LP")
    elif pressure[1] >= 0.1 and untere_hystere == True: #wenn man von < 0.1mBar kommt und < 1.0mBar ist. -> sensor 2 verwenden
        istWert = pressure[1]
        print("Sensor LP")
    elif pressure[0] < 1.0 and old_pressure >= pressure[0] and old_pressure >=1.0: #wenn man von > 1.0mBar kommt und > 0.1mBar ist. -> sensor 1 verwenden
        istWert = pressure[0]
        obere_hystere = True
        print("Sensor HP")
    elif pressure[0] < 1.0 and obere_hystere == True: #wenn man
        istWert = pressure[0]
        print("Sensor HP")
    if istWert < 0:
        istWert = old_pressure
    return istWert

       



def main():
    global ventilspannungen1, ventilspannungen2
    global test_konfigurationen
    filename = f"messung_{time.strftime('%Y%m%d-%H%M%S')}.csv"
    with open(filename, mode='w', newline='') as f:
        writer = csv.writer(f, delimiter=';')
        writer.writerow(['Zeit_s', 'Druck_mBar', 'V_Durchlass', 'V_Einlass', 'Modus', 'Dauer bis Druckstabilität_s'])

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

            #task.write([0, 7.25])
            #time.sleep(5)
            #task.write([0, 10])
           
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
        
    for i in range(len(Druck)-1):
        tangente = (Druck[i+1] - Druck[i]) / (zeit[i+1] - zeit[i])
        Ableitung.append(tangente)
    
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

    plt.tight_layout()

    plt.show()

main()
