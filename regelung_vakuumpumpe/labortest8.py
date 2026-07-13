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


kp=0.8 #0.95 als konstanter parameter funktioniert ganz gut

ki= 0.05 #letzter stand 0.001 funtioniert könnte aber noch strärker sein 
#0.0005 #0.0001  # 0.2 #standartmäßig

kd = 0.0 #vllt 0.1 oder 0.05 #5e-6
dt = 0.1

Dauer = 60 #Dauer in Sekunden, die der Druck im Zielbereich bleiben soll, damit das Programm stoppt. (zusätzlich zum relativen Fehler von 1% und der Ableitung des Drucks von 0.001 mBar/s)
Max_dauer = 1000
counter_limit = 500


#hier regelung muss noch komplett bearbeitet und angepasst werden.
def regelung(sensor, valves, lutData, measuredData, sollwert, startzeit):
    global  csv_buffer, counter_limit, Dauer, kp, ki, kd, dt 

    rel_fehler = 1
    lokale_zeit = 0

    istwert = sensor.getPressure()
    
    compare_pressure =  istwert
    Math = Mathfunctions.Interpolation(sollwert)
    V_ein_fallend = Math.interpolierte_Funktion(lutData.stab_v_einlass_fallend, lutData.stab_druck_einlass_fallend)
    if V_ein_fallend is None:
        print("Fehler: Interpolation fehlgeschlagen, LUT leer?")
        return
    Math.v_ein = V_ein_fallend(sollwert)
    Math.steigung(lutData.stab_v_einlass_fallend, lutData.stab_druck_einlass_fallend)
    print (f"Anfängliche Kp: {kp:.4f} | Sensitivität Sollwert: {Math.steigung_v_ein:.4f} | Max Sensitivität: {Math.max_steigung:.4f}")
    if Math.steigung_v_ein < 1e-3:
        Math.steigung_v_ein = 1e-3
    prev_kp = kp
    #da muss man sich nochmehr gedanken machen....
    kp = kp  * (Math.max_steigung/Math.steigung_v_ein)**(1/7) #man könnte hier auch mit einem anderen Exponenten arbeiten, um die Anpassung abzuschwächen
    ki = ki * (Math.max_steigung/Math.steigung_v_ein)**(1/5)
    controlUnit = Mathfunctions.ControllSystem(kp=kp, ki=ki, kd=kd, sollwert=sollwert, dt=dt)
    print(f"Angepasster Kp basierend auf Sensitivität: {kp:.4f}")
    tangent_counter = 0
    Endzeit = Max_dauer

    measuredData.TxtFile(sollwert=sollwert, alter_kp=prev_kp, kp=kp, ki=ki, kd=kd, dt=dt, steigung_bei_sollwert = Math.steigung_v_ein, max_steigung = Math.max_steigung, druck_max_steigung = Math.druck_bei_max_steigung )

    
    while lokale_zeit < Endzeit and istwert >= 0.001: #relativer Fehler kleiner 1%
        istwert = sensor.getPressure()
        lokale_zeit = time.time() - startzeit
        Stellgröße, rel_fehler, d_anteil, i_anteil= controlUnit.logarithmicPID(istwert)
        v_durch = 10

        #V_ein muss noch bestimmt werden
        v_ein = np.clip(Math.v_ein + Stellgröße, 0, 10)
        valves.applyVoltage(v_durch, v_ein)

        #Stabilitätscheck
        schwankung = (istwert - sensor.oldpressure)/sensor.oldpressure
        schwankung_in_relation_zum_vergleich = (istwert - compare_pressure)/compare_pressure

        
        if abs(schwankung) <= sensor.fehler_grenze and abs(schwankung_in_relation_zum_vergleich) <= sensor.rel_fehler_grenze and rel_fehler < 0.01: 
            if (tangent_counter == counter_limit) or lokale_zeit > Max_dauer - 1.5:
                #Stab_Startzeit = lokale_zeit
                #Endzeit = Stab_Startzeit + Dauer
                dur_str = f"{(lokale_zeit):.3f}".replace('.', ',')
            elif tangent_counter > counter_limit and lokale_zeit > Endzeit -1.5:
                dur_str = "300,0"
            else:
                dur_str = ""
            tangent_counter += 1
        elif (abs(schwankung) > sensor.fehler_grenze or abs(schwankung_in_relation_zum_vergleich) > sensor.rel_fehler_grenze):
            #if diff_compare_to_Solldruck > diff_istWert_Solldruck and diff_istWert_Solldruck * diff_compare_to_Solldruck >= 0:
            tangent_counter = 0
            Endzeit = Max_dauer
            compare_pressure = istwert
            dur_str = ""

        measuredData.writeToCSV(
                                zeit=lokale_zeit,
                                druck=istwert, 
                                v_durchlass=v_durch, 
                                v_einlass=v_ein, 
                                stellgröße=Stellgröße, 
                                response=sensor.response_array, 
                                duration=dur_str, 
                                p_anteil=controlUnit.p_anteil, 
                                i_anteil=controlUnit.i_anteil, 
                                d_anteil=controlUnit.d_anteil
                                )
    
        print(f"relativer Fehler:{rel_fehler: .4} | Druck: {istwert:.5f} mBar ({sensor.sensorwahl}) | Dauer: {lokale_zeit:.3f} s")
        print(f"P-Anteil: {controlUnit.p_anteil: .6f} | I-Anteil: {controlUnit.i_anteil: .6f} | D-Anteil: {controlUnit.d_anteil: .6f}")
        print(f"Stellgröße: {Stellgröße: .4f}") 
        print(f"V_ein_genau: {Math.v_ein: .4f} V | V_Ein: {v_ein:.4f} V | V_Durch: {v_durch:.4f} V ")
        print(f"Tangent Counter: {tangent_counter}") 
        print(f"Schwankung: {schwankung:.5f} | rel. Schwankung: {schwankung_in_relation_zum_vergleich:.5f}")
        print()
        
        wartezeit = startzeit + lokale_zeit
        while time.time() - wartezeit < 0.093:
            time.sleep(0.01)
        itaration_duration = time.time()-startzeit - lokale_zeit
        controlUnit.dt = itaration_duration
        print(f"Dauer einer iteration(dt): {itaration_duration:.4f}")
        




def main():
    
    #Pfad = input("Geben Sie den Pfad zur CSV-Datei ein: ").strip().replace('"', '')
    pfad = r"C:\Users\labor\Documents\messung_ventil_mehr_stützpunkte_gut.csv"
    

    #LutCSV = CSVManager.CSVReader()
    #LutCSV.inputPath() 
    LutCSV = CSVManager.CSVReader(pfad)
    LutCSV.extractData()


    CSVfile = CSVManager.CreateFile()
    CSVfile.allocateCSV()

    task_completed = False

    sensor = PressureSensor.PressureSensor()
    valves = ValveControl.ValveControl()

    try:
        if not sensor.connect():
            raise RuntimeError("Verbindung zum Drucksensor fehlgeschlagen.")
        
        if not valves.connect():
            raise RuntimeError("Ventil-Initialisierung fehlgeschlagen.")
    
        solldruck = Mathfunctions.Eingabe.druckeingabe()

        #hier die nächste Zeile muss noch evtl. bearbeitet werden.
        startzeit = time.time()
        regelung(sensor=sensor,  valves=valves, lutData=LutCSV, measuredData=CSVfile, sollwert = solldruck, startzeit=startzeit)

        valves.ambientPressure()

        task_completed = True
        if task_completed:
            print('Erfolgreich abgeschlossen. Verbindung wird beendet')
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
