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
    if response:
        print(f'Antwort: {response}')
        values = response.split(",")
        values = [float(v) for v in values]
        print(f"Druckwerte: {values}")
        return values
    else:
        print('keine Antwort. ')

def main():
    try:
        ser = serial.Serial(port=sp, baudrate=br, timeout=to) #stellt Verbindung mit der Vakuumpumpe her (öffnet Chanel)
        print(f'Verbindung hergestellt mit {sp}')
        getpressure(ser)
        time.sleep(1)
        getpressure(ser)
        time.sleep(1)
        getpressure(ser)
        time.sleep(1)
        getpressure(ser)

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

#hallo commit test v2