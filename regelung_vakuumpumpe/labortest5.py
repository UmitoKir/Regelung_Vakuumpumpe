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
from collections import deque

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
Dauer = 300.0

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


def Druck_abfahren(ser,task, dt, ventilspannung, Startzeit, Startzeit_neuer_Druck, lokale_zeit):
        global old_pressure
        global Dauer
        global zeit, Druck, Ventilspannung_Durchlass, Ventilspannung_Einlass
        Endzeit = Startzeit_neuer_Druck + Dauer
        
        untere_hystere = False
        obere_hystere = False
        
        task.write([ventilspannung, 0])
        
        while(lokale_zeit < Endzeit):
            pressure = getpressure(ser)
            while (pressure is None):
                    print("warte auf Druckwerte...")
                    pressure = getpressure(ser)
                    time.sleep(0.01)
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

        
            Ventilspannung_Durchlass.append(10.0)
            Ventilspannung_Einlass.append(ventilspannung)
            Druck.append(istWert)
            zeit.append(lokale_zeit)
            old_pressure = istWert
            print(f"Druck: {istWert:.2f} mBar | Einlassventil: {ventilspannung:.2f} V ")
            
            while time.time()-Startzeit-lokale_zeit < dt:
                time.sleep(0.005)
            lokale_zeit = time.time() - Startzeit


       
       



def main():
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

            task.write([0, 7.25])
            time.sleep(5)
            task.write([0, 10])

            ventilspannungen1 = [7.5, 7, 6.5, 6, 5.5, 5, 4.5, 4, 3.5, 3, 2.5, 2, 1.5, 1, 0.5, 0]
            ventilspannungen2 = [0, 0.5, 1, 1.5, 2, 2.5, 3, 3.5, 4, 4.5, 5, 5.5, 6, 6.5, 7, 7.5]
            Startzeit = time.time()
            
            for i in ventilspannungen2:
                Startzeit_neuer_Druck = time.time() - Startzeit
                aktuelle_zeit = time.time() - Startzeit
                Druck_abfahren(ser,task, dt, i, Startzeit, Startzeit_neuer_Druck, aktuelle_zeit)

            
            print("ao0: 0 , ao1: 5")
            task.write([0, 5])  # Volt
            time.sleep(20)
            print("ao0: 0 , ao1: 7.5")
            task.write([0, 7.5])  # Volt
            time.sleep(10)
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
            task.write([0.0, 0.0])  # Alle Ausgänge auf 0 setzen
            if 'ser' in locals() and ser.is_open:
                ser.close()
                print('Verbindung closed. ')
        except Exception as e:
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
