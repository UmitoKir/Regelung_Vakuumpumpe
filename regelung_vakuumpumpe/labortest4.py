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
I_Anteil = 0.0
old_pressure = 1000
Druck = []
Ableitung = []
zeit = []
Ventilspannung_Durchlass = []
Ventilspannung_Einlass = []
fehler_historie = deque(maxlen=25)

#Kp wird ermittelt Bisher: 100mBar -> Kp=0.25-0.3, 200mBar -> Kp=0.0
#kp= 0.4 * (1- np.exp(-1+(sollWert/1000))) #hi7er noch unklar wie dies ermittelt werden soll
#kp = 0.3 * np.exp(-(sollWert / 1000))
kp=0.1152
ki=0  # 0.2 #standartmäßig
Dauer = 15 #Dauer in Sekunden, die der Druck im Zielbereich bleiben soll, damit das Programm stoppt. (zusätzlich zum relativen Fehler von 1% und der Ableitung des Drucks von 0.001 mBar/s)

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


def PI_regler_step(sollWert, istWert, dt, kp, ki):
    global I_Anteil
    global fehler_historie
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

def PI_regler_kopplung(ser,task, sollWert, dt, kp, ki, jetzt, Dauer):
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
        
        untere_hystere = False
        obere_hystere = False

        if pressure1[0]>= 1.0: # ab >= 1mBar immer sensor 1 verwenden
            istWert = pressure1[0] 
            untere_hystere == False
            print("Sensor HP")
        elif pressure1[1]< 0.1: #ab <0.1mBar immer sensor 2 verwenden
            istWert = pressure1[1]
            obere_hystere = False
            print("Sensor LP")
        elif pressure1[1] >= 0.1 and old_pressure < pressure1[1] and old_pressure < 0.1: #wenn man von < 0.1mBar kommt und < 1.0mBar ist. -> sensor 2 verwenden
            istWert = pressure1[1]
            untere_hystere = True
            print("Sensor LP")
        elif pressure1[1] >= 0.1 and untere_hystere == True: #wenn man von < 0.1mBar kommt und < 1.0mBar ist. -> sensor 2 verwenden
            istWert = pressure1[1]
            print("Sensor LP")
        elif pressure1[0] < 1.0 and old_pressure >= pressure1[0] and old_pressure >=1.0: #wenn man von > 1.0mBar kommt und > 0.1mBar ist. -> sensor 1 verwenden
            istWert = pressure1[0]
            obere_hystere = True
            print("Sensor HP")
        elif pressure1[0] < 1.0 and obere_hystere == True: #wenn man
            istWert = pressure1[0]
            print("Sensor HP")
        
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

            sollWert = float(input("Welchen Druckwert möchten sie einstellen?"))
            print(f"übernommener Druck: {sollWert} mBar")
            print(type(sollWert))
            jetzt = time.time()
            #istWert = getpressure(ser)[0]

            PI_regler_kopplung(ser, task, sollWert, dt, kp=kp, ki=ki, jetzt=jetzt, Dauer=Dauer)
            print("ao0: 0 , ao1: 5")
            task.write([0, 5])  # Volt
            time.sleep(5)
            print("ao0: 0 , ao1: 7.5")
            task.write([0, 7.5])  # Volt
            time.sleep(5)
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
    """"
    plt.figure(1,figsize=(10, 6))
    plt.plot(zeit, Druck, color='red', linewidth=1.5)
    plt.grid(True, which="both", ls="-", alpha=0.5)
    plt.title(f"Druckverlauf zur Eisntellung {sollWert} mBar (lineare Y-Achse)")
    plt.xlabel("Zeit [s]")
    plt.ylabel("Druck [mbar]")"""

    plt.figure(2, figsize=(10, 6))
    plt.plot(zeit, Druck, color='red', linewidth=1.5)
    plt.yscale('log')
    plt.grid(True, which="both", ls="-", alpha=0.5)
    plt.title(f"Druckverlauf zur Einstellung {sollWert} mBar (logarithmische Y-Achse)")
    plt.xlabel("Zeit [s]")
    plt.ylabel("Druck [mbar]")

    plt.figure(3, figsize=(10, 6))
    plt.plot(zeit[:-1], Ableitung, color='red', linewidth=1.5)
    plt.grid(True, which="both", ls="-", alpha=0.5)
    plt.title(f"Ableitung des Drucks zur Einstellung {sollWert} mBar")
    plt.xlabel("Zeit [s]")
    plt.ylabel("Druckableitung [mbar/s]")
    
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 6))
    ax1.plot(zeit, Ventilspannung_Durchlass, color='blue', linewidth=1.5, label='Durchlassventil')
    ax1.set_title(f"Ventilspannung AO0 zur Einstellung {sollWert} mBar")
    ax1.set_xlabel("Zeit [s]")
    ax1.set_ylabel("Spannung [V]")
    ax1.grid(True, which="both", ls="-", alpha=0.5)

    ax2.plot(zeit, Ventilspannung_Einlass, color='red', linewidth=1.5, label='Einlassventil')
    ax2.set_title(f"Ventilspannung AO1 zur Einstellung {sollWert} mBar")
    ax2.set_xlabel("Zeit [s]")
    ax2.set_ylabel("Spannung [V]")
    ax2.grid(True, which="both", ls="-", alpha=0.5)

    plt.tight_layout()

    plt.show()

main()
