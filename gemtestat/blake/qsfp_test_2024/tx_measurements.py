import pyvisa
import time
import math

X2O_IP = "10.0.0.11" # X2O v1
#X2O_IP = "10.0.0.13" # X2O v2
X2O_PORT = 12333

SCOPE_VISA_ADDR = "TCPIP0::10.0.0.150::inst0::INSTR"
MEAS_POPULATION_SIZE = 30000 # change to 1M for actual test
GAIN = 460  #V/W used to convert volts to power

#lst of the measurements to be collected
MEASUREMENTS = [
"HIGH",
"LOW",
"WIDTH",
"WIDTHBER",
"TIE",
"DJ",
"RJ",
"TJBER"]

# add the calculated values to the measure list
TESTS = MEASUREMENTS + ["POWER", "ER", "OMA"]


#================= Helper Functions ==================
def visa_float(visa_response):
    return float(remove_endline(visa_response))

def visa_int(visa_response):
    return int(remove_endline(visa_response))

def remove_endline(str):
    return str.replace("\n", "")
#====================================================


def collect_tx_vars(measurements = MEASUREMENTS):
    """ Top level script to launch the scope software, select measurements, and collect sufficient statistics
    """    
    #---Connect to the Scope---
    rm = pyvisa.ResourceManager()
    scope = rm.open_resource(SCOPE_VISA_ADDR)
    scope.timeout = 100000
    #print(scope.query("*IDN?")) #this command can be used to read the state of the scope  (RUN, STOP, etc)
	
    #---Launch DPOJET---
    scope.write("APPLICATION:ACTVATE DPOJET") #DPOJET is the software tool for collecting measurements (on scope)
    time.sleep(5)
   
    #---Clear DPOJET---
    scope.write(":DPOJET:STATE STOP")
    scope.write(":DPOJET:CLEARALLMEAS")
	
    #---Add Measurements---
    for MEAS in measurements:
        scope.write(f":DPOJET:ADDMEAS {MEAS}")
 
    #---Collect Measurements---
    results = measure(scope)

    #---Calculate Remaining Measurements---
    power = abs((results["HIGH"] + results["LOW"])/2) / GAIN
    if(results["LOW"] == 0):
        ER = float("inf")
    else:
        ER = abs(results["HIGH"] / results["LOW"])    
        ER = 20*math.log10(ER) if ER else float("-inf") #convert ER to db
    OMA = (results["HIGH"] - results["LOW"]) / GAIN       
    OMA = 20*math.log10(OMA) if OMA else float("-inf") #convert OMA to db
    
    results["POWER"] = power
    results["ER"] = ER
    results["OMA"] = OMA

    #---and Return---
    scope.close()
    rm.close()

    return results


def measure(scope):
    """ Called by collect_tx_vars to run the data collection for a set population size
    """
    #clear the scope data, and restart
    scope.write(':DPOJET:STATE CLEAR')
    scope.write(':DPOJET:STATE RUN')
    time.sleep(1)

    # run the scope for some time to collect data
    while "RUN" in scope.query(":DPOJET:STATE?"):
        time.sleep(2)
        cur_pop = visa_int(scope.query(":DPOJET:MEAS1:RESULTS:ALL:POPULATION?"))
        # if the population has been met, STOP
        if cur_pop >= MEAS_POPULATION_SIZE:
            scope.write(":DPOJET:STATE STOP")
            time.sleep(1)
 
    results = {}    
    #record all measurements
    for i in range(len(MEASUREMENTS)):
        # for each item in the measurement list, record the mean 
        results[MEASUREMENTS[i]] = visa_float(scope.query(f":DPOJET:MEAS{i+1}:RESULTS:ALL:MEAN?"))

    return results


if __name__ == "__main__":
    scope_measurements = collect_tx_vars()

