#install the driver software NI-DAQ™mx
#install all the necessary libaries and debugger/compiler(python, python debugger, git etc.) to get it running on VS code
#install with py -m pip install in the terminal all the necessary packages
#matplotlib maybe also required
import time
import numpy as np
import nidaqmx
import serial
import serial.tools.list_ports

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

Druck = []
zeit = []

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
            while (Druck_array[1]>=0.001):
                Druck_array=getpressure(ser)
                if Druck_array[0]>=1.3:
                    Druck.append(Druck_array[0])
                    zeit.append(time.time())
                else: 
                    Druck.append(Druck_array[1])
                    zeit.append(time.time())
                time.sleep(0.1) 
10      print("ao0: 0 , ao1: 2 ")   

            
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
        
main()
