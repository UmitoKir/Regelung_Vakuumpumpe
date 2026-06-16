#install the driver software NI-DAQ™mx
#install all the necessary libaries and debugger/compiler(python, python debugger, git etc.) to get it running on VS code
#install with py -m pip install in the terminal all the necessary packages
#matplotlib maybe also required
import time
import numpy as np 
import PressureSensor
import ValveControl
import Mathfunctions
import CSVManager


br = 38400
to = 1

dt = 1
old_pressure = 1000
csv_buffer = [] 
fehler_historie = []
ableitung = 0

prev_error = 0
integral = 0


kp=0.8 #0.95 als konstanter parameter funktioniert ganz gut
ki= 0.0 #0.0005 #0.0001  # 0.2 #standartmäßig
kd = 0 # 0.00025 #5e-6
Dauer = 60 #Dauer in Sekunden, die der Druck im Zielbereich bleiben soll, damit das Programm stoppt. (zusätzlich zum relativen Fehler von 1% und der Ableitung des Drucks von 0.001 mBar/s)
Max_dauer = 300
counter_limit = 100

raw_array = b""
resp_array = ""
response_array = ""

#hier regelung muss noch komplett bearbeitet und angepasst werden.
def regelung(sensor, valves, lutData, measuredData sollwert, Startzeit):
    global  csv_buffer, counter_limit, Dauer, kp, ki, kd, dt 

    rel_fehler = 1
    lokale_zeit = 0

    istWert = sensor.getPressure()
    
    compare_pressure =  istWert
    Math = Mathfunctions.Interpolation(sollwert)
    V_ein_fallend = Math.interpolierte_Funktion(lutData.stab_v_einlass_fallend, lutData.stab_druck_einlass_fallend)
    if V_ein_fallend is None:
        print("Fehler: Interpolation fehlgeschlagen, LUT leer?")
        return
    V_ein_genau = V_ein_fallend(sollwert)
    max_sensitivity, Sollwert_sensitivity = Math.steigung(lutData.stab_v_einlass_fallend, lutData.stab_druck_einlass_fallend, sollwert, V_ein_genau)
    print (f"Anfängliche Kp: {kp:.4f} | Sensitivität Sollwert: {Sollwert_sensitivity:.4f} | Max Sensitivität: {max_sensitivity:.4f}")
    if Sollwert_sensitivity < 1e-3:
        Sollwert_sensitivity = 1e-3
    #da muss man sich nochmehr gedanken machen....
    kp = kp  * (max_sensitivity/Sollwert_sensitivity)**(1/20) #man könnte hier auch mit einem anderen Exponenten arbeiten, um die Anpassung abzuschwächen
    controllUnit = Mathfunctions.ControllSystem(kp, ki, kd, dt)
    print(f"Angepasster Kp basierend auf Sensitivität: {kp:.4f}")
    tangent_counter = 0
    Endzeit = Max_dauer


#------------------Ab hier noch alles anzupassen an die neue Klassenstruktur------------------
    while lokale_zeit < Endzeit and istWert >= 0.001: #relativer Fehler kleiner 1%
        istWert = sensor.getPressure()
        Stellgröße, rel_fehler, d_anteil, i_anteil= controllUnit.logarithmicPID(sollwert, istWert)
        v_durch = 10

        #V_ein muss noch bestimmt werden
        v_ein = np.clip(V_ein_genau + Stellgröße, 0, 10)
        valves.applyVoltage(v_durch, v_ein)

        #Stabilitätscheck
        schwankung = (istWert - old_pressure)/old_pressure
        schwankung_in_relation_zum_vergleich = (istWert - compare_pressure)/compare_pressure
        fehler_grenze = sensor.maxFehlerBestimmung()
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
            
        """
        t_str = f"{lokale_zeit:.3f}".replace('.', ',')
        p_str = f"{istWert:.5f}".replace('.', ',')
        vd_str = f"{v_durch:.2f}".replace('.', ',')
        ve_str = f"{v_ein:.2f}".replace('.', ',')
        stellgröße_str = f"{Stellgröße:.5f}".replace('.', ',')
        
        #response_str = str(response_array).replace('.', ',')  if response_array else ''

        csv_buffer.append([t_str, p_str, vd_str, ve_str, stellgröße_str, dur_str])
        try: 
            with open (measuredData.fullpath, mode='a', newline='') as f:
                writer = csv.writer(f, delimiter=';')
                while csv_buffer:
                    writer.writerow(csv_buffer[0])
                    csv_buffer.pop(0)
        except PermissionError :
            print("Fehler: CSV Datei konnte nicht geöffnet werden. (Datei offen?)")
            pass
        """
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
    
    #Pfad = input("Geben Sie den Pfad zur CSV-Datei ein: ").strip().replace('"', '')
    Pfad = r"C:\Users\labor\Documents\messung_ventil_mehr_stützpunkte_gut.csv"
    

    #LutCSV = CSVManager.CSVReader()
    #LutCSV.inputPath() 
    LutCSV = CSVManager.CSVReader(Pfad)
    LutCSV.extractData()


    CSVfile = CSVManager.CreateCSV(filename=None, pfad=Pfad)
    CSVfile.allocateCSV()

    task_completed = False

    sensor = PressureSensor()
    valves = ValveControl()

    try:
        if not sensor.connect():
            raise RuntimeError("Verbindung zum Drucksensor fehlgeschlagen.")
        
        if not valves.connect():
            raise RuntimeError("Ventil-Initialisierung fehlgeschlagen.")
    
        Solldruck = Mathfunctions.Eingabe.druckeingabe()

        #hier die nächste Zeile muss noch evtl. bearbeitet werden.
        regelung(sensor=sensor,  valves=valves, lutData=LutCSV, measuredData=CSVfile, Solldruck, Startzeit=time.time())

        valves.ambientPressure()

        task_completed = True
        if task_completed:
            print('Erfolgreich abgeschlossen. Verbindung wird beendet')
        valves.close()
    except KeyboardInterrupt:
        print("Programm unterbrochen.")
        valves.ambientPressure()
    except UnicodeDecodeError as e:
        print(f'Fehler bei der Dekodierung: {e}')
    finally:
        valves.shutdown()  # Alle Ausgänge auf 0 setzen
        valves.close()
        sensor.disconnect()

main()
