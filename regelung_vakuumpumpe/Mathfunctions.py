from scipy.interpolate import PchipInterpolator
import numpy as np

class ControllSystem:
    def __init__(self, kp, ki, kd, sollwert, dt=1.0, ambient_pressure = 1000):
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.dt = dt
        self.sollwert = max(sollwert, 1e-4)
        self.prev_error = 0.0
        self.integral = 0.0
        self.ambient_pressure = ambient_pressure
        self.integral_flag = False
        self.integral_startvalue = self.sollwert + (abs(self.ambient_pressure - self.sollwert) *0.05)
        self.p_anteil = None
        self.i_anteil = None
        self.d_anteil = None

        

    def logarithmicPID(self, istwert):
        
        safe_istwert = max(istwert, 1e-4)
        
        if (safe_istwert < self.integral_startvalue and self.integral_flag == False):
            self.integral_flag = True
        

        error = np.log10(self.sollwert) - np.log10(safe_istwert)
        rel_error = (self.sollwert - istwert) / self.sollwert

        if self.integral_flag == True:
            self.integral += error*self.dt
        else:
            print(f"flag ({self.integral_startvalue}) mBar wurde noch nocht ausgelöst...")
            self.integral = 0    
        derivative = (error - self.prev_error)/self.dt
        self.p_anteil = self.kp*error
        self.i_anteil = self.ki*self.integral
        self.d_anteil = self.kd*derivative
        output = self.p_anteil + self.i_anteil + self.d_anteil
        self.prev_error = error
        return output, rel_error, derivative, self.integral

    def relativePID(self, sollwert, istwert):
        safe_sollwert = max(sollwert, 1e-4)
        safe_istwert = max(istwert, 1e-4)

        rel_error = (safe_sollwert - safe_istwert) / safe_sollwert
        self.integral += rel_error*self.dt    
        derivative = (rel_error - self.prev_error)/self.dt
        output = (self.kp*rel_error)+(self.ki*self.integral)+(self.kd*derivative)
        self.prev_error = rel_error
        return output, rel_error, derivative, self.integral
            
    def reset(self):
        self.prev_error = 0.0
        self.integral = 0.0
        self.integral_flag = False
    

class Interpolation:

    def __init__(self, sollwert):
        self.ventilspannungen = None
        self.druck = None
        self.sollwert = sollwert
        self.v_ein = None
        self.max_steigung = None
        self.druck_bei_max_steigung = None
        self.steigung_v_ein = None
        


    def interpolierte_Funktion(self,ventilspannungen, druck):
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
        
    def x_interpoliert(self, ventilspannungen, druck):
        v_data = np.array(ventilspannungen)
        p_data = np.array(druck)
        idx = np.argsort(v_data)
        v_sorted = v_data[idx]
        p_sorted = p_data[idx]
        v_unique, unique_idx = np.unique(v_sorted, return_index=True)
        p_unique = p_sorted[unique_idx]
        if len(v_unique) > 1:
            x_interp = np.linspace(min(v_unique), max(v_unique), 100)
            pchip = PchipInterpolator(v_unique, p_unique)
            y_pchip = pchip(x_interp)
            return  x_interp, y_pchip
        else:
            print("Fehler bei der Interpolation")
            return None, None

    def steigung(self, ventilspannungen, druck):
        if len(ventilspannungen) > 1:
            x_interp, y_pchip = self.x_interpoliert(ventilspannungen, druck)
            if x_interp is None or y_pchip is None:
                print("Fehler bei der Interpolation. Steigungsberechnung nicht möglich.")
                return None, None

            dp_dv = []
            for i in range(len(x_interp)-1):
                delta_v = x_interp[i+1] - x_interp[i]
                delta_p = y_pchip[i+1] - y_pchip[i]
                sekante = abs(delta_p / delta_v)
                dp_dv.append(sekante)
            
            dp_dv.append(dp_dv[-1])
            
            max_idx = np.argmax(dp_dv)
            self.max_steigung = abs(dp_dv[max_idx])
            max_volt = x_interp[max_idx]
            self.druck_bei_max_steigung = y_pchip[max_idx]

            idx_v_ein = np.abs(x_interp - self.v_ein).argmin()
            self.steigung_v_ein = abs(dp_dv[idx_v_ein])

            print("\n=======================================================")
            print(f"-> Höchste Steigung:  {self.max_steigung:.4f} mBar/V")
            print(f"-> Bei Spannung:      {max_volt:.6f} V")
            print(f"-> Bei Druck:         {self.druck_bei_max_steigung:.4f} mBar")
            print(f"-> Steigung Sollwert: {self.steigung_v_ein:.4f} mBar/V")
            print(f"-> Bei Spannung:      {self.v_ein:.6f} V")
            print(f"-> Bei Druck:         {self.sollwert:.4f} mBar")
        else:
            print("Nicht genügend Datenpunkte für die Steigungsberechnung.")
class Eingabe:
    @staticmethod
    def druckeingabe ():
        sollwert = input("Bitte geben Sie den gewünschten Solldruck in mBar ein: ")
        try:
            return float(sollwert)
        except ValueError:
            print("Ungültige Eingabe. Bitte geben Sie eine Zahl ein.")
            return Eingabe.druckeingabe()

if __name__ == "__main__":
    ...