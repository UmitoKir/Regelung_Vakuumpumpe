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

Druck = []
Ableitung = []
zeit = []

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
            task.write([10, 0])  # Volt
            Druck_array = getpressure(ser)
            jetzt = time.time()
            #kleiner sicherheitscheck damit in der nächsten Scheife kein Error auftritt
            while (Druck_array is None):
                print("warte auf Druckwerte...")
                Druck_array= getpressure(ser)
                time.sleep(0.5)

            #loggen der Druckwerte bis es 1 uBar erreicht
            while (Druck_array[0]>=1 or Druck_array[1]>=0.001): #solange der Druck größer als 1 mbar ist, werden die Werte ausgelesen und in die Liste Druck und zeit gespeichert
                Druck_array=getpressure(ser)
                if Druck_array[0]>=1.3:
                    Druck.append(Druck_array[0])
                    zeit.append(time.time()-jetzt)
                else: 
                    Druck.append(Druck_array[1])
                    zeit.append(time.time()-jetzt)
                print(f"Zeit: {zeit[-1]}, Druck: {Druck[-1]}")
                time.sleep(0.1) 
            print("ao0: 0 , ao1: 1.5")
            task.write([0, 1.5])
            time.sleep(5)
            print("ao0: 0 , ao1: 4")
            task.write([0, 4.0])
            time.sleep(5)
            print("ao0: 0 , ao1: 7")
            task.write([0, 7.0])
            time.sleep(5)
            task.stop()
        input("Enter drücken zum Beenden...")
    except KeyboardInterrupt:
        print("Programm unterbrochen.")
    except serial.SerialException as e:
        print(f'Fehler mit der seriellen Verbindung: {e}')
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
    plt.title("Druckverlauf lineare Y-Achse")
    plt.xlabel("Zeit [s]")
    plt.ylabel("Druck [mbar]")

    plt.figure(2, figsize=(10, 6))
    plt.plot(zeit, Druck, color='red', linewidth=1.5)
    plt.yscale('log')
    plt.grid(True, which="both", ls="-", alpha=0.5)
    plt.title("Druckverlauf logarithmische Y-Achse")
    plt.xlabel("Zeit [s]")
    plt.ylabel("Druck [mbar]")

    plt.figure(3, figsize=(10, 6))
    plt.plot(zeit[:-1], Ableitung, color='red', linewidth=1.5)
    plt.grid(True, which="both", ls="-", alpha=0.5)
    plt.title("Ableitung des Drucks")
    plt.xlabel("Zeit [s]")
    plt.ylabel("Druckableitung [mbar/s]")
    plt.show() 
 
main()
