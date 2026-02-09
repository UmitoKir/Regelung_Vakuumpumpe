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

dt = 0.1
I_Anteil = 0.0

def PI_regler_step(sollWert, istWert, dt, kp, ki):
    global I_Anteil 
    fehler = sollWert - istWert
    rel_fehler = fehler / sollWert if sollWert != 0 else 0
    I_Anteil += fehler * dt
    Stellgröße = kp * fehler + ki * I_Anteil
    return (Stellgröße, rel_fehler)

def PI_regler_kopplung(ser,task, sollWert, dt, kp, ki):
    rel_fehler = 1
    tangente = 1
    while abs(rel_fehler) > 0.005 and abs(tangente)>0.001: #relativer Fehler kleiner 1%
        pressure1 = getpressure(ser)
        if not pressure1:
            continue
        istWert = pressure1[0]
        Stellgröße, rel_fehler= PI_regler_step(sollWert, istWert, dt, kp, ki)
        ventilspannung = abs(Stellgröße)
        if Stellgröße<=0:
            if ventilspannung > 10.0: ventilspannung = 10.0
            task.write([ventilspannung, 0.0])
            print(f"Ist {istWert:.2f} | Soll {sollWert:.2f} | Spannung für AO0: {ventilspannung:.2f} V")
        elif Stellgröße > 0:
            if ventilspannung > 6.5: ventilspannung = 6.5
            task.write([0.0, ventilspannung])
            print(f"Ist {istWert:.2f} | Soll {sollWert:.2f} | Spannung für AO1: {ventilspannung:.2f} V")
        time.sleep(dt)
        pressure2 = getpressure(ser)
        if not pressure2:
            continue
        tangente = (pressure2[0] - istWert) / dt

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

            sollWert = float(input("Welchen Druckwert möchten sie einstellen?"))
            print(f"übernommener Druck: {sollWert} mBar")
            print(type(sollWert))
            #istWert = getpressure(ser)[0]
            PI_regler_kopplung(ser, task, sollWert, dt, kp=0.2100, ki=0.0)
        
            print("ao0: 0 , ao1: 2 ")
            task.write([0, 2])  # Volt
            for i in range(20):
                getpressure(ser)
                time.sleep(0.5) 
            print("ao0: 0 , ao1: 7")
            task.write([0, 7])  # Volt
            for i in range(20):
                getpressure(ser)
                time.sleep(0.5)

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

#hallo commit test v2