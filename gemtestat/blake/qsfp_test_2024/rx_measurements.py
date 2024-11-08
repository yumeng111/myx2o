import time
import sys
from termcolor import colored

RPI_IP = "10.0.0.100"
RPI_PORT = 12333
X2O_IP = "10.0.0.11" # X2O v1
#X2O_IP = "10.0.0.13" # X2O v2
X2O_PORT = 12333
SWITCH_OPM_PORT = 5
MAX_ERRORS_ALLOWED = 999999999

# the OH / GBT number on the X2O that is connected to the GBT which is sending the data back to the X2O receivers under test
GE21_TX_OH = 2 # X2O v1
GE21_TX_GBT = 0

ME0_TX_OH = 0 # X2O v1
ME0_TX_GBT = 0

# (oh, gbt) : switch channel
ME0_MAP = {(0, 0) : 1, (0, 1) : 2, (0, 2) : 3, (0, 3) : 4}
GE21_MAP = {(3, 0) : 1, (3, 1) : 2, (2, 0) : 3, (2, 1) : 4}
# map of all frontend board mappings
FE_MAP = {0:ME0_MAP, 2:GE21_MAP}


COARSE_ATT_STEP = 0.5
FINE_ATT_STEP = 0.05

DATA_ROOT_DIR = "/home/gemtest/blake/qsfp_test_2023"
RESULTS_SUMMARY_FILE = DATA_ROOT_DIR + "/results_summary.csv"

source = {
    'QSFP': 'qsfp',
    'VTRX': 'vtrx',
    'VTRX_Plus': 'vtrx_plus',
    'DMB': 'dmb'
} #The keys are the inputs in the command line, the values are used in the function to determine which transmitter will be tested


def gbt_locked(oh, gbt, rw):
    #print("requesting lock status for OH%d GBT%d" % (oh, gbt))
    return rw.read_reg("BEFE.GEM.OH_LINKS.OH%d.GBT%d_READY" % (oh, gbt))


#TODO (not important): change this to the function existing on RPI
def measure_power(opm, num_measure):
    opm.multi_measure(iterations=num_measure, sleep=0.0, units="dBm")
    res = float(opm.median())
    return res


def gbtx_write_reg(global_gbt_idx, addr, value, rw):
    fw_date = rw.read_reg("BEFE.SYSTEM.RELEASE.DATE")
    fw_year = fw_date & 0xffff
    if fw_year < 0x2023:  
        rw.write_reg("BEFE.GEM.SLOW_CONTROL.IC.GBTX_LINK_SELECT", global_gbt_idx)
    else:
        rw.write_reg("BEFE.GEM.SLOW_CONTROL.IC.GBT_LINK_SELECT", global_gbt_idx)
    rw.write_reg("BEFE.GEM.SLOW_CONTROL.IC.ADDRESS", addr)
    rw.write_reg("BEFE.GEM.SLOW_CONTROL.IC.WRITE_DATA", value)
    rw.write_reg("BEFE.GEM.SLOW_CONTROL.IC.EXECUTE_WRITE", 1)
    time.sleep(1)


def gbt_config_loopback(oh, gbt, rw, x2o_gbt, x2o_utils):
    station = rw.read_reg("BEFE.GEM.GEM_SYSTEM.RELEASE.GEM_STATION")
    if station == 2:
        global_gbt_idx = oh * 2 + gbt
        gbtx_write_reg(global_gbt_idx, 29, 0x17, rw)
        gbtx_write_reg(global_gbt_idx, 30, 0x17, rw)
        gbtx_write_reg(global_gbt_idx, 31, 0x17, rw)
    elif station == 0:
        x2o_gbt.initGbtRegAddrs()
        x2o_gbt.selectGbt(oh, gbt)
        gbt_version = x2o_utils.get_config("CONFIG_ME0_GBT_VER")[oh][gbt]
        if gbt_version == 0:
            x2o_gbt.writeGbtRegAddrs(0x119, 0x36) # enable loopback on groups 0 and 1
            x2o_gbt.writeGbtRegAddrs(0x11a, 0x36)  # enable loopback on groups 2 and 3
            x2o_gbt.writeGbtRegAddrs(0x11b, 0x36)  # enable loopback on groups 4 and 5
            x2o_gbt.writeGbtRegAddrs(0x11c, 0x06)  # enable loopback on group 6
        elif gbt_version == 1:
            x2o_gbt.writeGbtRegAddrs(0x129, 0x36)  # enable loopback on groups 0 and 1
            x2o_gbt.writeGbtRegAddrs(0x12a, 0x36)  # enable loopback on groups 2 and 3
            x2o_gbt.writeGbtRegAddrs(0x12b, 0x36)  # enable loopback on groups 4 and 5
            x2o_gbt.writeGbtRegAddrs(0x12c, 0x06)  # enable loopback on group 6
        else:
            print("Unknown LpGBT version %d (should be 0 or 1" % gbt_version)
            sys.exit()
    else:
        print("ERROR: unsupported GEM station = %d" % station)
        # sys.exit()


def gbt_config_prbs(oh, gbt, rw, x2o_gbt, x2o_utils):
    """configure the PRBS signal for a gem frontend
    """
    gbt_config_loopback(oh, gbt, rw, x2o_gbt, x2o_utils)
    rw.write_reg("BEFE.GEM.GEM_SYSTEM.CTRL.GBT_PRBS_TX_EN", 1)
    time.sleep(1)


#currently unused, will be implemented for CSC tests
def odmb_config_prbs():
    links = x2o_fw_utils.befe_get_all_links()
    x2o_prbs.prbs_control(links, 5) # turn on PRBS31 mode on all links


def read_link_errors_gem(oh, gbt, err_measure_time, rw):
    """ Called by measure_BER to collect the number of errors over a period of PRBS bits
    """
    time.sleep(5)
    rw.write_reg("BEFE.GEM.GEM_SYSTEM.CTRL.LINK_RESET", 1)
    starting_time = time.time()
    while time.time() < starting_time + err_measure_time:
        time.sleep(1)
        gbt_ready = int(rw.read_reg("BEFE.GEM.OH_LINKS.OH%d.GBT%d_READY" % (oh, gbt)))
        fec_err = int(rw.read_reg("BEFE.GEM.OH_LINKS.OH%d.GBT%d_FEC_ERR_CNT" % (oh, gbt)))
        prbs_err = int(rw.read_reg("BEFE.GEM.OH_LINKS.OH%d.GBT%d_PRBS_ERR_CNT" % (oh, gbt)))
        if gbt_ready != 1:
            fec_err = 2**16 - 1
            prbs_err = 2**16 - 1
        if prbs_err > MAX_ERRORS_ALLOWED:
            break
    return fec_err, prbs_err


#currently unused, should be used for csc tests
def read_link_errors_csc(dmb, err_measure_time):
    if is_odmb:
        rx_mgt = ODMB_RX_MGT[dmb]

        links = x2o_fw_utils.befe_get_all_links()
        x2o_prbs.prbs_control(links, 0) # normal mode on all links
        x2o_prbs.prbs_control(links, 5) # turn on PRBS31 mode on all links

        time.sleep(5)
        rw.write_reg("BEFE.MGTS.MGT%d.CTRL.RX_PRBS_CNT_RESET" % rx_mgt, 1)
        # time.sleep(err_measure_time)
        starting_time = time.time()
        while time.time() < starting_time + err_measure_time:
            time.sleep(1)
            prbs_err = rw.read_reg("BEFE.MGTS.MGT%d.STATUS.PRBS_ERROR_CNT" % rx_mgt)
            if prbs_err > MAX_ERRORS_ALLOWED:
                break

        return prbs_err, prbs_err

    else:
        dmb_link = rw.read_reg("BEFE.CSC_FED.CSC_SYSTEM.RELEASE.DMB_LINK_CONFIG.DMB%d.RX0_LINK" % dmb)
        dmb_mgt = rw.read_reg("BEFE.SYSTEM.LINK_CONFIG.LINK%d.RX_MGT_IDX" % dmb_link)
        rw.write_reg("BEFE.MGTS.MGT%d.CTRL.RX_RESET" % dmb_mgt, 1)
        time.sleep(5)
        rw.write_reg("BEFE.CSC_FED.TEST.DMB_PRBS_TEST.ENABLE", 0)
        rw.write_reg("BEFE.CSC_FED.TEST.DMB_PRBS_TEST.LINK_SELECT", dmb)
        rw.write_reg("BEFE.CSC_FED.TEST.DMB_PRBS_TEST.ENABLE", 1)
        rw.write_reg("BEFE.CSC_FED.LINKS.CTRL.CNT_RESET", 1)
        time.sleep(err_measure_time)
        not_in_table_err = int(rw.read_reg("BEFE.CSC_FED.LINKS.DMB%d.NOT_IN_TABLE_CNT" % dmb))
        prbs_err = int(rw.read_reg("BEFE.CSC_FED.TEST.DMB_PRBS_TEST.PRBS_ERR_CNT"))
    #    if not_in_table_err > prbs_err:
    #        prbs_err = not_in_table_err

        return prbs_err, not_in_table_err


def measure_BER(gbt, oh, switch, opm, rw, bitrate):
    """ Collect measurements on the bit error ratio and optical power
    """
    power = 0.0

    #switch to RX OPM
    switch.select_chan(SWITCH_OPM_PORT)
    time.sleep(1)
    power = measure_power(opm, 1)
    avg_power = measure_power(opm, 100)
    
    frontend_brd = rw.read_reg("BEFE.GEM.GEM_SYSTEM.RELEASE.GEM_STATION")
    switch.select_chan(FE_MAP[frontend_brd][(oh, gbt)])
    print(f"switched to {FE_MAP[frontend_brd][(oh, gbt)]}")
    #switch.select_chan(1)
 
    time.sleep(1)
    num_bits = 3*10**8   #should be 3*10^12 for full test      
    err_measure_time = num_bits / bitrate
    
    fec_err, prbs_err = read_link_errors_gem(oh, gbt, err_measure_time, rw) #!!!
    print("CHANNEL %d:, power: %.2f, FEC correction count: %d, PRBS error count: %d" % (gbt+1, power, fec_err, prbs_err))
    return power, avg_power, fec_err, prbs_err


def find_attenuation_threshold(opm, switch, voa, spec = -11.1):
    """ find the attenuation required for the power to be 'spec' on the current QSFP
    """
 
    print(f"Finding attenuation lvl for {spec} dBm power...")
    voa.attenuate(0)
    switch.select_chan(SWITCH_OPM_PORT)
    time.sleep(1.5)
    optical_power = measure_power(opm, 50)
 
    #determine starting attenuation
    att = abs(optical_power) if optical_power+abs(spec)-1 < 0 else optical_power+abs(spec)-1

    #attenuate until we are just below the power spec
    while(optical_power > spec):
        att += COARSE_ATT_STEP
        voa.attenuate(att)
        time.sleep(1)
        optical_power = measure_power(opm, 50)
    while(optical_power < spec):
        att -= FINE_ATT_STEP
        voa.attenuate(att)
        time.sleep(1)
        optical_power = measure_power(opm, 50)	
    return att


def collect_rx_vars(chan, opm, rx_switch1, rw, x2o_gbt, x2o_utils):
    """The top level script to collect all rx variables on the given channel
    """    
    # before this function is called, the switch and attenuation are set by x2o_prodtest.py
    station = rw.read_reg("BEFE.GEM.GEM_SYSTEM.RELEASE.GEM_STATION") #2=GE21, 0=ME0
    oh, gbt, bitrate = -1, -1, -1
    if(station == 0):
        oh = 0
        gbt = (chan-1) % 4
        bitrate = 10.24*10**9
    elif(station == 2):
        gbt = (chan-1) % 2
        #chan = (chan-1) % 4 +1#temporary map to 1x4 sw:until 1x32 switches arrive
        if(chan >= 3 ):
            oh = 2
        else:
            oh = 3
        bitrate = 4.8*10**9
    print(f"chan{chan} oh{oh} gbt{gbt}") 
    print("STATUS:", gbt_locked(oh, gbt, rw))
    #                                           # configure PRBS signal
    
    power, avg_power, fec_err, prbs_err = measure_BER(gbt, oh, rx_switch1, opm, rw, bitrate)

    # print PASS/FAIL
    if(fec_err | prbs_err == 0):
        print(colored(f"PASS: channel {chan}", "green"))
    else:
        print(colored(f"FAIL: channel {chan}", "red"))
    
    data = {"POWER": power, "AVG_POWER": avg_power, "PREFEC_BER": fec_err, "POSTFEC_BER": prbs_err}  #RX data     
    return data
   
# configure PRBS on frontend
def configure_PRBS(rw, x2o_gbt, x2o_utils):
    station = rw.read_reg("BEFE.GEM.GEM_SYSTEM.RELEASE.GEM_STATION") 
    if(station == 0):
        gbt_config_prbs(ME0_TX_OH, ME0_TX_GBT, rw, x2o_gbt, x2o_utils)
    elif(station == 2):
        gbt_config_prbs(GE21_TX_OH, GE21_TX_GBT, rw, x2o_gbt, x2o_utils)

