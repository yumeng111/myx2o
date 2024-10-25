import pyvisa
import time
import rpyc
import csv
import sys
import os
import serial
import numpy as np

X2O_IP = "10.0.0.11" # X2O v1
#X2O_IP = "10.0.0.13" # X2O v2
X2O_PORT = 12333
X2O_FIRMWARE_FILE = "/root/gem/0xbefe/scripts/resources/x2o_ge21.bit"

SCOPE_VISA_ADDR = "TCPIP0::10.0.0.150::inst0::INSTR"
MEAS_POPULATION_SIZE = 8000000
GAIN = 460  #V/W used to convert volts to power

MEASUREMENTS = [
"TIE"
]

TESTS = MEASUREMENTS + ["POWER", "ER", "OMA"]


def collect_tx_vars(measurements = MEASUREMENTS):
   
    #---Clear DPOJET---
    scope.write(":DPOJET:CLEARALLMEAS")
	
    #---Add Measurements---
    for MEAS in measurements:
        scope.write(f":DPOJET:ADDMEAS {MEAS}")
 
    #---Collect Measurements---
    results = measure(scope)

    #---Format, Print, and Return---
    #print(results)

    return results


def measure(scope):
    scope.write(':DPOJET:STATE CLEAR')
    scope.write(':DPOJET:STATE RUN')
    time.sleep(1)

    # run the scope for some time to collect data
    t1 = time.time()
    while "RUN" in scope.query(":DPOJET:STATE?"):
        time.sleep(2)
        cur_pop = visa_int(scope.query(":DPOJET:MEAS1:RESULTS:ALL:POPULATION?"))
        if cur_pop < MEAS_POPULATION_SIZE:
            #print(f"Running:  {cur_pop} out of {MEAS_POPULATION_SIZE}")
            continue
        else:
            #print(f"Complete: final population of {cur_pop}")
            scope.write(":DPOJET:STATE STOP")
            time.sleep(1)

    t2 = time.time()
    #print("SCOPE_MEASURE DONE, took %fs" % (t2 - t1))

    results = {}    
    #record measurements
    for i in range(len(MEASUREMENTS)):
        #record mean
        results[MEASUREMENTS[i]] = []
        #results[MEASUREMENTS[i]].append(("mean", visa_float(scope.query(f":DPOJET:MEAS{i+1}:RESULTS:ALL:MEAN?"))))
        #results[MEASUREMENTS[i]].append(("stddev", visa_float(scope.query(f":DPOJET:MEAS{i+1}:RESULTS:ALL:STDDEV?"))))
        #results[MEASUREMENTS[i]].append(("max", visa_float(scope.query(f":DPOJET:MEAS{i+1}:RESULTS:ALL:MAX?"))))
        results[MEASUREMENTS[i]].append(("p-p", visa_float(scope.query(f":DPOJET:MEAS{i+1}:RESULTS:ALL:PK2PK?"))))
    return results


def visa_float(visa_response):
    return float(remove_endline(visa_response))


def visa_int(visa_response):
    return int(remove_endline(visa_response))


def remove_endline(str):
    return str.replace("\n", "")


if __name__ == "__main__":
    print("Connecting to RPI (VOA)")
    conn_rpi = rpyc.classic.connect("10.0.0.100", "12333")
    voa = conn_rpi.modules["voa"] 
    voa.configure()
 
    print("Opening connection to the scope")
    
    #---Connect to the Scope---
    rm = pyvisa.ResourceManager()
    scope = rm.open_resource(SCOPE_VISA_ADDR)
    scope.timeout = 100000
    print(scope.query("*IDN?"))
	
    #---Launch DPOJET---
    scope.write("APPLICATION:ACTVATE DPOJET")
    time.sleep(5)
    
    scope.write(":DPOJET:CLEARALLMEAS")
    voa.attenuate(0)
    time.sleep(2)

    meas_lst = []
  
    for att in np.linspace(0, 14, 25):
        print(f"Test at {att} dB attenuation and {0.3-att} dBm power:")
        voa.attenuate(att)   
        time.sleep(2) 
        scope_measurements = collect_tx_vars()
        meas_lst.append(scope_measurements["TIE"][0][1])
        print(scope_measurements["TIE"][0][1], "\n")

    #write results to csv
    with open("VTRX_sat_me0.csv", "w") as f:
        wr = csv.writer(f)
        wr.writerow(meas_lst)

    print("")
    print("ALL DONE!")
    print("Close scope connection")
    scope.close()
    rm.close()











