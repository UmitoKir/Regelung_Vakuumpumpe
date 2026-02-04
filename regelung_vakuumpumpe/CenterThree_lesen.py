#install the driver software NI-DAQ™mx
#install all the necessary libaries and debugger/compiler(python, python debugger, git etc.) to get it running on VS code
#install with py -m pip install nidaqmx in the terminal all the necessary packages
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
    # nur für Überprüfung ob Response gleich ACK(6) ist      print(f'Response: {ord(response)}')
    if response:
        print(f'Antwort: {response}')
    else:
        print('keine Antwort. ')

def main():
    try:
        ser = serial.Serial(port=sp, baudrate=br, timeout=to) #stellt Verbindung mit der Vakuumpumpe her (öffnet Chanel)
        print(f'Verbindung herestellt mit {sp}')
        getpressure(ser)
        time.sleep(1)
        getpressure(ser)
        time.sleep(1)
        getpressure(ser)
        time.sleep(1)
        getpressure(ser)
        
        # system = nidaqmx.system.System.local()
        # for dev in system.devices:
        #     print(dev.name, "-", dev.product_type)
        # print("neu start:")
        # with nidaqmx.Task() as task:
        #     task.ao_channels.add_ao_voltage_chan(f"{"Dev1_MSA"}/ao0") #a00
        #     task.ao_channels.add_ao_voltage_chan(f"{"Dev1_MSA"}/ao1")
            
        #     print("ao0: 3 , ao1: 3 ")
        #     task.write([3, 3])  # Volt
        #     time.sleep(30)
        #     print("ao0: 0, ao1: 0")
        #     task.write([0, 0])  # Volt
        #     time.sleep(30)
        #     print("ao0: 10, ao1: 0")
        #     task.write([10, 0])  # Volt
        #     time.sleep(30)
        #     print("ao0: 0, ao1: 10")
        #     task.write([0, 10])  # Volt
        #     time.sleep(30)
        #     print("ao0: 0, ao1: 0")
        #     task.write([0, 0])  # Volt
        #     time.sleep(30)

        input("Enter drücken zum Beenden...")
    except serial.SerialException as e:
        print(f'Fehler: {e}')
    except UnicodeDecodeError as e:
        print(f'Fehler bei der Dekodierung: {e}')
    finally:
        if 'ser' in locals() and ser.is_open:
            ser.close()
            print('Verbindung closed. ')

main()
