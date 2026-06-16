import nidaqmx
import time

class Valvecontrol:
    def __init__(self, valve_name = "Dev1_MSA", ao0_name = "ao0", ao1_name = "ao1"):
        self.valve_name = valve_name
        self.channel_name_0 = f"{valve_name}/{ao0_name}"
        self.channel_name_1 = f"{valve_name}/{ao1_name}"
        self.task = None
    
    def connect(self):
        try: 
            system = nidaqmx.system.System.local()
            print("Verfügbare der DAQ-Geräte:")
            for dev in system.devices:
                print(dev.name, "-", dev.product_type)
            self.task = nidaqmx.Task()
            self.task.ao_channels.add_ao_voltage_chan(self.channel_name_0)
            self.task.ao_channels.add_ao_voltage_chan(self.channel_name_1)
            self.task.start()
            print("DAQ-Kanäle erfolgreich initialisiert.")
            return True
        except Exception as e:
            print(f"Fehler bei der Ventil-Initialisierung: {e}")
            self.close()
            return False
        
    def applyVoltage(self, v_durch, v_ein):
        if self.task is None:
            print("Ventile nicht initialisiert....")
            return False
        v_durchlass = max(0.0, min(10.0, float(v_durchlass)))
        v_einlass = max(0.0, min(10.0, float(v_einlass)))

        try: 
            self.task.write([v_durch, v_ein])
            return True 
        except Exception as e:
            print("Fehler bei anlegen der Ventilspannungen: {e}")
            return False
        
    def ambientPressure(self):
        print("ao0: 0 , ao1: 5.5")
        self.applyVoltages(0.0, 5.0)
        time.sleep(5)
        
        print("ao0: 0 , ao1: 7")
        self.applyVoltages(0.0, 6.0)
        time.sleep(5)
        
        print("ao0: 0 , ao1: 7")
        self.applyVoltages(0.0, 7.0)
        time.sleep(4)

        print("ao0: 0 , ao1: 10")
        self.applyVoltages(0.0, 10.0)
        time.sleep(3)

    def shutdown(self):
        try: 
            self.task.write([0.0, 0.0])
            return True 
        except Exception as e:
            print("Fehler bei Schließung der Ventile: {e}")
            return False
    def close(self):
        if self.task is not None:
            try:
                self.shutdown()
                self.task.stop()
                self.task.close()
                print("DAQmx-Task sauber beendet.")
            except Exception as e:
                print(f"Fehler beim Schließen der DAQmx-Task: {e}")
            finally:
                self.task = None

if __name__ == "__main__":
    valves = Valvecontrol()
    task_completed = False
    try:    
        if not valves.connect():
            raise RuntimeError("Ventil-Initialisierung fehlgeschlagen.")
        
        print("ao0: 10 , ao1: 0")
        valves.applyVoltages(10.0, 0.0)
        time.sleep(10)

        valves.ambientPressure()
        
        task_completed = True
        if task_completed:
            print('Erfolgreich abgeschlossen.')
    except Exception as e:
        print(f"Ein Fehler ist aufgetreten: {e}")
    finally:
        valves.close()