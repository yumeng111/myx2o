import pyvisa
from ThorlabsPM100 import ThorlabsPM100
import time
import numpy as np
import math
import matplotlib.pyplot as plt

def configure(avg_count=10):
    global connected
    global rm    
    rm = pyvisa.ResourceManager()
    rm.list_resources()
    inst = rm.open_resource('USB0::0x1313::0x8076::M00819707::0::INSTR', read_termination='\n')
    
    inst.query("*IDN?")
    global power_meter 
    power_meter = ThorlabsPM100(inst=inst)
    global avg
    avg = avg_count

    print("Set average count to: ", avg)
    power_meter.sense.average.count = avg_count
    power_meter.sense.power.dc.range.auto = "ON"

    print("Measurement type :", power_meter.getconfigure)
    print("Wavelength       :", power_meter.sense.correction.wavelength)
    connected = True
    
def disconnect():
    connected = False
    rm.close()

def measure(units="W"): 
    if units == "dBm":
        return 10*math.log(power_meter.read*1000, 10)
    else: 
        return power_meter.read * 1000000
         

def multi_measure(iterations, sleep=0, units="W"): #iterations is how many times you want to run the configure function, sleep in seconds of sleep between each reading, units are in microWatts or dBm 
    print("Making %d measurements..."%(iterations))
    start_time = time.time() #Necessary to determine time in the configure function
    global unit
    if units == "dBm":
        unit = "dBm"
    elif units == "W":
        unit = "\u03BCW"
    else: 
        print("Unknown units, use W or dBm. Using \u03BCW")
        unit = "\u03BCW" 

    global iteration
    iteration = iterations
    global power_array 
    power_array = np.array([])
    global measurement_array 
    measurement_array = np.empty((0, 2), int)

    for i in range(iterations):
        _time = time.time() - start_time
        measurement = [_time, measure(unit)] 
        power_array = np.append(power_array, measurement[1])
        measurement_array = np.append(measurement_array, np.array([measurement]), axis=0)
        time.sleep(sleep)

    return measurement_array

def to_csv():
    np.savetxt(fname = '%d_iterations_at_%d_avg_each_ThorlabsPM100.csv' %(iteration, avg), X = measurement_array, delimiter = ' ') #We should also consider something that will change the name of the files (csv, plot, and hist) so that old files don't get replaced with new files (eg '%d_iterations_at_%d_avg_ThorlabsPM100_v%d.csv' %(iteration, avg, <version #>))

def plot_data():
    fig = plt.figure()
    x = np.linspace(measurement_array[0][0], measurement_array[len(power_array)-1][0], len(power_array))
    plt.plot(x, power_array)
    if unit == "W":
        plt.ylabel("Power (\u03BCW)")
    elif unit == "dBm":
        plt.ylabel("Power (dBm)")
    plt.xlabel("Time (s)")
    fig.savefig('/home/cscdev/Kyla/plots/%d_iterations_at_%d_avg_each_plot.png' %(iteration, avg))
    plt.show()

def histogram():
    fig = plt.figure()
    plt.hist(power_array)
    plt.xlabel("Power (\u03BCW)")
    fig.savefig('/home/cscdev/Kyla/plots/%d_iterations_at_%d_avg_each_histogram.png' %(iteration, avg))
    plt.show()
    
def mean():
    return np.mean(power_array)

def median():
    return np.median(power_array)

if __name__ == '__main__': 
    configure(avg_count=5)
    multi_measure(50, 0, "dBm")
    multi_measure(50, 0, "W")
    print("Mean Power: ", mean(), unit)
    print("Median Power: ", median(), unit)
    disconnect()
    






