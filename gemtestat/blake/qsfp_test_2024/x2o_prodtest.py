#libraries
import rpyc
import time
import sys
from termcolor import colored
import xml.etree.ElementTree as ET
import time

#external files
from tx_measurements import collect_tx_vars
from rx_measurements import collect_rx_vars, find_attenuation_threshold

X2O_IP = "10.0.0.11"
SPEC_POWER = -11.1
EXTENDED_POWER = -12.5

# switch map and indexes TODO: match with physical network (when attenuation boxes are done)
TX_SWITCH_MAP = {}
chan_cnt = 0
for i in range(30):
    TX_SWITCH_MAP[i] = []
    for j in range(1,5):
        TX_SWITCH_MAP[i].append(chan_cnt)
        chan_cnt += 1

RX_SWITCH_MAP = TX_SWITCH_MAP
RX_OPM_INDEX = 63
TX_OPM_INDEX = 5
SCOPE_INDEX = 7

#========== Classes ======================================
# struct for RX channel
class QSFP_RX_CHAN:
    
    def __init__(self, id):
        self.data_spec = {}
        self.data_extended = {}
        self.id = id

    def measure(self, chan, att, opm, switch, voa, rw, x2o_gbt, x2o_utils, att_type = "spec"):
        if(att_type == "spec"):
            self.data_spec = collect_rx_vars(chan, opm, switch, rw, x2o_gbt, x2o_utils)
        else:
            self.data_extended = collect_rx_vars(chan, opm, switch, rw, x2o_gbt, x2o_utils)

    def __str__(self):
        ret_str = str(f"Spec Attenuation: {self.data_spec}\nExtended Attenuation: {self.data_extended}")
        return ret_str

# struct for TX channel
class QSFP_TX_CHAN:

    def __init__(self, id):
        self.data = {}
        self.id = id


    def measure(self):
        self.data = collect_tx_vars()


    def __str__(self):
        return str(self.data)


# struct for QSFP, contains 4 RX channels and 4 TX channels
class QSFP:
    
    def __init__(self, id):	
        self.data = {}
        self.id = id
        self.cage_num = id
        self.RX_channels = [QSFP_RX_CHAN(i+1) for i in range(4)]
        self.TX_channels = [QSFP_TX_CHAN(i+1) for i in range(4)]
            
    def __str__(self):
        ret_str = str(self.data) + "\n"
        ret_str += "TX Channels:\n"
        for chan in self.TX_channels:
            ret_str += str(chan) + "\n"
        ret_str += "\nRX Channels:"
        for chan in self.RX_channels:
            ret_str += str(chan) + "\n" 
        return ret_str        


# this class collects various voltage, current, and temperatures from x2o FPGA
class FPGA_MONITOR:

    #FPGA_MONITOR must be given the status (off, programmed, etc.) and object to call monitor()
    def __init__(self, x2o_monitor, FPGA_status):
        #when the class is initialized, the data will be collected
        self.data = x2o_monitor.monitor()
        self.status = FPGA_status

    #return the data formatted for output as df
    def monitor(self, data):
        mon_data = self.data
        #put monitor data and status together in df
        return mon_data

    def check_data(self): #TODO: Verify all values
        if(self.data["3V3_STANDBY"]["V"] > 3.3*0.98 or self.data["3V3_STANDBY"]["V"] < 3.3*1.02):
            print(colored("PASS", "green"))
        else:
            print(colored("FAIL", "red"))

    def __str__(self):
        return str(self.data)

#========================================================



#========= Functions ====================================

def configure():
    # Connect to X2O
    conn_x2o = rpyc.classic.connect(X2O_IP, "12333")
    conn_x2o._config["sync_request_timeout"] = None

    # X2O Modules
    x2o_monitor = conn_x2o.modules["boards.x2o.monitor"]
    conn_x2o.execute("import os")
    rw = conn_x2o.modules["common.rw_reg"]
    rw.parse_xml()
    x2o_utils = conn_x2o.modules["common.utils"]
    x2o_gbt = conn_x2o.modules["gem.gbt"]
    x2o_optics = conn_x2o.modules["boards.x2o.optics"]

    # Connect to RPI
    conn_rpi = rpyc.classic.connect("10.0.0.100", port="12333")
    conn_rpi._config['sync_request_timeout'] = None

    # Configure OPMs TODO: eliminate need for try statement, add all 3 OPMS
    opm = conn_rpi.modules["measure_power"]
    try:
        opm.configure(avg_count=1) # configures power meter, avg_count is number of readings
    except:
        opm.disconnect()
        opm.configure(avg_count=1)

    # Configure Switches
    switch = conn_rpi.modules["optical_switch"]
    rx_switch1 = switch.configure("ttyUSB0")
    #TODO: add all switches, verify each device file
    #tx_switch2 = switch.configure("ttyUSB1")
    #rx_source_switch1 = switch.configure("ttyUSB2")
    #tx_switch2 = switch.configure("ttyUSB3")
    #rx_source_switch2 = switch.configure("ttyUSB4")
    #tx_dest_switch = switch.configure("ttyUSB5")

    # VOA configuration TODO: add second VOA
    voa = conn_rpi.modules["voa"]
    voa.configure()
    
    #TODO: return new components voa2, switches
    return conn_rpi, conn_x2o, rx_switch1, opm, voa, x2o_monitor, rw, x2o_utils, x2o_gbt, x2o_optics  

#========================================================



#========= Main Loop ====================================
if __name__ == "__main__":    
  
    #TODO: User may need to pass in the test starting point

    #COMMAND: python3 x2o_prodtest.py [cages] subsystem serialnum
    #---get command line args---
    CAGES_UNDER_TEST = list(eval(sys.argv[1]))
    subsystem = sys.argv[2]
    if(subsystem not in ["me0", "ge21", "dmb", "odmb7", "dth"]):
        print(f"{subsystem} is invalid. Select from me0, ge21, dmb, odmb7, dth")
        sys.exit()

    print(f"STARTING X2O PRODUCTION TESTING:")
    print(f"Frontend Board: {subsystem}")
    print(f"Cages: {CAGES_UNDER_TEST}")
 
    #---configure modules and components---
    print("Starting module configuration.")
    conn_rpi, conn_x2o, switch, opm, voa, x2o_monitor, rw, x2o_utils, x2o_gbt, x2o_optics = configure()
            	
    input(f"25 Gb Test. Ensure all 100G QSFPs are plugged in for loopback testing. PRESS ENTER:")
    # TODO loopback tests
    # load firmware
    # check BER
    input(f"Automoatic testing. Ensure the correct QSFPs for the {subsystem} board are plugged in. PRESS ENTER:")
    

    # TEST PROCEDURE BEGINS
    # rx_source switch TODO: connect to actual switch
    switch_index = ["me0", "ge21", "dmb", "odmb7", "dth"].index(subsystem) 
    #set the source switch
    #TODO: rx_source_switch.select_chan(switch_index+1)
    # tx_dest switch
    TX_DEST_INDEX = switch_index+1
    #TODO: tx_dest_switch.select_chan(TX_DEST_INDEX)
    #TODO: program firmware and init backend. Need X2O v2, currently this is done before x2o_prodtest.py is ran

    #*********X2O General***********
    # serial number
    x2o_serial = sys.argv[3]
    # notes
    

    #********Power Module**********
    # TODO: collect the following vars
    # serial number
    # 12 V rail
    
    
    #*********Kria Module**********
    # TODO: collect the following vars
    # serial number
    # FPGA DNA Code, via JTAG


    #********Optical Module********
    # TODO: collect the following vars
    # Serial number

    # List of QSFPs
    # opticmod objects
    optics_qsfps = x2o_optics.x2o_get_qsfps()     
    # python objects
    qsfp_lst = []
    for i in CAGES_UNDER_TEST:
        qsfp_dataobj = optics_qsfps[i]
        qsfp_dataobj.select()
        qsfp = QSFP(i)
        qsfp.data["QSFP_NUMBER"] = "NA" 
        qsfp.data["type"] = qsfp_dataobj.identifier().replace(" or later", "") 
        qsfp.data["vendor"] = qsfp_dataobj.vendor() 
        qsfp.data["part_num"] = qsfp_dataobj.part_number()  
        qsfp.data["serial"] = qsfp_dataobj.serial_number()
        qsfp.data["voltage"] = qsfp_dataobj.voltage() 
        qsfp.data["spec_temp"] = 0 
        qsfp.data["extended_temp"] = 0
        qsfp_lst.append(qsfp)

 
    #************QSFPs*************
    print("\nCollecting QSFP data.")

    # --TX--
    """
    print("\nTransmiters:")
    voa.attenuate(0)
    #TODO: add physical switch. tx_dest_switch.select_chan(SCOPE_INDEX) #set destination to scope
    for qsfp in qsfp_lst:
        # loop through each TX channel in qsfp
        for chan in range(4):
            print(f"Cage {qsfp.cage_num}, chan {chan}")
            # switching
            #TODO: add physical switch. tx_switch.select_channel(TX_SWITCH_MAP[qsfp.cage_num][chan])
            # measure
            qsfp.TX_channels[chan].measure()
    """
    #TODO: add switch. tx_dest_switch.select_chan(TX_DEST_INDEX) #set destination to frontend board 

    # --RX--
    print("\nRecievers")
    for qsfp in qsfp_lst:
        qsfp_dataobj = optics_qsfps[qsfp.cage_num]
        qsfp_dataobj.select()

        # find the attenuation required for spec and extended power on this qsfp
        spec_att = 0 #find_attenuation_threshold(opm, switch, voa, SPEC_POWER)
        extended_att = 0 #find_attenuation_threshold(opm, switch, voa, EXTENDED_POWER)

        # loop through each RX channel in qsfp
        for chan in range(4):
            voa.attenuate(0)
            # switching
            #TODO: add physical. switch rx_switch.select_chan(RX_SWITCH_MAP[qsfp.cage_num][chan-1])             
            switch.select_chan(chan+1) #this switch is temporarily being used for testing

            # --RX--
            # BER @ spec att 
            voa.attenuate(spec_att)
            time.sleep(0.5)
            qsfp.RX_channels[chan].measure(chan+1, spec_att, opm, switch, voa, rw, x2o_gbt, x2o_utils, "spec")
            #spec temp
            qsfp.data["spec_temp"] += qsfp_dataobj.temperature() 
                
            # BER @ extended att
            voa.attenuate(extended_att)
            time.sleep(0.5)
            qsfp.RX_channels[chan].measure(chan+1, extended_att, opm, switch, voa, rw, x2o_gbt, x2o_utils, "ext")
            #extended temp
            qsfp.data["extended_temp"] += qsfp_dataobj.temperature() 
            

    #*********FPGA Module************ 
    voa.attenuate(0)
    time.sleep(1)

    print("FPGA Monitor with power down")
    # power down
    conn_x2o.modules["boards.x2o.power_down"].power_down()
    time.sleep(2)
    FPGA_off = FPGA_MONITOR(x2o_monitor, "OFF")
    #pass/fail
    FPGA_off.check_data()    

    # power on
    #print("Unprogrammed FPGA Monitor")
    conn_x2o.modules["boards.x2o.power_up"].power_up()
    time.sleep(2)
    FPGA_unprogrammed = FPGA_MONITOR(x2o_monitor, "UNPROGRAMMED")
    FPGA_unprogrammed.check_data() 
    
    #programmed
    print("Programmed FPGA Monitor")
    print("FPGA being programmed...")
    conn_x2o.modules["boards.x2o.program_fpga"].program_fpga()
    #TODO: init_backend, need the x2o v2
    time.sleep(2)
    FPGA_programmed = FPGA_MONITOR(x2o_monitor, "PROGRAMMED")    
    FPGA_programmed.check_data()  
    time.sleep(1)

    # compile FPGA data
    fpga_data = [FPGA_off, FPGA_unprogrammed, FPGA_programmed] #TODO: add FPGA 25Gb   




    #**********Transform data into XML************
    #TODO: file location and directory creation
    # ex: save to ~/{serial}/{timestamp}/prodtest_data.xml
    filepath = "x2o_test.xml"
    # TODO: fill in all missing variables below. will require x2o v2
    data = ET.Element("X2O") #create main data element

    #---x2o data---
    ET.SubElement(data, "serial").text = x2o_serial
    ET.SubElement(data, "subsystem").text = subsystem     
    ET.SubElement(data, "notes").text = "NA"
 
    #other x2o modules
    power_mod = ET.SubElement(data, "power_module")
    kria_mod = ET.SubElement(data, "kria_module")
    optic_mod = ET.SubElement(data, "optical_module")
    fpga_mod = ET.SubElement(data, "FPGA_module")

    #---module data---
    # power module
    ET.SubElement(power_mod, "powermod_serial").text = "NA"     
    ET.SubElement(power_mod, "powermod_12V").text = "NA" 
    
    # kria module
    ET.SubElement(kria_mod, "kria_serial").text = "NA" 
    ET.SubElement(kria_mod, "kria_DNA").text = "NA" 

    # optic module
    ET.SubElement(optic_mod, "opticmod_serial").text = "NA" 
    qsfps = ET.SubElement(optic_mod, "opticmod_QSFPs") 
    
    # fpga module
    ET.SubElement(fpga_mod, "FPGA_serial").text = "NA" 
    ET.SubElement(fpga_mod, "FPGA_DNA").text = "NA" 

    fpga_off = ET.SubElement(fpga_mod, "FPGA_monitor_off") 
    fpga_unprogrammed = ET.SubElement(fpga_mod, "FPGA_monitor_unprogrammed") 
    fpga_programmed = ET.SubElement(fpga_mod, "FPGA_monitor_programmed") 
    fpga_25gb = ET.SubElement(fpga_mod, "FPGA_monitor_25Gb")

    ET.SubElement(fpga_mod, "FPGA_25Gb_BER").text = "NA" 
    ET.SubElement(fpga_mod, "FPGA_25Gb_eyescan").text = "NA" 
    ET.SubElement(fpga_mod, "FPGA_25Gb_temperatures").text = "NA" 
    ET.SubElement(fpga_mod, "FPGA_slow_BER").text = "NA" 
    
    # Get FPGA Monitor Elements
    cnt = 0
    for fpga_mon in [fpga_off, fpga_unprogrammed, fpga_programmed]:
        # fpga data
        cur_fpga_data = fpga_data[cnt].data
        
        ET.SubElement(fpga_mon, "status").text = fpga_data[cnt].status

        ET.SubElement(fpga_mon, "V_12V0").text = str(cur_fpga_data["12V0"]) 
        ET.SubElement(fpga_mon, "V_0V85_VCCINT_VUP").text = str(cur_fpga_data["0V85_VCCINT_VUP"]["V"])
        ET.SubElement(fpga_mon, "I_0V85_VCCINT_VUP").text = str(cur_fpga_data["0V85_VCCINT_VUP"]["I"]) 
        ET.SubElement(fpga_mon, "T_loc_0V85_VCCINT_VUP").text = str(cur_fpga_data["0V85_VCCINT_VUP"]["T"][0]) 
        ET.SubElement(fpga_mon, "T_ext_0V85_VCCINT_VUP").text = str(cur_fpga_data["0V85_VCCINT_VUP"]["T"][1]) 

        ET.SubElement(fpga_mon, "V_0V9_MGTAVCC_VUP_S").text = str(cur_fpga_data["0V9_MGTAVCC_VUP_S"]["V"]) 
        ET.SubElement(fpga_mon, "I_0V9_MGTAVCC_VUP_S").text = str(cur_fpga_data["0V9_MGTAVCC_VUP_S"]["I"]) 
        ET.SubElement(fpga_mon, "T_loc_0V9_MGTAVCC_VUP_S").text = str(cur_fpga_data["0V9_MGTAVCC_VUP_S"]["T"][0]) 
        ET.SubElement(fpga_mon, "T_ext_0V9_MGTAVCC_VUP_S").text = str(cur_fpga_data["0V9_MGTAVCC_VUP_S"]["T"][1]) 

        ET.SubElement(fpga_mon, "V_0V9_MGTAVCC_VUP_N").text = str(cur_fpga_data["0V9_MGTAVCC_VUP_N"]["V"]) 
        ET.SubElement(fpga_mon, "I_0V9_MGTAVCC_VUP_N").text = str(cur_fpga_data["0V9_MGTAVCC_VUP_N"]["I"]) 
        ET.SubElement(fpga_mon, "T_loc_0V9_MGTAVCC_VUP_N").text = "NA"
        ET.SubElement(fpga_mon, "T_ext_0V9_MGTAVCC_VUP_N").text = "NA"

        ET.SubElement(fpga_mon, "V_1V2_MGTAVCC_VUP_S").text = "NA"#str(cur_fpga_data["1V2_MGTAVCC_VUP_S"]["V"]) 
        ET.SubElement(fpga_mon, "I_1V2_MGTAVCC_VUP_S").text = "NA"#str(cur_fpga_data["1V2_MGTAVCC_VUP_S"]["I"]) 
        ET.SubElement(fpga_mon, "T_loc_1V2_MGTAVCC_VUP_S").text = "NA"#str(cur_fpga_data["1V2_MGTAVCC_VUP_S"]["T"][0]) 
        ET.SubElement(fpga_mon, "T_ext_1V2_MGTAVCC_VUP_S").text = "NA"#str(cur_fpga_data["1V2_MGTAVCC_VUP_S"]["T"][1]) 

        ET.SubElement(fpga_mon, "V_1V2_MGTAVCC_VUP_N").text = ""#str(cur_fpga_data["1V2_MGTAVCC_VUP_N"]["V"]) 
        ET.SubElement(fpga_mon, "I_1V2_MGTAVCC_VUP_N").text = ""#str(cur_fpga_data["1V2_MGTAVCC_VUP_N"]["I"]) 
        ET.SubElement(fpga_mon, "T_loc_1V2_MGTAVCC_VUP_N").text = ""#str(cur_fpga_data["1V2_MGTAVCC_VUP_N"]["T"][0]) 
        ET.SubElement(fpga_mon, "T_ext_1V2_MGTAVCC_VUP_N").text = ""#str(cur_fpga_data["1V2_MGTAVCC_VUP_N"]["T"][1]) 

        ET.SubElement(fpga_mon, "V_1V8_MGTVCCAUX_VUP_S").text = ""#str(cur_fpga_data["1V2_MGTVCCAUX_VUP_S"]["V"]) 
        ET.SubElement(fpga_mon, "V_1V8_MGTVCCAUX_VUP_N").text = ""#str(cur_fpga_data["1V2_MGTVCCAUX_VUP_N"]["V"]) 

        ET.SubElement(fpga_mon, "V_1V8_VCCAUX_VUP").text = str(cur_fpga_data["1V8_VCCAUX_VUP"]["V"]) 
        ET.SubElement(fpga_mon, "I_1V8_VCCAUX_VUP").text = str(cur_fpga_data["1V8_VCCAUX_VUP"]["I"]) 

        ET.SubElement(fpga_mon, "MACHXO2_V").text = str(cur_fpga_data["1V8_VCCAUX_VUP"]["V"]) 

        ET.SubElement(fpga_mon, "V_2V5_OSC_NE").text = str(cur_fpga_data["2V5_OSC_NE"]["V"]) 
        ET.SubElement(fpga_mon, "V_2V5_OSC_NW").text = str(cur_fpga_data["2V5_OSC_NW"]["V"]) 
        ET.SubElement(fpga_mon, "V_2V5_OSC_SE").text = str(cur_fpga_data["2V5_OSC_SE"]["V"]) 
        ET.SubElement(fpga_mon, "V_2V5_OSC_SW").text = str(cur_fpga_data["2V5_OSC_SW"]["V"]) 

        ET.SubElement(fpga_mon, "LMK_SYNTH_V").text = str(cur_fpga_data["3V3_SI5395J"]["V"])

        ET.SubElement(fpga_mon, "INTERMEDIATE_V").text = str(cur_fpga_data["2V7_INTERMEDIATE"]["V"])
        ET.SubElement(fpga_mon, "INTERMEDIATE_I").text = str(cur_fpga_data["2V7_INTERMEDIATE"]["I"]) 
        ET.SubElement(fpga_mon, "INTERMEDIATE_T_loc").text = str(cur_fpga_data["2V7_INTERMEDIATE"]["T"][0])
        ET.SubElement(fpga_mon, "INTERMEDIATE_T_ext").text = str(cur_fpga_data["2V7_INTERMEDIATE"]["T"][1]) 

        ET.SubElement(fpga_mon, "V_3V3_STANDBY").text = str(cur_fpga_data["3V3_STANDBY"]["V"])

        ET.SubElement(fpga_mon, "FPGA_T_loc").text = "NA"
        ET.SubElement(fpga_mon, "FPGA_T_ext").text = "NA"
        cnt += 1

    # Get QSFP elements
    for qsfp in qsfp_lst:
        qsfp_elem = ET.SubElement(qsfps, "QSFP"+str(qsfp.id)) #QSFP data element
        # qsfp data
        qsfp.data["spec_temp"] = qsfp.data["spec_temp"]/4
        qsfp.data["extended_temp"] = qsfp.data["extended_temp"]/4  
        qsfp_data = {key: str(value) for key, value in qsfp.data.items()}
        ET.SubElement(qsfp_elem, "QSFP_NUMBER").text = "NA"
        ET.SubElement(qsfp_elem, "type").text = qsfp_data["type"] 
        ET.SubElement(qsfp_elem, "vendor").text = qsfp_data["vendor"] 
        ET.SubElement(qsfp_elem, "part_num").text = qsfp_data["part_num"] 
        ET.SubElement(qsfp_elem, "serial").text = qsfp_data["serial"] 
        ET.SubElement(qsfp_elem, "voltage").text = qsfp_data["voltage"] 
        ET.SubElement(qsfp_elem, "spec_temperature").text = qsfp_data["spec_temp"]
        ET.SubElement(qsfp_elem, "extended_temperature").text =qsfp_data["extended_temp"]  
        ET.SubElement(qsfp_elem, "cage_num").text = str(qsfp.cage_num) 
        tx_channels = ET.SubElement(qsfp_elem, "tx_channels") 
        rx_channels = ET.SubElement(qsfp_elem, "rx_channels")

        # QSFP TX Channels
        for i in range(4):
            TX_chan = ET.SubElement(tx_channels, "tx_chan"+str(i)) #TX channel data element
            # TX channel data
            chan_data = {key: str(value) for key, value in qsfp.TX_channels[i].data.items()}
            ET.SubElement(TX_chan, "power").text = chan_data["POWER"] 
            ET.SubElement(TX_chan, "bias").text = "NA"     
            ET.SubElement(TX_chan, "extinction_ratio").text = chan_data["ER"]
            ET.SubElement(TX_chan, "optical_modulation_amplitude").text = chan_data["OMA"]     
            ET.SubElement(TX_chan, "total_interval_error").text = chan_data["TIE"] 
            ET.SubElement(TX_chan, "deterministic_jitter").text = chan_data["DJ"] 
            ET.SubElement(TX_chan, "random_jitter").text =chan_data["RJ"] 
            ET.SubElement(TX_chan, "total_jitter").text = chan_data["TJBER"] 
            ET.SubElement(TX_chan, "total_width").text = chan_data["WIDTH"] 
            ET.SubElement(TX_chan, "width_at_BER").text = chan_data["WIDTHBER"]      
            ET.SubElement(TX_chan, "high").text = chan_data["HIGH"] 
            ET.SubElement(TX_chan, "low").text = chan_data["LOW"]  
              
        # QSFP RX Channels
        for i in range(4):
            RX_chan = ET.SubElement(rx_channels, "rx_chan"+str(i)) #RX channel data element
            # RX channel data
            chan_data_spec = {key: str(value) for key, value in qsfp.RX_channels[i].data_spec.items()}
            chan_data_ext = {key: str(value) for key, value in qsfp.RX_channels[i].data_extended.items()}
            ET.SubElement(TX_chan, "spec_power").text = chan_data_spec["POWER"]
            ET.SubElement(TX_chan, "avg_spec_power").text = chan_data_spec["AVG_POWER"]
            ET.SubElement(TX_chan, "extended_power").text = chan_data_ext["POWER"]
            ET.SubElement(TX_chan, "avg_extended_power").text = chan_data_ext["AVG_POWER"]     
            ET.SubElement(TX_chan, "preFEC_BER_spec").text = chan_data_spec["PREFEC_BER"]
            ET.SubElement(TX_chan, "postFEC_BER_spec").text = chan_data_spec["POSTFEC_BER"]
            ET.SubElement(TX_chan, "preFEC_BER_extended").text = chan_data_ext["PREFEC_BER"]
            ET.SubElement(TX_chan, "postFEC_BER_extended").text = chan_data_ext["POSTFEC_BER"] 

    #reset TODO: add init_backend once x2o v2 is in 
    switch.select_chan(1) 
    voa.attenuate(0)

              
tree = ET.ElementTree(data)
tree.write(filepath, encoding="utf-8", xml_declaration=True) 
#========================================================


