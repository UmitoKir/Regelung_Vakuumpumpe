#install the driver software NI-DAQ™mx
#install all the necessary libaries and debugger/compiler(python, python debugger, git etc.) to get it running on VS code
#install with py -m pip install in the terminal all the necessary packages
#matplotlib maybe also required
import time
import numpy as np
import nidaqmx
import serial
import serial.tools.list_ports
import csv
import pandas as pd 
from scipy.interpolate import PchipInterpolator
import matplotlib.pyplot as plt
#from function_lib import interpolation, druckeingabe, steigung, max_fehler_bestimmung, pressure_error_handler, sensorwahl_mit_hysterese, getpressure

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

dt = 1
old_pressure = 1000
Druck = []
zeit = []
Ventilspannung_Durchlass = []
Ventilspannung_Einlass = []
StufenDauer = []
stab_druck = []
stab_ventilspannung_einlass = []
stab_ventilspannung_durchlass = []
lut_v_einlass_steigend = []
lut_v_einlass_fallend = []
lut_v_durchlass_steigend = []
lut_v_durchlass_fallend = []
druck_einlass_steigend = []
druck_einlass_fallend = []
druck_durchlass_steigend = []
druck_durchlass_fallend = []
csv_buffer = [] 
fehler_historie = []
ableitung = 0

prev_error = 0
integral = 0

untere_hystere = False
obere_hystere = False
integral_flag = False

kp=0.95 #0.95 als konstanter parameter funktioniert ganz gut
ki= 0.02 #0.0005 #0.0001  # 0.2 #standartmäßig
kd = 0 # 0.00025 #5e-6
Dauer = 60 #Dauer in Sekunden, die der Druck im Zielbereich bleiben soll, damit das Programm stoppt. (zusätzlich zum relativen Fehler von 1% und der Ableitung des Drucks von 0.001 mBar/s)
Max_dauer = 300
counter_limit = 100

raw_array = b""
resp_array = ""
response_array = ""

def get_arrays_from_csv(dateipfad):
    global zeit, Druck, Ventilspannung_Durchlass, Ventilspannung_Einlass, StufenDauer
    try:
        df = pd.read_csv(dateipfad, sep=';', decimal=',', encoding='cp1252')
        df.columns = df.columns.str.strip()  # Entfernt führende und nachfolgende Leerzeichen aus den Spaltennamen
        zeit = df['Zeit_s'].values
        Druck = df['Druck_mBar'].values
        Ventilspannung_Durchlass = df['V_Durchlass'].values
        Ventilspannung_Einlass = df['V_Einlass'].values
        StufenDauer = df['Dauer bis Druckstabilitaet_s'].values
    except Exception as e:
        print(f"Fehler beim Laden: {e}")
        return False
    return True

def getpressure(ser): #"Druckauslesebefehl"
    global raw_array, resp_array, response_array
    try:
        raw = ser.readline()
        raw_array = raw
        resp = raw.decode('utf-8', errors='ignore') #liest die Werte vom CenterThree
        resp_array = resp
        response = resp.strip()
        response_array = response

        #response = ser.readline().decode('utf-8').strip() #liest die Werte vom CenterThree
        if response:
            #print(f'Antwort: {response}')
            values = response.split(",")
            values = [float(values[i]) for i in (1,3)]
            #print(f"Druckwerte: {values}")
            return values
        else:
            print('keine Antwort. ')
            ser.flushInput()
            return None
    except (ValueError, UnicodeDecodeError, IndexError) as e:
        print(f"Fehler bei der Druckauslesung: {e} | {response if 'response' in locals() else 'unbekannt'}" )
        ser.flushInput() # Puffer leeren 
        return None

def sensorwahl_mit_hysterese(pressure):
    global untere_hystere, obere_hystere, old_pressure

    istWert = pressure[0] #default Wert, falls alle Bedingungen fehlschlagen sollten

    if pressure[0]>= 1.0: # ab >= 1mBar immer sensor 1 verwenden
        istWert = pressure[0] 
        untere_hystere = False
    elif pressure[1]< 0.5: #ab <0.5mBar immer sensor 2 verwenden
        istWert = pressure[1]
        obere_hystere = False
    elif pressure[1] >= 0.5 and old_pressure < pressure[1] and old_pressure < 0.5: #wenn man von < 0.5mBar kommt und < 1.0mBar ist. -> sensor 2 verwenden
        istWert = pressure[1]
        untere_hystere = True
    elif pressure[1] >= 0.5 and untere_hystere == True: #wenn man von < 0.5mBar kommt und < 1.0mBar ist. -> sensor 2 verwenden
        istWert = pressure[1]
    elif pressure[0] < 1.0 and old_pressure >= pressure[0] and old_pressure >=1.0: #wenn man von > 1.0mBar kommt und > 0.1mBar ist. -> sensor 1 verwenden
        istWert = pressure[0] 
        obere_hystere = True
    elif pressure[0] < 1.0 and obere_hystere == True: #wenn man
        istWert = pressure[0] 
    if istWert <=0:
        istWert = 1e-4
    return istWert

def PID(sollwert, istwert):
    global fehler_historie, prev_error, kp, ki, kd, dt, integral, integral_flag
    safe_sollwert = max(sollwert, 1e-4)
    safe_istwert = max(istwert, 1e-4)
    
    error = np.log10(safe_sollwert) - np.log10(safe_istwert)
    rel_error = (sollwert - istwert) / sollwert


    #if abs(rel_error) <= 0.5:
    #     integral = integral + (error*dt)
    # if abs(rel_error) > 0.5:
    #     integral = 0
    if  abs(rel_error) <= 0.01:
        integral_flag = True

    # fehler_historie.append(error)
    # if len(fehler_historie) > 100:
    #     fehler_historie.pop(0)
    # integral = sum(fehler_historie)*dt
    if integral_flag: 
        integral = integral + (error*dt)
    else: 
        integral = 0.0    
    derivative = (error - prev_error)/dt
    output = (kp*error)+(ki*integral)+(kd*derivative)
    prev_error = error
    return output, rel_error, derivative, integral

def pressure_error_handler(ser, pressure, filename, Startzeit):
    retry_count = 0
    while pressure is None and retry_count < 20:
            pressure = getpressure(ser)
            if pressure is None:
                retry_count += 1
                time.sleep(0.1)
        
    if pressure is None: 
        print("Kritischer Fehler: Antwort vom Sensor auch nach 20 versuchen nicht sauber")
        try: 
            with open (filename, mode='a', newline='') as f:
                writer = csv.writer(f, delimiter=';')
                writer.writerow([f"{Startzeit:.3f}".replace('.', ','), "ERROR", 0, 0, "Sensor Timeout", "", "", ""])
        except PermissionError :
            print("Fehler: CSV Datei konnte nicht geöffnet werden. (Datei offen?)")
            pass
        return False
    return pressure

def max_fehler_bestimmung(istWert):
    if istWert < 7.5 * 1e-4:
        fehler_grenze = 0.02
    elif istWert < 1e-3:
        fehler_grenze = 0.0134
    elif istWert < 2.5*1e-3:
        fehler_grenze = 0.01
    elif istWert < 5*1e-3:
        fehler_grenze = 0.004
    elif istWert < 7.5*1e-3:
        fehler_grenze = 0.002
    elif istWert < 1e-2:
        fehler_grenze = 0.0015
    elif istWert >= 1*1e-2 and istWert < 5*1e-1:
        fehler_grenze = 0.001
    elif istWert >= 5*1e-1 and istWert < 7.5*1e-1:
        fehler_grenze = 0.02
    elif istWert >= 7.5 * 1e-1 and istWert < 1.0:
        fehler_grenze = 0.014
    elif istWert >= 1.0 and istWert < 2.5:
        fehler_grenze = 0.01
    elif istWert >= 2.5 and istWert < 5:
        fehler_grenze = 0.004
    elif istWert >= 5 and istWert < 7.5:
        fehler_grenze = 0.002
    elif istWert >= 7.5 and istWert < 10:
        fehler_grenze = 0.0014
    elif istWert >= 10:
        fehler_grenze = 0.001   
    return fehler_grenze

def interpolation(ventilspannungen, druck):
    v_data = np.array(ventilspannungen)
    p_data = np.array(druck)
    idx_inv = np.argsort(p_data)
    p_inv_sorted = p_data[idx_inv]
    v_inv_sorted = v_data[idx_inv]
    p_inv_final, inv_unique_idx = np.unique(p_inv_sorted, return_index=True)
    v_inv_final = v_inv_sorted[inv_unique_idx]

    if len(p_inv_final) > 1:
        x_interp_pchip = PchipInterpolator(p_inv_final, v_inv_final)
        return x_interp_pchip
    else: 
        return None
    
def steigung(ventilspannungen, druck, pressure, v_ein):
    if len(ventilspannungen) > 1:
        v_data = np.array(ventilspannungen)
        p_data = np.array(druck)
        idx = np.argsort(v_data)
        v_sorted = v_data[idx]
        p_sorted = p_data[idx]

        v_unique, unique_idx = np.unique(v_sorted, return_index=True)
        p_unique = p_sorted[unique_idx]
        
        if len(v_unique) > 1:
            x_interp = np.linspace(min(v_unique), max(v_unique), 500)
            pchip = PchipInterpolator(v_unique, p_unique)
            y_pchip = pchip(x_interp)
            

        dp_dV = []
        for i in range(len(x_interp)-1):
            delta_v = x_interp[i+1] - x_interp[i]
            delta_p = y_pchip[i+1] - y_pchip[i]
            sekante = abs(delta_p / delta_v)
            dp_dV.append(sekante)
        
        dp_dV.append(dp_dV[-1])
        
        max_idx = np.argmax(dp_dV)
        max_steigung = abs(dp_dV[max_idx])
        max_volt = x_interp[max_idx]
        max_druck = y_pchip[max_idx]

        idx_v_ein = np.abs(x_interp - v_ein).argmin()
        steigung_v_ein = abs(dp_dV[idx_v_ein])

        print("\n=======================================================")
        print(f"-> Höchste Steigung:  {max_steigung:.4f} mBar/V")
        print(f"-> Bei Spannung:      {max_volt:.6f} V")
        print(f"-> Bei Druck:         {max_druck:.4f} mBar")
        print(f"-> Steigung Sollwert: {steigung_v_ein:.4f} mBar/V")
        print(f"-> Bei Spannung:      {v_ein:.6f} V")
        print(f"-> Bei Druck:         {pressure:.4f} mBar")
        return max_steigung, steigung_v_ein
    else:
        return None


def druckeingabe ():
    Solldruck = input("Bitte geben Sie den gewünschten Solldruck in mBar ein: ")
    try:
        return float(Solldruck)
    except ValueError:
        print("Ungültige Eingabe. Bitte geben Sie eine Zahl ein.")
        return druckeingabe()




def regelung(ser, task, Sollwert, filename, Startzeit):
    global old_pressure, csv_buffer, raw_array, resp_array, response_array, counter_limit, Dauer, kp, ki, dt
    global lut_v_einlass_fallend, druck_einlass_fallend, lut_v_einlass_steigend, druck_einlass_steigend, lut_v_durchlass_fallend, druck_durchlass_fallend, lut_v_durchlass_steigend, druck_durchlass_steigend, ableitung

    rel_fehler = 1
    lokale_zeit = 0

    pressure = getpressure(ser)
    result = pressure_error_handler(ser, pressure, filename, Startzeit)
    if result == False:
        return
    else: 
        pressure = result
    
    istWert = sensorwahl_mit_hysterese(pressure)
    compare_pressure =  istWert

    V_ein_fallend = interpolation(lut_v_einlass_fallend, druck_einlass_fallend)
    #V_ein_steigend = interpolation(lut_v_einlass_steigend, druck_einlass_steigend)
    #V_durch_fallend = interpolation(lut_v_durchlass_fallend, druck_durchlass_fallend)
    #V_durch_steigend = interpolation(lut_v_durchlass_steigend, druck_durchlass_steigend)
    if V_ein_fallend is None:
        print("Fehler: Interpolation fehlgeschlagen, LUT leer?")
        return
    V_ein_genau = V_ein_fallend(Sollwert)
    max_sensitivity, Sollwert_sensitivity = steigung(lut_v_einlass_fallend, druck_einlass_fallend, Sollwert, V_ein_genau)
    print (f"Anfängliche Kp: {kp:.4f} | Sensitivität Sollwert: {Sollwert_sensitivity:.4f} | Max Sensitivität: {max_sensitivity:.4f}")
    if Sollwert_sensitivity < 1e-3:
        Sollwert_sensitivity = 1e-3

    #da muss man sich nochmehr gedanken machen....
    kp = kp  * (max_sensitivity/Sollwert_sensitivity)**(1/20) #man könnte hier auch mit einem anderen Exponenten arbeiten, um die Anpassung abzuschwächen
    print(f"Angepasster Kp basierend auf Sensitivität: {kp:.4f}")
    tangent_counter = 0
    Endzeit = Max_dauer
    while lokale_zeit < Endzeit and istWert >= 0.001: #relativer Fehler kleiner 1%
        pressure = getpressure(ser)
        result = pressure_error_handler(ser, pressure, filename, Startzeit)
        if result == False:
            return
        else: 
            pressure = result
        istWert = sensorwahl_mit_hysterese(pressure)
        
        Stellgröße, rel_fehler, d_anteil, i_anteil= PID(Sollwert, istWert)
        v_durch = 10

        
        v_ein = np.clip(V_ein_genau + Stellgröße, 0, 10)
        task.write([v_durch, v_ein])

        #Stabilitätscheck
        schwankung = (istWert - old_pressure)/old_pressure
        schwankung_in_relation_zum_vergleich = (istWert - compare_pressure)/compare_pressure
        fehler_grenze = max_fehler_bestimmung(istWert)
        rel_fehler_grenze = 5 * fehler_grenze

        if abs(schwankung) <= fehler_grenze and abs(schwankung_in_relation_zum_vergleich) <= rel_fehler_grenze and rel_fehler < 0.01: 
            if (tangent_counter == counter_limit) or lokale_zeit > Max_dauer - 1.5:
                #Stab_Startzeit = lokale_zeit
                #Endzeit = Stab_Startzeit + Dauer
                dur_str = f"{(lokale_zeit):.3f}".replace('.', ',')
            elif tangent_counter > counter_limit and lokale_zeit > Endzeit -1.5:
                dur_str = "300,0"
            else:
                dur_str = ""
            tangent_counter += 1
        elif (abs(schwankung) > fehler_grenze or abs(schwankung_in_relation_zum_vergleich) > rel_fehler_grenze):
            #if diff_compare_to_Solldruck > diff_istWert_Solldruck and diff_istWert_Solldruck * diff_compare_to_Solldruck >= 0:
            tangent_counter = 0
            Endzeit = Max_dauer
            compare_pressure = istWert
            dur_str = ""
        
        t_str = f"{lokale_zeit:.3f}".replace('.', ',')
        p_str = f"{istWert:.5f}".replace('.', ',')
        vd_str = f"{v_durch:.2f}".replace('.', ',')
        ve_str = f"{v_ein:.2f}".replace('.', ',')
        stellgröße_str = f"{Stellgröße:.5f}".replace('.', ',')
        
        #response_str = str(response_array).replace('.', ',')  if response_array else ''

        csv_buffer.append([t_str, p_str, vd_str, ve_str, stellgröße_str, dur_str])
        try: 
            with open (filename, mode='a', newline='') as f:
                writer = csv.writer(f, delimiter=';')
                while csv_buffer:
                    writer.writerow(csv_buffer[0])
                    csv_buffer.pop(0)
        except PermissionError :
            print("Fehler: CSV Datei konnte nicht geöffnet werden. (Datei offen?)")
            pass

        print(f"relativer Fehler:{rel_fehler: .4} | Druck: {istWert:.5f} mBar | Dauer: {lokale_zeit:.3f} s")
        print(f"D-Anteil: {d_anteil: .6f} | I-Anteil: {i_anteil: .6f} | Stellgröße: {Stellgröße: .4f}") 
        print(f"V_ein_genau: {V_ein_genau: .4f} V | V_Ein: {v_ein:.4f} V | V_Durch: {v_durch:.4f} V ")
        print(f"Tangent Counter: {tangent_counter}") 
        print(f"Schwankung: {schwankung:.5f} | rel. Schwankung: {schwankung_in_relation_zum_vergleich:.5f}")
        print()


        old_pressure = istWert
        wartezeit = Startzeit + lokale_zeit
        while time.time() - wartezeit < dt:
            time.sleep(0.01)
        lokale_zeit = time.time() - Startzeit




    


def main():
    global Druck, Ventilspannung_Durchlass, Ventilspannung_Einlass, zeit, StufenDauer, stab_druck
    global lut_v_einlass_steigend, lut_v_einlass_fallend, druck_einlass_steigend, druck_einlass_fallend 
    global lut_v_durchlass_steigend, lut_v_durchlass_fallend, druck_durchlass_steigend, druck_durchlass_fallend

    #Pfad = input("Geben Sie den Pfad zur CSV-Datei ein: ").strip().replace('"', '')
    Pfad = r"C:\Users\labor\Documents\messung_ventil_mehr_stützpunkte_gut.csv"
    get_arrays_from_csv(Pfad)
    
    filename = f"messung_{time.strftime('%Y%m%d-%H%M%S')}.csv"
    with open(filename, mode='w', newline='') as f:
        writer = csv.writer(f, delimiter=';')
        writer.writerow(['Zeit_s', 'Druck_mBar', 'V_Durchlass', 'V_Einlass', 'Stellgröße', 'response'])

    for i in range(len(StufenDauer)):
        if not pd.isna(StufenDauer[i]):
            stab_ventilspannung_einlass.append(Ventilspannung_Einlass[i])
            stab_ventilspannung_durchlass.append(Ventilspannung_Durchlass[i])
            stab_druck.append(Druck[i])
    
    print(f"länge stab_druck: {len(stab_druck)}")
    print()

    for i in range(1, len(stab_ventilspannung_einlass)):
        v_aktuell = stab_ventilspannung_einlass[i]
        v_vorher = stab_ventilspannung_einlass[i-1]
        
        if stab_ventilspannung_durchlass[i] == 10:
            if v_aktuell > v_vorher:
                lut_v_einlass_steigend.append(v_aktuell)
                druck_einlass_steigend.append(stab_druck[i])
            elif v_aktuell < v_vorher:
                lut_v_einlass_fallend.append(v_aktuell)
                druck_einlass_fallend.append(stab_druck[i])

        if stab_ventilspannung_einlass[i] == 0:
            if v_aktuell > v_vorher:
                lut_v_durchlass_steigend.append(stab_ventilspannung_durchlass[i])
                druck_durchlass_steigend.append(stab_druck[i])
            elif v_aktuell < v_vorher:
                lut_v_durchlass_fallend.append(stab_ventilspannung_durchlass[i])
                druck_durchlass_fallend.append(stab_druck[i])

    task_completed = False
    try:
        ser = serial.Serial(port=sp, baudrate=br, timeout=to) #stellt Verbindung mit der Vakuumpumpe her (öffnet Chanel)
        print(f'Verbindung hergestellt mit {sp}')

        system = nidaqmx.system.System.local()
        for dev in system.devices:
            print(dev.name, "-", dev.product_type)
        with nidaqmx.Task() as task:
                task.ao_channels.add_ao_voltage_chan(f"Dev1_MSA/ao0") 
                task.ao_channels.add_ao_voltage_chan(f"Dev1_MSA/ao1")
                task.start()

                Solldruck = druckeingabe()
                regelung(ser, task,  Solldruck, filename=filename, Startzeit=time.time())
                
                print("ao0: 0 , ao1: 5.5")
                task.write([0, 5.5])
                time.sleep(9)
                print("ao0: 0 , ao1: 7")
                task.write([0, 7.0])
                time.sleep(6)
                print("ao0: 0 , ao1: 10")
                task.write([0, 10.0])
                time.sleep(3)
                task.write([0.0, 0.0])  # Alle Ausgänge auf 0 setzen
                task_completed = True
                print('Erfolgreich abgeschlossen. Verbindung wird beendet')
                task.stop()
    except KeyboardInterrupt:
        print("Programm unterbrochen.")
        try:
            with nidaqmx.Task() as task:
                task.ao_channels.add_ao_voltage_chan(f"Dev1_MSA/ao0") 
                task.ao_channels.add_ao_voltage_chan(f"Dev1_MSA/ao1")
                task.start()
                print("ao0: 0 , ao1: 5.5")
                task.write([0, 5.5])
                time.sleep(9)
                print("ao0: 0 , ao1: 7")
                task.write([0, 7.0])
                time.sleep(6)
                print("ao0: 0 , ao1: 10")
                task.write([0, 10.0])
                time.sleep(3)
                task.write([0.0, 0.0])
                task.stop()
        except Exception as e:
                pass
    except serial.SerialException as e:
        print(f'Fehler: {e}')
    except UnicodeDecodeError as e:
        print(f'Fehler bei der Dekodierung: {e}')
    finally:
        if not task_completed:
            try: 
                with nidaqmx.Task() as task:
                    task.ao_channels.add_ao_voltage_chan(f"Dev1_MSA/ao0") 
                    task.ao_channels.add_ao_voltage_chan(f"Dev1_MSA/ao1")
                    task.start()
                    task.write([0.0, 0.0])  # Alle Ausgänge auf 0 setzen
                    if 'ser' in locals() and ser.is_open:
                        ser.close()
                        print('Verbindung closed. ')
                    task.stop()
            except Exception as e:
                pass
        else: 
            try:
                if 'ser' in locals() and ser.is_open:
                    ser.close()
                    print('Verbindung closed. ')
            except Exception as e:
                pass   

main()
