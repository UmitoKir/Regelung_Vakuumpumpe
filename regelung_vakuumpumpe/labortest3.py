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

dt = 0.1
I_Anteil = 0.0
old_pressure = 1000
Druck = []
Ableitung = []
zeit = []
VentilspannungAO0 = []
VentilspannungAO1 = []

def PI_regler_step(sollWert, istWert, dt, kp, ki):
    global I_Anteil 
    fehler = sollWert - istWert
    rel_fehler = fehler / sollWert if sollWert != 0 else 0
    I_Anteil += rel_fehler * dt
    #Anti-Windup: Begrenzung des I-Anteils
    I_Anteil = max(-50, min(50, I_Anteil))
    Stellgröße = kp * rel_fehler + ki * I_Anteil
    print(f"Fehler: {fehler:.2f} | Relativer Fehler: {rel_fehler:.4f} | Stellgröße: {Stellgröße:.2f}")
    return (Stellgröße, rel_fehler)

def PI_regler_kopplung(ser,task, sollWert, dt, kp, ki, old_pressure):
    rel_fehler = 1
    tangente = 1
    while abs(rel_fehler) > 0.01 or abs(tangente)>0.001: #relativer Fehler kleiner 1%
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
        
        Stellgröße, rel_fehler= PI_regler_step(sollWert, istWert, dt, kp, ki)
        ventilspannung = abs(Stellgröße)
        if Stellgröße<=0:
            if ventilspannung > 10.0: ventilspannung = 10.0
            task.write([ventilspannung, 0.0])
            VentilspannungAO0.append(ventilspannung)
            VentilspannungAO1.append(0.0)
            print(f"Ist {istWert:.2f} | Soll {sollWert:.2f} | Spannung für AO0: {ventilspannung:.2f} V")
        elif Stellgröße > 0:
            if ventilspannung > 7.0: ventilspannung = 7.0
            task.write([0.0, ventilspannung])
            VentilspannungAO0.append(0.0)
            VentilspannungAO1.append(ventilspannung)
            print(f"Ist {istWert:.2f} | Soll {sollWert:.2f} | Spannung für AO1: {ventilspannung:.2f} V")
        time.sleep(dt)

        Druck.append(istWert)
        zeit.append(time.time())
        #tangente = ( - istWert) / dt
        #print(f"Tangente: {tangente:.4f} mBar/s")
        #old_pressure = istWert
        i += 1
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
            sollWert = float(input("Welchen Druckwert möchten sie einstellen?"))
            print(f"übernommener Druck: {sollWert} mBar")
            print(type(sollWert))
            #istWert = getpressure(ser)[0]
            PI_regler_kopplung(ser, task, sollWert, dt, kp=0.22, ki=0.00625, old_pressure=old_pressure)
            print("ao0: 0 , ao1: 2 ")
            task.write([0, 2])  # Volt
            for i in range(20):
                getpressure(ser)
                time.sleep(0.1) 
            print("ao0: 0 , ao1: 7")
            task.write([0, 7])  # Volt
            for i in range(20):
                getpressure(ser)
                time.sleep(0.5)
            task.stop()
        input("Enter drücken zum Beenden...")
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
    plt.title(f"Druckverlauf zur Eisntellung {sollWert} mBar (lineare Y-Achse)")
    plt.xlabel("Zeit [s]")
    plt.ylabel("Druck [mbar]")

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
    ax1.plot(zeit, VentilspannungAO0, color='blue', linewidth=1.5, label='AO0')
    ax1.set_title(f"Ventilspannung AO0 zur Einstellung {sollWert} mBar")
    ax1.set_xlabel("Zeit [s]")
    ax1.set_ylabel("Spannung [V]")
    ax1.grid(True, which="both", ls="-", alpha=0.5)

    ax2.plot(zeit, VentilspannungAO1, color='red', linewidth=1.5, label='AO1')
    ax2.set_title(f"Ventilspannung AO1 zur Einstellung {sollWert} mBar")
    ax2.set_xlabel("Zeit [s]")
    ax2.set_ylabel("Spannung [V]")
    ax2.grid(True, which="both", ls="-", alpha=0.5)

    plt.tight_layout()

    plt.show()

main()
