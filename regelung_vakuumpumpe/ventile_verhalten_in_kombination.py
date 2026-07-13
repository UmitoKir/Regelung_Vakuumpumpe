#install the driver software NI-DAQ™mx
#install all the necessary libaries and debugger/compiler(python, python debugger, git etc.) to get it running on VS code
#install with py -m pip install in the terminal all the necessary packages
#matplotlib maybe also required
import csv
import time
import numpy as np 
import PressureSensor
import ValveControl
import CSVManager


#10, 9.5, 9, 8.5, 8, 
#0, 0.5, 1, 1.5, 2, 
ventilspannungen1 = [8, 7.549, 7.381, 7.291, 7.234, 7.164, 7.034, 6.618, 6.130, 6.074, 
                     6.013, 5.951, 5.891, 5.825, 5.746, 5.648, 5.522, 5.358, 5.331, 5.301, 5.266, 5.226, 
                     5.181, 5.129, 5.072, 5.008, 4.928, 4.909, 4.886, 4.858, 4.824, 4.784, 4.738, 4.684, 
                     4.622, 4.552, 4.545, 4.537, 4.530, 4.522, 4.514, 4.506, 4, 3, 2, 1, 0]
ventilspannungen2 = [3, 3.483, 3.738, 3.882, 4.022, 4.161, 4.294, 4.462, 4.664,
                     4.692, 4.723, 4.758, 4.799, 4.845, 4.897, 4.956, 5.018, 5.113, 5.134, 5.159, 5.187,
                     5.219, 5.255, 5.295, 5.341, 5.392, 5.448, 5.454, 5.460, 5.466, 5.472, 5.478, 5.484,
                     5.491, 5.497, 5.657, 5.720, 5.795, 5.882, 5.980, 6.181, 6.597, 7, 8, 9, 10]
counter_limit = 200

untere_hystere = False
obere_hystere = False

class CSVDatei(CSVManager.CreateFile):
    def writeToCSV(self, zeit, druck, v_durchlass, v_einlass, duration, response):
        t_str = f"{zeit:.3f}".replace('.', ',')
        p_str = f"{druck:.5f}".replace('.', ',')
        vd_str = f"{v_durchlass:.4f}".replace('.', ',')
        ve_str = f"{v_einlass:.4f}".replace('.', ',')
        if duration == None: 
            dur_str = ""
        else: 
            dur_str = f"{duration:.3f}".replace('.', ',')
        response_str = f"{response}".replace('.', ',')
        self.buffer.append([t_str, p_str, vd_str, ve_str, dur_str, response_str]) 
        try:
            with open(self.full_path, mode='a', newline='', encoding = "utf-8") as f:
                writer = csv.writer(f, delimiter=';')
                while self.buffer:
                    writer.writerow(self.buffer[0])
                    self.buffer.pop(0)
        except PermissionError:
            print("Fehler: CSV Datei konnte nicht geöffnet werden. (Ist die Datei parallel geöffnet?)")
            pass
    

def Druck_abfahren(sensor, valves, CSVFile, v_durch, v_ein, startzeit, current_step, total_steps):
    max_dauer = 240
    counter_limit = 450
    startzeit_neuer_druck = time.time() - startzeit
    lokale_zeit = time.time() - (startzeit_neuer_druck + startzeit)
    tangent_counter = 0
    
    valves.applyVoltage(v_durch, v_ein)
    
    istwert = sensor.getPressure()
    compare_pressure =  istwert

    while(istwert > 0.001) and (lokale_zeit < max_dauer) and (tangent_counter <= counter_limit):
        istwert = sensor.getPressure()
        lokale_zeit = time.time() -  (startzeit_neuer_druck + startzeit)
        #Stabilitätscheck
        schwankung = (istwert - sensor.oldpressure)/sensor.oldpressure
        schwankung_in_relation_zum_vergleich = (istwert - compare_pressure)/compare_pressure

        if abs(schwankung) <= sensor.fehler_grenze and abs(schwankung_in_relation_zum_vergleich) <= sensor.rel_fehler_grenze:
            if (tangent_counter == counter_limit) or lokale_zeit > max_dauer - 1.5:
                duration = lokale_zeit
            else: 
                duration = None
            tangent_counter += 1
        elif (abs(schwankung) > sensor.fehler_grenze or abs(schwankung_in_relation_zum_vergleich) > sensor.rel_fehler_grenze):
            tangent_counter = 0
            compare_pressure = istwert
            duration = None

        CSVFile.writeToCSV(
            zeit = lokale_zeit + startzeit_neuer_druck, 
            druck = istwert, 
            v_durchlass =v_durch, 
            v_einlass = v_ein, 
            duration = duration, 
            response = sensor.response_array
            ) 
        
        print(f"V_Einlass: {v_ein:.3f} V | V_Durch: {v_durch:.3f} V | Druck: {istwert:.5f} mBar")
        print(f"Schwankung: {schwankung:.5f} | rel. Schwankung zu Vergleichswert: {schwankung_in_relation_zum_vergleich:.5f} ") 
        print(f"Dauer der Stufe: {lokale_zeit:.3f} s | Tangent Counter: {tangent_counter} | Runde: {current_step} von {total_steps} ")
        print()

        wartezeit = startzeit_neuer_druck + lokale_zeit + startzeit
        while time.time() - wartezeit < 0.093:
            time.sleep(0.01)
        itaration_duration = time.time() - (startzeit_neuer_druck + lokale_zeit + startzeit)        
        print(f"Dauer einer iteration(dt): {itaration_duration:.4f}")
        

       



def main():
    global ventilspannungen1, ventilspannungen2

    CSVFile = CSVDatei()
    csv_spalten = ['Zeit_s', 'Druck_mBar', 'V_Durchlass', 'V_Einlass', 'Dauer','response']
    CSVFile.allocateCSV(stringchain=csv_spalten)

    sensor = PressureSensor.PressureSensor()
    valves = ValveControl.ValveControl()
    task_completed = False

    try:
        if not sensor.connect():
            raise RuntimeError("Verbindung zum Drucksensor fehlgeschlagen.")
        
        if not valves.connect():
            raise RuntimeError("Ventil-Initialisierung fehlgeschlagen.")

        total_steps = len(ventilspannungen1) #* len(ventilspannungen1)
        current_step = 0
        startzeit = time.time()
            
        #for v_durch in ventilspannungen2:
        for v_ein in ventilspannungen1:
            v_durch = 10.0 - v_ein
            current_step += 1
            Druck_abfahren(sensor = sensor, 
                            valves = valves, 
                            CSVFile = CSVFile, 
                            v_durch = v_durch, 
                            v_ein = v_ein, 
                            startzeit = startzeit, 
                            current_step = current_step, 
                            total_steps = total_steps
                            )            
                
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
