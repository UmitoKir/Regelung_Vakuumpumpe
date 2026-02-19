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
            print("ao0: 10 , ao1: 0")
            task.write([10, 0]) # mit ctrl+C programm abbrechen diese zeile und nächste auskommetieren und dann programm neu starten.
            time.sleep(1800)  # diesen auch auskommentieren
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
