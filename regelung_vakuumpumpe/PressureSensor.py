import serial
import serial.tools.list_ports
import time


class PressureSensor:
    FIRST_CONSTANT = 15

    def __init__(self, port=None, baudrate = 38400, timeout = 0.05):
        self.port = port
        self.ser = None
        self.baudrate = baudrate
        self.timeout = timeout   
        self.old_pressure = 1000
        self.untere_hysterese = False
        self.obere_hysterese = False
        self.pressure = 1000
        self.pressure_Error = False
        self.response_array = None
        self.fehler_grenze = None
        self.rel_fehler_grenze = None
        self.pressure_buffer = []
        self.sensorwahl = ""


    def findDevice(self):
        #this function gets automatically triggered when the connect function is called. So Don't call this function directly, because it is not designed to be called directly.
        ports = list(serial.tools.list_ports.comports()) #ruft eine Liste mit allen existierenden Anschlüssen an Ihrem Computer ab
        print(f'Liste der angeschlossenen Geräte: {ports}')
        for p in ports:
            if 'ATEN'in p.description:
                print(f'this is the Device: {p.device}')
                self.port = p.device
                return self.port
        if self.port is None:
            print('Das Gerät wurde nicht gefunden.')
            return None

    def connect(self):
        if self.port is None:
            self.findDevice()
        if self.port is None:
            print("Kein gültiger Port gefunden. Verbindung fehlgeschlagen.")
            return False
        
        try:
            self.ser = serial.Serial(port=self.port, baudrate = self.baudrate, timeout = self.timeout)
            
            print(f"Erfolgreich mit {self.port} verbunden.")
            # Send device command in ASCII:  C O M , a <CR> <LF>
            self.ser.write(b'COM,0\r\n')
            return True
        except serial.SerialException as e:
            print(f"Fehler beim Verbinden mit {self.port}: {e}")
            return False
    
    def disconnect(self):
        if self.ser and self.ser.is_open:
            self.ser.close()
            print(f"Verbindung zu {self.port} geschlossen.")

    def _readPressure(self):
        #this function gets automatically triggered when the get_pressure function is called. So Don't call this function directly, because it is not designed to be called directly.
        if not self.ser or not self.ser.is_open:
            return None
        try:
            if self.ser.in_waiting > 0: 
                raw = self.ser.readline()
            else: 
                return None
            resp = raw.decode('utf-8', errors='ignore').strip()
            if resp:
                values = resp.split(",")
                pressure = [float(values[1]), float(values[3])]
                self.response_array = resp
                return pressure 
        except Exception as e :
                self.ser.flushInput()
        return None
    def _filterPressure(self, new_pressure):
        if new_pressure < 1:
            median_length = 5
        elif new_pressure <10:
            median_length = 9
        elif new_pressure < 100:
            median_length = 7
        else: 
            median_length = 3

        self.pressure_buffer.append(new_pressure)
        if len(self.pressure_buffer)>median_length:
            self.pressure_buffer.pop(0)
        if len(self.pressure_buffer)==median_length:
            return sorted(self.pressure_buffer)[1]
        else:
            return new_pressure

    def getPressure(self):
        if self.pressure:
            self.oldpressure = self.pressure
        pressure = self._readPressure()
        counter = 0
        while pressure is None and counter < 20:
            pressure = self._readPressure()
            counter += 1
            time.sleep(0.01)
        if pressure is None:
            print("Kritischer Fehler: Antwort vom Sensor auch nach 20 versuchen nicht sauber")
            self.pressure_Error = True
            return None
        
        self.SensorwahlmitHysterese(pressure)
        self.maxFehlerBestimmung()
        return self.pressure
    
    def SensorwahlmitHysterese(self, pressure):
        if pressure[0]>= 1.3: # ab >= 1mBar immer sensor 1 verwenden
            temp_pressure = pressure[0] #round(self.pressure[0], 2) #round(hp_smooth, 2)
            self.untere_hysterese = False
            self.obere_hysterese = False
            self.sensorwahl = "HP sensor"
        elif pressure[1]< 1.0: #ab <1mBar immer sensor 2 verwenden
            temp_pressure = pressure[1]
            self.obere_hysterese = False
            self.untere_hysterese = False
            self.sensorwahl = "LP sensor"
        elif self.untere_hysterese == True:
            temp_pressure = pressure[1]
            self.sensorwahl = "LP sensor"
        elif self.obere_hysterese == True:
            temp_pressure = pressure[0]
            self.sensorwahl = "HP sensor"
        elif pressure[1] >= 1.0 and self.oldpressure < pressure[1] and self.oldpressure < 1.0: #wenn man von < 1.0 mBar kommt und < 1.3 mBar ist. -> sensor 2 verwenden
            temp_pressure = pressure[1]
            self.untere_hysterese = True
            self.sensorwahl = "LP sensor"
        elif pressure[0] < 1.3 and self.oldpressure >= pressure[0] and self.oldpressure >=1.3: #wenn man von > 1.3 mBar kommt und > 1.0 mBar ist. -> sensor 1 verwenden
            temp_pressure = pressure[0]
            self.obere_hysterese = True
            self.sensorwahl = "HP sensor"
        else:
            temp_pressure = pressure[0]
            self.sensorwahl = "HP sensor"
        if temp_pressure <=0:
            temp_pressure = 1e-4
        #hier wird noch gefiltert damit es keine messfehler wie signalrauschen eine instabilität in die regelung wirft
        temp_pressure = self._filterPressure(temp_pressure)
        self.pressure = temp_pressure
    
    def maxFehlerBestimmung(self):
        if self.pressure < 7.5 * 1e-4:
            fehler_grenze = 0.02
        elif self.pressure < 1e-3:
            fehler_grenze = 0.0134
        elif self.pressure < 2.5*1e-3:
            fehler_grenze = 0.01
        elif self.pressure < 5*1e-3:
            fehler_grenze = 0.004
        elif self.pressure < 7.5*1e-3:
            fehler_grenze = 0.002
        elif self.pressure < 1e-2:
            fehler_grenze = 0.0015
        elif self.pressure >= 1*1e-2 and self.pressure < 5*1e-1:
            fehler_grenze = 0.001
        elif self.pressure >= 5*1e-1 and self.pressure < 7.5*1e-1:
            fehler_grenze = 0.02
        elif self.pressure >= 7.5 * 1e-1 and self.pressure < 1.0:
            fehler_grenze = 0.014
        elif self.pressure >= 1.0 and self.pressure < 2.5:
            fehler_grenze = 0.01
        elif self.pressure >= 2.5 and self.pressure < 5:
            fehler_grenze = 0.004
        elif self.pressure >= 5 and self.pressure < 7.5:
            fehler_grenze = 0.002
        elif self.pressure >= 7.5 and self.pressure < 10:
            fehler_grenze = 0.0014
        elif self.pressure >= 10:
            fehler_grenze = 0.001   
        self.fehler_grenze = fehler_grenze
        self.rel_fehler_grenze = self.fehler_grenze * 5

if __name__ == "__main__":
    sensor = PressureSensor() 
    if sensor.connect():
        try:
            end_time = time.time() + 10  # Lese den Druck für 10 Sekunden
            while time.time() < end_time:
                pressure = sensor.getPressure()
                print(f"Aktueller Druck: {pressure} mBar")
                #time.sleep(0.09)  # Warte 1 s zwischen den Messungen
        finally:
            sensor.disconnect()