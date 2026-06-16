import serial
import serial.tools.list_ports
import time


class PressureSensor:
    FIRST_CONSTANT = 15

    def __init__(self, port=None, baudrate = 38400, timeout = 1):
        self.port = port
        self.ser = None
        self.baudrate = baudrate
        self.timeout = timeout   
        self.old_pressure = 1000
        self.untere_hysterese = False
        self.obere_hysterese = False
        self.pressure = 1000
        self.pressure_Error = False
        self.response_array = []
        self.fehler_grenze = None

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
            self.find_device()
        if self.port is None:
            print("Kein gültiger Port gefunden. Verbindung fehlgeschlagen.")
            return False
        
        try:
            self.ser = serial.Serial(port=self.port, baudrate = self.baudrate, timeout = self.timeout)
            print(f"Erfolgreich mit {self.port} verbunden.")
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
            raw = self.ser.readline()
            resp = raw.decode('utf-8', errors='ignore').strip()
            if resp:
                values = resp.split(",")
                pressure = [float(values[1]), float(values[3])]
                self.response_array.append(resp)
                return pressure 
        except Exception as e :
                self.ser.flushInput()
        return None
        
    def getPressure(self):
        if self.pressure:
            self.oldpressure = self.pressure
        pressure = self._readPressure()
        counter = 0
        while pressure is None and counter < 20:
            pressure = self._read_pressure()
            counter += 1
            time.sleep(0.1)
        if pressure is None:
            print("Kritischer Fehler: Antwort vom Sensor auch nach 20 versuchen nicht sauber")
            self.pressure_Error = True
            return None
        
        self.SensorwahlmitHysterese(pressure)
        self.maxFehlerBestimmung()
        return self.pressure
    
    def SensorwahlmitHysterese(self, pressure):
        if pressure[0]>= 1.0: # ab >= 1mBar immer sensor 1 verwenden
            self.pressure = pressure[0] #round(self.pressure[0], 2) #round(hp_smooth, 2)
            self.untere_hysterese = False
            self.obere_hysterese = False
        elif pressure[1]< 0.5: #ab <0.5mBar immer sensor 2 verwenden
            self.pressure = pressure[1]
            self.obere_hysterese = False
            self.untere_hysterese = False
        elif self.untere_hysterese == True:
            self.pressure = pressure[1]
        elif self.obere_hysterese == True:
            self.pressure = pressure[0]
        elif pressure[1] >= 0.5 and self.oldpressure < pressure[1] and self.oldpressure < 0.5: #wenn man von < 0.5mBar kommt und < 1.0mBar ist. -> sensor 2 verwenden
            self.pressure = pressure[1]
            self.untere_hysterese = True 
        elif pressure[0] < 1.0 and self.oldpressure >= pressure[0] and self.oldpressure >=1.0: #wenn man von > 1.0mBar kommt und > 0.1mBar ist. -> sensor 1 verwenden
            self.pressure = pressure[0]
            self.obere_hysterese = True
        else:
            self.pressure = pressure[0]
        if self.pressure <=0:
            self.pressure = 1e-4
    
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

if __name__ == "__main__":
    sensor = PressureSensor() 
    if sensor.connect():
        try:
            time = time.time() + 10  # Lese den Druck für 10 Sekunden
            while time.time() < time: 
                pressure = sensor.getPressure()
                print(f"Aktueller Druck: {pressure} mBar")
                time.sleep(1)  # Warte 1 s zwischen den Messungen
        finally:
            sensor.disconnect()