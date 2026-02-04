#alle wichtigen libarys erstmal ein binden.
import serial
import time
import serial.tools.list_ports
import numpy as np

#der folgende Absatz sucht den usb port aus an dem sie die Vakuumpumpe aneschlossen haben
ports = list(serial.tools.list_ports.comports()) #ruft eine Liste mit allen existierenden Anschlüssen an Ihrem Computer ab
sp=None
#durch Vergleichen der Namen von allen Anschlüssen mit dem Namen vom Adapter RS232 zu usb wählt es den richtigen Port aus.
for p in ports:
    print(p)
    if 'ATEN'in p.description:
        print(f'this is the Device: {p.device}')
        sp=p.device
    if sp is None:
        print('Das Gerät wurde nicht gefunden.')

br = 38400
to = 1
def getpressure(): #"Druckauslesebefehl" als Symbolkette erstellen
    befehl=('GP')
    return befehl

def setpressure(): #"Druckeinstellungsbefehl" als Symbolkette erstellen
    druck=input('Druck in mbar: ')
    befehl = (f'SP{druck}')
    return befehl

def main(befehl):
    try:
        ser = serial.Serial(port=sp, baudrate=br, timeout=to) #stellt Verbindung mit der Vakuumpumpe her (öffnet Chanel)
        print(f'Verbindung herestellt mit {sp}')
        command=f'{befehl}\r'
        for char in command: #wandelt die Befehlsymbolkette einzeln in ASCII code um und schick diese mit 0.2Sekunden Abstand zum Gerät ab
            ser.write(char.encode('utf-8'))
            print(f'Command gesendet: {char.strip()}')
            time.sleep(0.2)
        time.sleep(0.3) #wartet insgesamt 0.5Sekunden ab bevor Empfangen der Antwort
        response = ser.readline().decode('utf-8').strip() #liest die Antwort von der Vakuumpumpe
# nur für Überprüfung ob Rsponse gleich ACK(6) ist      print(f'Response: {ord(response)}')
        if response:
            print(f'Antwort: {response}')
        else:
            print('keine Antwort. ')
    except serial.SerialException as e:
        print(f'Fehler: {e}')
    except UnicodeDecodeError as e:
        print(f'Fehler bei der Dekodierung: {e}')
    finally:
        if 'ser' in locals() and ser.is_open:
            ser.close()
            print('Verbindung closed. ')

def choice():
    wahl=input('(1) Druckabfrage, (2) Druckeinstellung oder (3) Druckabfahren? ')
    if wahl=='1':
        main(getpressure())
    elif wahl=='2':
        main(setpressure())
    elif wahl=='3':
        stufen()
    else:
        print('Die Eingabe ist ungültig. ')
        choice()

def end():
    beenden=input('Möchten Sie das Programm beenden drücken Sie bitte die 0.\n Möchten Sie noch ein Befehl eingeben drücken Sie die 1. \n ')
    w2=int(beenden)
    if w2==1:
        choice()
        end()
    elif w2==0:
        input('Drücke irgendeine Taste um Programm zu schließen. ')

def stufen():
    try:
        ser = serial.Serial(port=sp, baudrate=br, timeout=to)
        print(f'Verbindung hergestellt mit {sp}')
#        SW = float(input('Startwert[mBar]: '))
#        EW = float(input('Endwert[mBar]: '))
#        schritte = int(input('Anzahl der Abtastungspunkte: '))
#        druckhalten = float(input('Anzahl Sekunden, bei dem der Druck gehalten werden soll: '))  # zeit in sekunden, bei der druck gehalten werden soll
#        points = np.linspace(SW, EW, schritte)
        try:
            excelfile = input(r'bitte gebe den Pfad ein: ')
            df = pd.read_excel(excelfile)
            druckhalten=df.at[0, 'Zeitsabstand[s]: ']
            points = list(df['Druck[mBar]:'])
            print(points)
        except FileNotFoundError:
            print("Die Datei 'book2.xlsx' wurde nicht gefunden.")
        except Exception as e:
            print(f"Ein Fehler ist aufgetreten: {e}")


        for counter in points:
            command = f'SP{counter}\r'
            for char in command:
                ser.write(char.encode('utf-8'))
                print(f'Command gesendet: {char.strip()}')
                time.sleep(0.2)
            time.sleep(0.5)
            response = ord(ser.readline().decode('utf-8').strip())
            if response:
                print(f'ACK=6 or NAK=21 : {response}')
                antwort = druckabfrage(ser, counter)
                print(f'typ von druckaktuell: {type(antwort)}')
                print(f'Antwort Druck: {antwort}')
            else:
                print('keine Antwort. ')
            time.sleep(druckhalten)


    except serial.SerialException as e:
        print(f'Fehler: {repr(e)}')
    except UnicodeDecodeError as e:
        print(f'Fehler bei der Dekodierung: {repr(e)}')
    finally:
        if 'ser' in locals() and ser.is_open:
            ser.close()
            print('Verbindung closed. ')

def druckabfrage(ser, counter):
    gp = 'GP\r'
    ser.write(gp.encode('utf-8'))
    time.sleep(0.3)
    response1 = ser.readline().decode('utf-8').strip()
    print(f'Antwort 1: {response1}')
    ser.write(gp.encode('utf-8'))
    time.sleep(0.3)
    response2 = ser.readline().decode('utf-8').strip()
    print(f'Antwort 2: {response2}')
    druckdavor=float(response1)
    druckaktuell=float(response2)
    steigung=abs(druckdavor-druckaktuell)/druckdavor
    relerror=abs(druckaktuell-counter)/counter
    if relerror<0.01 and steigung<0.05:
        return druckaktuell
    else:
        print("Bedingungen nicht erfüllt, erneuter Versuch...")
        return druckabfrage(ser, counter)


choice()
end()