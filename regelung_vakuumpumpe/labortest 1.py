#install the driver software NI-DAQ™mx
#install all the necessary libaries and debugger/compiler(python, python debugger, git etc.) to get it running on VS code
#install with py -m pip install nidaqmx in the terminal all the necessary packages
import time
import numpy as np
import nidaqmx


system = nidaqmx.system.System.local()
for dev in system.devices:
    print(dev.name, "-", dev.product_type)
print("neu start:")
with nidaqmx.Task() as task:
    task.ao_channels.add_ao_voltage_chan(f"{"Dev1_MSA"}/ao0")
    task.ao_channels.add_ao_voltage_chan(f"{"Dev1_MSA"}/ao1")
    for i in range(5):
        print("Iteration", i+1)
        task.write([2.5, 4.0])  # Volt
        time.sleep(1.0)
        task.write([5, 6])  # Volt
        time.sleep(1.0)
        task.write([2.5, 8.0])  # Volt
        time.sleep(1.0)
        task.write([8, 10])  # Volt
        time.sleep(1.0)
        task.write([0, 0])  # Volt
        time.sleep(2.0)

print("for-loop beendet.")
input("Enter drücken zum Beenden...")


