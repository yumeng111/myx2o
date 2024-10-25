"""
Note: It is important to change the QSFP number, OH number, and date down when the scripts are being printed otherwise old data will be lost. The program will be updated soon to prevent the error from happening.
"""

import rpyc
import time
import sys
import numpy as np
import matplotlib.pyplot as plt
import datetime
import csv
import os.path
from termcolor import colored

RPI_IP = "10.0.0.100"
RPI_PORT = 12333
X2O_IP = "10.0.0.11" # X2O v1
#X2O_IP = "10.0.0.13" # X2O v2
X2O_PORT = 12333
OPM_AVG_CNT = 5
OPM_NUM_ITERATIONS = 50
OPM_SLEEP = 0.0
SWITCH_OPM_PORT = 5
# this map had QSFP RX channels 3, 2, 0 connected to switch ports 0, 1, 2
# SWITCH_GE21_OH_PORTS = {"OH2_GBT0": 1, "OH3_GBT0": 2, "OH2_GBT1": 0}
# SWITCH_ME0_OH_PORTS = {"OH0_GBT0": 2, "OH0_GBT2": 1, "OH0_GBT3": 0}
# SWITCH_CSC_DMB_PORTS = {"DMB0": 2, "DMB2": 1, "DMB3": 0}
# ODMB_RX_MGT = {0: 89, 2: 93, 3: 95}
# this map expects QSFP RX channels 0, 2, 3 connected to switch ports 0, 1, 2  (I'm not sure if GE2/1 is correct in this case...)
SWITCH_GE21_OH_PORTS = {"OH2_GBT0": 1, "OH3_GBT0": 0, "OH2_GBT1": 2} # X2O v1
# SWITCH_GE21_OH_PORTS = {"OH0_GBT0": 0, "OH0_GBT1": 1, "OH1_GBT0": 2} # X2O v2
SWITCH_ME0_OH_PORTS = {"OH0_GBT0": 0, "OH0_GBT1": 1, "OH0_GBT2": 2}
#SWITCH_CSC_DMB_PORTS = {"DMB0": 0, "DMB2": 1, "DMB3": 2}
#ODMB_RX_MGT = {0: 89, 2: 93, 3: 95}
SWITCH_CSC_DMB_PORTS = {"DMB0": 0, "DMB1": 1, "DMB2": 2}
ODMB_RX_MGT = {0: 89, 1: 91, 2: 93}

# TX_SWITCH_GE21_OH_PORTS = {"OH3_GBT0": 0, "OH3_GBT1": 1, "OH2_GBT0": 2, "OH2_GBT1": 3}
# TX_SWITCH_GE21_OH_PORTS = {"OH2_GBT0": 0, "OH2_GBT1": 1, "OH3_GBT0": 2, "OH3_GBT1": 3}
TX_SWITCH_GE21_OH_PORTS = {"OH0_GBT0": 0, "OH0_GBT1": 1, "OH1_GBT0": 2, "OH1_GBT1": 3}
TX_SWITCH_ME0_OH_PORTS = {"OH0_GBT0": 0, "OH0_GBT1": 1, "OH0_GBT2": 2, "OH0_GBT3": 3}
TX_SWITCH_CSC_DMB_PORTS = {}

# the OH / GBT number on the X2O that is connected to the GBT which is sending the data back to the X2O receivers under test
GE21_TX_OH = 2 # X2O v1
# GE21_TX_OH = 0 # X2O v2
GE21_TX_GBT = 0

ME0_TX_OH = 0
ME0_TX_GBT = 0

# INITIAL_ATTENUATION = 6.0
# COARSE_ATT_STEP = 2.0
#INITIAL_ATTENUATION = 11.5 # Addon (?)
#INITIAL_ATTENUATION = 13.0 # ODMB7 to Vitex
# INITIAL_ATTENUATION = 12.0 # normal
INITIAL_ATTENUATION_ME0 = 12.0 # ME0 to Vitex
INITIAL_ATTENUATION_TX_ME0 = 16.0 # TX test to ME0
INITIAL_ATTENUATION_GE21 = 12.0 # GE21 to Vitex
INITIAL_ATTENUATION_TX_GE21 = 19.0 # TX test to GE21
INITIAL_ATTENUATION_ODMB7 = 14.5 #13.0 # ODMB7 to Vitex
INITIAL_ATTENUATION_TX_ODMB7 = 16.0 # TX test to ODMB7
INITIAL_ATTENUATION_DTH = 12.0 # DTH
INITIAL_ATTENUATION_TX_DTH = 12.0 # DTH
INITIAL_ATTENUATION_DMB = 8.5 #12.0 # 17.0 # DTH
#INITIAL_ATTENUATION = 14.0
COARSE_ATT_STEP = 0.5
#FINE_ATT_STEP = 0.25
FINE_ATT_STEP = 0.05

MAX_ERRORS_ALLOWED = 0
GO_TO_ZERO_AFTER_SWITCH = True

DATA_ROOT_DIR = "/home/gemtest/blake/qsfp_test_2023"
RESULTS_SUMMARY_FILE = DATA_ROOT_DIR + "/results_summary.csv"

source = {
    'QSFP': 'qsfp',
    'VTRX': 'vtrx',
    'VTRX_Plus': 'vtrx_plus',
    'DMB': 'dmb'
} #The keys are the inputs in the command line, the values are used in the function to determine which transmitter will be tested

# returns power meter, switch, VOA, and X2O rw_reg
def configure():
    print("Connecting to RPi")
    conn_rpi = rpyc.classic.connect(RPI_IP, port=RPI_PORT)
    conn_rpi._config['sync_request_timeout'] = None
    print("Configuring the optical power meter")
    power_meter = conn_rpi.modules["measure_power"]
    try:
        power_meter.configure(avg_count=OPM_AVG_CNT) # configures power meter, avg_count is number of readings in 1 average(1 measurement)
    except:
        power_meter.disconnect()
        power_meter.configure(avg_count=OPM_AVG_CNT)
    print("Configuring the optical switch")
    switch = conn_rpi.modules["optical_switch"]
    #switch.configure()
    print("Configuring the variable optical attenuator")
    voa = conn_rpi.modules["voa"]
    voa.configure()
    # voa.reset()

    print("Connecting to X2O")
    conn_x2o = rpyc.classic.connect(X2O_IP, port=X2O_PORT)
    conn_x2o._config['sync_request_timeout'] = None
    print("Setting up X2O register access")
    rw = conn_x2o.modules["common.rw_reg"]
    rw.parse_xml()
    x2o_utils = conn_x2o.modules["common.utils"]
    x2o_gbt = conn_x2o.modules["gem.gbt"]
    x2o_fw_utils = conn_x2o.modules["common.fw_utils"]
    x2o_prbs = conn_x2o.modules["common.prbs"]
    x2o_optics = conn_x2o.modules["boards.x2o.optics"]

    return power_meter, switch, voa, rw, x2o_utils, x2o_gbt, x2o_fw_utils, x2o_prbs, x2o_optics


def measure_power(opm):
    opm.multi_measure(iterations=OPM_NUM_ITERATIONS, sleep=OPM_SLEEP, units="dBm")
    res = float(opm.median())
    return res

def scatter_plot(x, y, name, title, x_label, y_label, series_label, fig, ax, color="b", marker="o"):
    # plt.xlabel(x_label)
    # plt.xlabel(y_label)
    ax.set_title(title)
    ax.scatter(x, y, c=color, marker=marker, label=series_label)
    # fig.savefig(DATA_ROOT_DIR + '/%s.png' % name)

# x_series is an array of X value arrays
# y_series is an array of Y value arrays
# titles is an array of titles for each of the series
# colors is an array of colors for each of the series
def scatter_plot_multiseries(x_series, y_series, titles, colors):
    pass
    # fig = plt.figure()
    # ax1 = fig.add_subplot(111)
    #
    # for ser in range(len(x_series)):
    #
    # ax1.scatter(x[:4], y[:4], s=10, c='b', marker="s", label='first')
    # ax1.scatter(x[40:], y[40:], s=10, c='r', marker="o", label='second')
    # plt.legend(loc='upper left');
    # plt.show()

def gbtx_write_reg(global_gbt_idx, addr, value):
    fw_date = rw.read_reg("BEFE.SYSTEM.RELEASE.DATE")
    fw_year = fw_date & 0xffff
    if fw_year < 0x2023:
        rw.write_reg("BEFE.GEM.SLOW_CONTROL.IC.GBTX_LINK_SELECT", global_gbt_idx)
    else:
        rw.write_reg("BEFE.GEM.SLOW_CONTROL.IC.GBT_LINK_SELECT", global_gbt_idx)
    rw.write_reg("BEFE.GEM.SLOW_CONTROL.IC.ADDRESS", addr)
    rw.write_reg("BEFE.GEM.SLOW_CONTROL.IC.WRITE_DATA", value)
    rw.write_reg("BEFE.GEM.SLOW_CONTROL.IC.EXECUTE_WRITE", 1)

def gbt_config_loopback(oh, gbt):
    station = rw.read_reg("BEFE.GEM.GEM_SYSTEM.RELEASE.GEM_STATION")
    if station == 2:
        global_gbt_idx = oh * 2 + gbt
        gbtx_write_reg(global_gbt_idx, 29, 0x17)
        gbtx_write_reg(global_gbt_idx, 30, 0x17)
        gbtx_write_reg(global_gbt_idx, 31, 0x17)
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

def gbt_config_prbs(oh, gbt):
    gbt_config_loopback(oh, gbt)
    rw.write_reg("BEFE.GEM.GEM_SYSTEM.CTRL.GBT_PRBS_TX_EN", 1)

def odmb_config_prbs():
    links = x2o_fw_utils.befe_get_all_links()
    x2o_prbs.prbs_control(links, 5) # turn on PRBS31 mode on all links

def read_link_errors_gem(oh, gbt, err_measure_time):
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

    # rw.write_reg("BEFE.GEM.GEM_SYSTEM.CTRL.LINK_RESET", 1)
    # time.sleep(err_measure_time)
    # gbt_ready = int(rw.read_reg("BEFE.GEM.OH_LINKS.OH%d.GBT%d_READY" % (oh, gbt)))
    # fec_err = int(rw.read_reg("BEFE.GEM.OH_LINKS.OH%d.GBT%d_FEC_ERR_CNT" % (oh, gbt)))
    # prbs_err = int(rw.read_reg("BEFE.GEM.OH_LINKS.OH%d.GBT%d_PRBS_ERR_CNT" % (oh, gbt)))
    # if gbt_ready != 1:
    #     fec_err = 2**16 - 1
    #     prbs_err = 2**16 - 1

    return fec_err, prbs_err

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

def attenuate_and_measure(att, switch_oh_port, sleep_after_switch=1.0, use_power_meter=True, power_at_zero_att=None):
    power = 0.0
    if use_power_meter:
        voa.attenuate(att)
        switch.select_chan(SWITCH_OPM_PORT)
        power = measure_power(opm)
        switch.select_chan(switch_oh_port)
        time.sleep(sleep_after_switch)
        if GO_TO_ZERO_AFTER_SWITCH:
            voa.attenuate(0)
            voa.attenuate(att)
    else:
        if GO_TO_ZERO_AFTER_SWITCH:
            voa.attenuate(0)
        voa.attenuate(att)
        power = power_at_zero_att - att
    if is_gem:
        fec_err, prbs_err = read_link_errors_gem(oh, gbt, err_measure_time)
        print("Attenuation: %.2f, power: %.2f, FEC correction count: %d, PRBS error count: %d" % (att, power, fec_err, prbs_err))
    else:
        prbs_err, not_in_table = read_link_errors_csc(dmb, err_measure_time)
        print("Attenuation: %.2f, power: %.2f, PRBS error count: %d, not in table error count: %d" % (att, power, prbs_err, not_in_table))
        if not_in_table > prbs_err:
            prbs_err = not_in_table
        fec_err = prbs_err
    return power, fec_err, prbs_err


def measure_BER(att, gbt, sleep_after_switch=1.0, use_power_meter=True, power_at_zero_att=None):
    power = 0.0
    voa.attenuate(att)
    if use_power_meter:
        switch.select_chan(SWITCH_OPM_PORT)
        power = measure_power(opm)
        switch.select_chan(gbt+1)
        time.sleep(1)
        
    if is_gem:
        fec_err, prbs_err = read_link_errors_gem(oh, gbt, err_measure_time)
        print("CHANNEL %d: Attenuation: %.2f, power: %.2f, FEC correction count: %d, PRBS error count: %d" % (gbt, att, power, fec_err, prbs_err))
    else:
        prbs_err, not_in_table = read_link_errors_csc(dmb, err_measure_time)
        print("Attenuation: %.2f, power: %.2f, PRBS error count: %d, not in table error count: %d" % (att, power, prbs_err, not_in_table))
        if not_in_table > prbs_err:
            prbs_err = not_in_table
        fec_err = prbs_err
    return power, fec_err, prbs_err



def gbt_locked(oh, gbt):
    return rw.read_reg("BEFE.GEM.OH_LINKS.OH%d.GBT%d_READY" % (oh, gbt))



def find_attenuation_threshold(spec = -12):
   
    print("\n----------- Attenuation Threshold -----------")
    print(f"Finding attenuation for {round(spec,2)} dBm...") 

    # loop, while current power > spec, attenuate further
    voa.attenuate(0)
    switch.select_chan(SWITCH_OPM_PORT)
    time.sleep(1.5)
    optical_power = measure_power(opm)
    print("Power at zero attenuation: %.2f dBm" % optical_power)
 
    att = 0 if optical_power+abs(spec)-1 < 0 else optical_power+abs(spec)-1

    #attenuate until we are just below the power spec
    while(optical_power > spec):
        att += COARSE_ATT_STEP
        voa.attenuate(att)
        time.sleep(1)
        optical_power = measure_power(opm)
        print(f"Power at {round(att, 4)} attenuation: {round(optical_power, 4)} dBm")

    while(optical_power < spec):
        att -= FINE_ATT_STEP
        voa.attenuate(att)
        time.sleep(1)
        optical_power = measure_power(opm)
        print(f"Power at {round(att, 4)} attenuation: {round(optical_power, 4)} dBm")
	
    print(f"Attenuation set to {round(att, 4)}, with optical power of {round(optical_power, 4)} dBm\n")
    return att




# use_power_meter -- if this is True, then after each increase in attenuation the switch will switch to the output connected to the power meter and measure the power, if this is False, then the power is measured only at the beginning at 0 attenuation, and it's just estimated later on by adding attenuation to the initial level
# initial_power -- if None is supplied, the initial power at 0 attenuation will be measured, but if it is supplied, then it won't be measured
def test_qsfp_rx(find_edge=False, use_power_meter=True, initial_power=None):
    print("=========== Attenuation scan ===========")
	
    # loop, adjusting VOA until OPM reads at least {qsfp_power}
    # then, check BER
	
    # SINGLE QSFP-------------------------------------------------
    print("Begin with 0 attenuation")
    voa.attenuate(0)
    switch.select_chan(1)
    time.sleep(1)
    # check for GBT lock
    if is_gem:
        if(not gbt_locked(oh, 0)):
            print(colored("ERROR: GBT is not locked even at 0 attenuation. Exiting...\n\n","red"))
            sys.exit()

    # get spec attenuation
    #print("Find the attenuation required to reach the power spec...")
    spec_attenuation = 0 #find_attenuation_threshold(spec=-11.1)
    # go to desired att
    voa.attenuate(spec_attenuation)
    gbt_config_prbs(tx_oh, tx_gbt)
    
    for channel in [0, 1, 2, 3]:
        switch_oh_port = channel+1
        #goto channel
        switch.select_chan(channel)
        time.sleep(1) 
        fec_err = 0
        att = 10.6
        last_sens = 0
        while(fec_err == 0):
            power, fec_err, prbs_err = measure_BER(att, channel)
            att += 0.4
            last_sens = power
            
        print("Sensitivity: ", last_sens)

        if(last_sens <= -12.5):
            print(colored(f"PASS: channel{channel}", "green"))
        else:
            print(colored(f"FAIL: channel{channel}", "red"))
        #pre-FEC BER
        #post-FEC BER
        # average pow at spec att
    # ------------------------------------------------------------    
   

    # rw.write_reg("BEFE.GEM.GEM_SYSTEM.CTRL.GBT_FORCE_HEADER_LOCK", 0)
    print("QSFP temperature: %.2fC" % qsfp.temperature())
    #save_data(qsfp_id, source_id, oh_gbt, timestamp, att_values, power_values, fec_err_values, prbs_err_values, temperature_values, num_bits, num_bits_str, options)


def lpgbt_config_line_driver(mod_curr, emphasis_en, emphasis_short, emphasis_curr):
    if mod_curr > 85:
        print("ERROR: modulation current setting above ~85 may damage VTRX+")
        sys.exit()

    reg39_val = (emphasis_en << 7) | mod_curr
    x2o_gbt.writeGbtRegAddrs(0x39, reg39_val)
    reg3a_val = (emphasis_short << 7) | emphasis_curr
    x2o_gbt.writeGbtRegAddrs(0x3a, reg3a_val)


def qsfp_test(command, qsfp_cage, source_id, oh, num_bits, num_bits_str):
    
    is_tx_test = False
    find_edge = "find-edge" in command
    use_power_meter = True
    if len(sys.argv) > 7:
        if "no-switching" in sys.argv[7]:
            use_power_meter = False
            print("WARNING: no-switching option was provided -- power is only measured at zero attenuation, and then it's just estimated for each point based on attenuation (this can be useful to avoid GBT unlocks in the backend)")
    test_qsfp_rx(find_edge=find_edge, use_power_meter=use_power_meter)
    opm.disconnect() 

#def attenuation_at_power(power):



if __name__ == '__main__':
    if len(sys.argv) < 7:
        print("Usage: measure_sensitivity.py <COMMAND> <QSFP_CAGE_NUM> <SOURCE_ID> <OH> <GBT> <NUM_BITS> [command dependent args]")
        print("COMMAND:")
        print("     scan-att [no-switching]: scans through various attennuation levels and prints / plots the pre-FEC and post-FEC errors")
        print("     scan-att-find-edge [no-switching]: same as above, but at the end it uses very fine attenuation steps to dial in to the spot where errors are starting")
        print("     scan-att-tx <initial_tx_power_dbm> <TX_OH> <TX_GBT>: in this mode the script expects that 4 QSFP TX channels are connected to the optical switch inputs, and the output goes to the frontend through attenuator, the QSFP RX stays constant on OH0 GBT0. Note that in this mode the power cannot be measured automatically, and has to be supplied as an extra argument")
        print("     scan-lpgbt-mod-curr <att> <mod_curr_step> <emphasis_curr_step>: sets attenuation to the specified level, and then scans through lpgbt line driver modulation current")
        print("NUM_BITS: number of bits to test for errors, this can be an expression e.g. 3*10**12")
        sys.exit()

    #get args
    command = sys.argv[1]
    qsfp_cage = int(sys.argv[2])
    source_id = sys.argv[3]
    oh = int(sys.argv[4])
    num_bits = eval(sys.argv[6])
    num_bits_str = sys.argv[6]
    opm, switch, voa, rw, x2o_utils, x2o_gbt, x2o_fw_utils, x2o_prbs, x2o_optics = configure()
    bitrate = 0
    is_odmb = False

    if "VTRX+" in source_id or "ME0" in source_id:
        if "tx" not in command:
            bitrate = 10.24 * 10**9
            INITIAL_ATTENUATION = INITIAL_ATTENUATION_ME0
        else:
            bitrate = 2.56 * 10**9
            INITIAL_ATTENUATION = INITIAL_ATTENUATION_TX_ME0
    elif "VTRX" in source_id or "GE21" in source_id:
        bitrate = 4.8 * 10**9
        if "tx" not in command:
            INITIAL_ATTENUATION = INITIAL_ATTENUATION_GE21
        else:
            INITIAL_ATTENUATION = INITIAL_ATTENUATION_TX_GE21

    	
    qsfps = x2o_optics.x2o_get_qsfps()
    if qsfp_cage not in qsfps.keys():
        print("ERROR: qsfp cage %d cannot be accessed through I2C" % qsfp_cage)
        sys.exit()
	
    qsfp = qsfps[qsfp_cage]
    qsfp.select()
    qsfp_id = qsfp.vendor() + "_" + qsfp.serial_number()

        
    #for gbt in [0, 1, 2]: 
    #    print("############ QSFP ID %s | source ID %s | OH %s | GBT %s | NUM_BITS %s (%d seconds) ############" % (qsfp_id, source_id, oh, gbt, "{:.1e}".format(num_bits), err_measure_time))

    timestamp = time.strftime("%Y%m%d-%H%M%S")


    
    is_gem = True if rw.read_reg("BEFE.SYSTEM.RELEASE.FW_FLAVOR") == 0 and "DTH" not in source_id else False # if testing DTH, just treat it as an ODMB test, because both of these are just PRBS
    if is_gem and "DMB" in source_id:
        print("ERROR: source ID indicates DMB, but the X2O is loaded with CSC firmware")
        sys.exit()

    if is_gem:
        gem_station = rw.read_reg("BEFE.GEM.GEM_SYSTEM.RELEASE.GEM_STATION")
        tx_oh = GE21_TX_OH if gem_station == 2 else ME0_TX_OH if gem_station == 0 else None
        tx_gbt = GE21_TX_GBT if gem_station == 2 else ME0_TX_GBT if gem_station == 0 else None
        x2o_gbt.initGbtRegAddrs()
        x2o_gbt.selectGbt(tx_oh, tx_gbt)
        #oh_gbt = "OH%d_GBT%d" % (oh, gbt)
    
    err_measure_time = num_bits / bitrate

    
    qsfp_test(command, qsfp_cage, source_id, oh, num_bits, num_bits_str)
