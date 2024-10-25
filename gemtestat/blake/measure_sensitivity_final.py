"""
Note: It is important to change the QSFP number, OH number, and date down when the scripts are being printed otherwise old data will be lost. The program will be updated soon to prevent the error from happening. 
"""

import rpyc
import time
import sys
import numpy as np
import matplotlib.pyplot as plt


RPI_IP = "10.0.0.100"
RPI_PORT = 12333
X2O_IP = "10.0.0.10"
X2O_PORT = 12333
OPM_AVG_CNT = 5
OPM_NUM_ITERATIONS = 50
OPM_SLEEP = 0.0
SWITCH_OPM_PORT = 3
SWITCH_GE21_OH_PORTS = {"OH2_GBT0": 1, "OH3_GBT0": 2, "OH2_GBT1": 0}
SWITCH_ME0_OH_PORTS = {"OH0_GBT0": 2, "OH0_GBT2": 1, "OH0_GBT3": 0}

# the OH / GBT number on the X2O that is connected to the GBT which is sending the data back to the X2O receivers under test
GE21_TX_OH = 2
GE21_TX_GBT = 0

ME0_TX_OH = 0
ME0_TX_GBT = 0

# INITIAL_ATTENUATION = 6.0
# COARSE_ATT_STEP = 2.0
INITIAL_ATTENUATION_FEC = 13
FINAL_ATTENUATION_FEC = 15
INITIAL_ATTENUATION_PRBS = 14
FINAL_ATTENUATION_PRBS = 16
COARSE_ATT_STEP = 0.2
FINE_ATT_STEP = 0.25

DATA_ROOT_DIR = "/home/gemtest/evka/evaldas_test"

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
    switch.configure()
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

    return power_meter, switch, voa, rw, x2o_utils, x2o_gbt


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

def scatter_plot_one(x, y, name, title, x_label, y_label, series_label, color="b", marker="o"):
    # plt.xlabel(x_label)
    # plt.xlabel(y_label)
    plt.scatter(x, y, c=color, marker=marker, label=series_label)
    plt.title(title)
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
    rw.write_reg("BEFE.GEM.SLOW_CONTROL.IC.GBTX_LINK_SELECT", global_gbt_idx)
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


def read_link_errors_gem(oh, gbt, err_measure_time):
    rw.write_reg("BEFE.GEM.GEM_SYSTEM.CTRL.LINK_RESET", 1)
    time.sleep(err_measure_time)
    gbt_ready = int(rw.read_reg("BEFE.GEM.OH_LINKS.OH%d.GBT%d_READY" % (oh, gbt)))
    fec_err = int(rw.read_reg("BEFE.GEM.OH_LINKS.OH%d.GBT%d_FEC_ERR_CNT" % (oh, gbt)))
    prbs_err = int(rw.read_reg("BEFE.GEM.OH_LINKS.OH%d.GBT%d_PRBS_ERR_CNT" % (oh, gbt)))
    if gbt_ready != 1:
        fec_err = 2**16 - 1
        prbs_err = 2**16 - 1

    return fec_err, prbs_err

def read_link_errors_csc(dmb, err_measure_time):
    rw.write_reg("BEFE.CSC_FED.TEST.DMB_PRBS_TEST.ENABLE", 0)
    rw.write_reg("BEFE.CSC_FED.TEST.DMB_PRBS_TEST.LINK_SELECT", dmb)
    rw.write_reg("BEFE.CSC_FED.LINKS.CTRL.CNT_RESET", 1)
    rw.write_reg("BEFE.CSC_FED.TEST.DMB_PRBS_TEST.ENABLE", 1)
    time.sleep(err_measure_time)
    not_in_table_err = int(rw.read_reg("BEFE.CSC_FED.LINKS.DMB%d.NOT_IN_TABLE_COUNT" % dmb))
    prbs_err = int(rw.read_reg("BEFE.CSC_FED.TEST.DMB_PRBS_TEST.PRBS_ERR_CNT"))
    if not_in_table_err > prbs_err:
        prbs_err = not_in_table_err

    return prbs_err

def save_data(qsfp_id, source_id, oh_gbt, timestamp, att_values, power_values, fec_err_values, prbs_err_values):
    arr = [att_values, power_values, fec_err_values, prbs_err_values, bit_values]
    np.savetxt(DATA_ROOT_DIR + '/full_measurement_data/qsfp_%s_source_%s_%s_power_%s.csv' % (qsfp_id, source_id, oh_gbt, timestamp), np.transpose(arr), delimiter=',', header="Attenuation,Power,FEC error,PRBS error,Bits(1e10) ")
    fig, (ax1, ax2) = plt.subplots(2)
    scatter_plot(power_values, att_values, "power_vs_attenuation", "Attenuation vs measured power (dBm)", "Measured power (dBm)", "Attenuation (dBm)", "attenuation", fig, ax1)
    scatter_plot(power_values, fec_err_values, "power_fec_err", "Error count vs measured power (dBm)," + "{:.1e}".format(num_bits), "Measured power (dBm)", "FEC correction count", "pre-FEC errors", fig, ax2, color="b", marker="o")
    scatter_plot(power_values, prbs_err_values, "power_fec_err", "Error count vs measured power (dBm), " + "{:.1e}".format(num_bits), "Measured power (dBm)", "FEC correction count", "post-FEC errors", fig, ax2, color="r", marker="o")
    # scatter_plot_one(power_values, fec_err_values, "power_fec_err", "Error count vs measured power (dBm)", "Measured power (dBm)", "FEC correction count", "pre-FEC errors", color="b", marker="o")
    # scatter_plot_one(power_values, prbs_err_values, "power_fec_err", "Error count vs measured power (dBm), " + "{:.1e}".format(num_bits), "Measured power (dBm)", "FEC correction count", "post-FEC errors", color="r", marker="o")
    plt.legend(loc='upper right')
    ax1.legend(loc='upper right')
    plt.subplots_adjust(hspace=0.5)
    plt.savefig(DATA_ROOT_DIR + '/plot_data/qsfp_%s_source_%s_%s_%s.png' % (qsfp_id, source_id, oh_gbt, timestamp))
    # plt.show()


def attenuate_and_measure(att, switch_port, bits, sleep_after_switch=1.0, use_power_meter=True, power_at_zero_att=None):
    power = 0.0
    err_measure_time = bits/bitrate
    voa.attenuate(att)
    time.sleep(1)
    if is_gem:
        fec_err, prbs_err = read_link_errors_gem(oh, gbt, err_measure_time)
    else:
        prbs_err = read_link_errors_csc(dmb, err_measure_time)
        fec_err = prbs_err

    if use_power_meter:
        switch.output_select(SWITCH_OPM_PORT)
        power = measure_power(opm)
        switch.output_select(switch_port)
        time.sleep(sleep_after_switch)
        voa.attenuate(0)
        time.sleep(1)
    else:
        power = power_at_zero_att - att
    print("Attenuation: %.2f, power: %.2f, FEC correction count: %d, PRBS error count: %d" % (att, power, fec_err, prbs_err))
    return power, fec_err, prbs_err


def gbt_locked(oh, gbt):
    return rw.read_reg("BEFE.GEM.OH_LINKS.OH%d.GBT%d_READY" % (oh, gbt))


def return_error(fec_err, prbs_err):
    if error_type == "fec":
        return fec_err
    elif error_type == "prbs":
        return prbs_err


def linear_measure(left, right, step, bits, switch_port, stop_at_err=True, use_power_meter=False):
    print("Measuring between", round(left, 2), "and", round(right, 2), "with step", str(step) + ",", "{:.1e}".format(bits), "bits per measurement") 
    att = round(left, 2)
    first_err_att = None
    while att < round(right, 2) or att == round(right, 2):
        power, fec_err, prbs_err = attenuate_and_measure(att, switch_port, bits, sleep_after_switch=1.0, use_power_meter=use_power_meter, power_at_zero_att=power_at_zero_att)
        fec_err_values.append(fec_err)
        prbs_err_values.append(prbs_err) 
        att_values.append(att)
        power_values.append(power)
        bit_values.append(bits/(10**10))
        error = return_error(fec_err, prbs_err)
        if error > 0 and first_err_att is None:
            first_err_att = att
            if stop_at_err:
                break

        att += step
    
    voa.attenuate(0)
    if first_err_att is None:
        return round(right, 2)
    else:  
        return first_err_att - 0.0


def scan_att(find_edge=False, use_power_meter=True):     
    global oh
    global gbt
    global oh_gbt
    global switch_port
    global dmb
    for switch_oh_port in [2, 1, 0]:
        switch_port = switch_oh_port
        if is_gem:
            if gem_station == 0:
                oh = 0
                if switch_oh_port == 0:
                    gbt = 3
                elif switch_oh_port == 1:
                    gbt = 2
                elif switch_oh_port == 2:
                    gbt = 0
            elif gem_station == 2:
                if switch_oh_port == 0:
                    oh = 2
                    gbt = 1
                elif switch_oh_port == 1:
                    oh = 3
                    gbt = 0
                elif switch_oh_port == 2:
                    oh = 2
                    gbt = 0

            oh_gbt = "OH%d_GBT%d" % (oh, gbt)
        else:
            dmb = switch_oh_port
            oh_gbt = "DMB%d" % dmb

        print("=========== Attenuation scan ===========")
        print("")

        print("Setting initial attenuation zero")
        voa.attenuate(0)
        switch.output_select(SWITCH_OPM_PORT)
        time.sleep(1.5)
        global power_at_zero_att
        power_at_zero_att = measure_power(opm)
        print("Power at zero attenuation: %.2f" % power_at_zero_att)
        switch.output_select(switch_oh_port)
        time.sleep(1)

        if error_type == "fec":
            init_att = INITIAL_ATTENUATION_FEC
            final_att = FINAL_ATTENUATION_FEC
        else:
            init_att = INITIAL_ATTENUATION_PRBS
            final_att = FINAL_ATTENUATION_PRBS
        print("Setting initial attenuation to %ddB" % init_att)
        voa.attenuate(init_att)
        time.sleep(1.5)
        if is_gem:
            locked = gbt_locked(oh, gbt)
            if locked == 0:
                print("ERROR: GBT is not locked even at the initial attenuation level. Exiting..")
                sys.exit()

            # disable GBT header pattern search in order not to shift the MGT data when it unlocks due to switching to the OPM for measurement
            # rw.write_reg("BEFE.GEM.GEM_SYSTEM.CTRL.GBT_FORCE_HEADER_LOCK", 1)

            print("Configuring GBT for PRBS31 loopback")
            gbt_config_prbs(tx_oh, tx_gbt)

            print("OH switch port: %d" % switch_oh_port)
            print("OH GBT: %s" % oh_gbt)
            print("Starting the test")
        print("")

        global att_values
        global power_values
        global fec_err_values
        global prbs_err_values
        global bit_values
        att_values = []
        power_values = []
        fec_err_values = []
        prbs_err_values = []
        bit_values = []
        first_bad_att = None
        first_error_att = None
        att = linear_measure(init_att, final_att, COARSE_ATT_STEP, num_bits, switch_oh_port, stop_at_err=False, use_power_meter=use_power_meter)
        if find_edge:
            print("Finding the edge of failure and leaving the attenuator there")
            if att > 1:
                att = linear_measure(att - 1, att + 1, 0.1, 10**11, switch_oh_port, use_power_meter=use_power_meter)
            else:
                att = linear_measure(0, att + 1, 0.1, 10 ** 11, switch_oh_port, use_power_meter=use_power_meter)
            att = linear_measure(att - 0.3, att + 0.3, 0.02, 5*10**11, switch_oh_port, use_power_meter=use_power_meter)
            att = linear_measure(att - 0.06, att + 0.06, 0.02, 10**12, switch_oh_port, use_power_meter=use_power_meter)
            att -= 0.02
            print("Testing attenuation level", round(att, 2))
            power, fec_err, prbs_err = attenuate_and_measure(att, switch_oh_port, 4.75*10**12, sleep_after_switch=1.0, use_power_meter=True, power_at_zero_att=power_at_zero_att)
            att_values.append(att)
            power_values.append(power)
            fec_err_values.append(fec_err)
            prbs_err_values.append(prbs_err)
            bit_values.append(475)
            error = return_error(fec_err, prbs_err)
            if error < 2:
                while error < 2:
                    att += 0.02
                    print("Testing attenuation level", round(att, 2))
                    power, fec_err, prbs_err = attenuate_and_measure(att, switch_oh_port, 4.75*10**12, sleep_after_switch=1.0, use_power_meter=True, power_at_zero_att=power_at_zero_att)
                    error = return_error(fec_err, prbs_err)
                    att_values.append(att)
                    power_values.append(power)
                    fec_err_values.append(fec_err)
                    prbs_err_values.append(prbs_err)
                    bit_values.append(475)
                att -= 0.01
                print("Testing attenuation level", round(att, 2))
                power, fec_err, prbs_err = attenuate_and_measure(att, switch_oh_port, 4.75*10**12, sleep_after_switch=1.0, use_power_meter=True, power_at_zero_att=power_at_zero_att)
                error = return_error(fec_err, prbs_err)
                att_values.append(att)
                power_values.append(power)
                fec_err_values.append(fec_err)
                prbs_err_values.append(prbs_err)
                bit_values.append(475)
                if error < 2:
                    good_power = power
                    first_good_att = att
                else: 
                    good_power = power_values[len(power_values) - 3]
                    first_good_att = att_values[len(att_values) - 3]
 
            else:     
                error = return_error(fec_err, prbs_err)
                while error > 1:
                    att -= 0.02
                    print("Testing attenuation level", round(att, 2))
                    power, fec_err, prbs_err = attenuate_and_measure(att, switch_oh_port, 4.75*10**12, sleep_after_switch=1.0, use_power_meter=True, power_at_zero_att=power_at_zero_att)
                    error = return_error(fec_err, prbs_err)
                    att_values.append(att)
                    power_values.append(power)
                    fec_err_values.append(fec_err)
                    prbs_err_values.append(prbs_err)
                    bit_values.append(475)
                att += 0.01
                print("Testing attenuation level", round(att, 2))
                power, fec_err, prbs_err = attenuate_and_measure(att, switch_oh_port, 4.75*10**12, sleep_after_switch=1.0, use_power_meter=True, power_at_zero_att=power_at_zero_att)
                error = return_error(fec_err, prbs_err)
                att_values.append(att)
                power_values.append(power)
                fec_err_values.append(fec_err)
                prbs_err_values.append(prbs_err)
                bit_values.append(475)
                if error > 1:
                    good_power = power_values[len(power_values) - 2]
                    first_good_att = att_values[len(att_values) - 2]
                else: 
                    good_power = power
                    first_good_att = att
 
            print(round(first_good_att, 2), "is the first working attenuation level, with power", round(good_power, 2), "dBm")
        # rw.write_reg("BEFE.GEM.GEM_SYSTEM.CTRL.GBT_FORCE_HEADER_LOCK", 0)
        save_data(qsfp_id, source_id, oh_gbt, timestamp, att_values, power_values, fec_err_values, prbs_err_values)


def lpgbt_config_line_driver(mod_curr, emphasis_en, emphasis_short, emphasis_curr):
    if mod_curr > 85:
        print("ERROR: modulation current setting above ~85 may damage VTRX+")
        sys.exit()

    reg39_val = (emphasis_en << 7) | mod_curr
    x2o_gbt.writeGbtRegAddrs(0x39, reg39_val)
    reg3a_val = (emphasis_short << 7) | emphasis_curr
    x2o_gbt.writeGbtRegAddrs(0x3a, reg3a_val)


def scan_lpgbt_mod_curr(min_lock_att, att, mod_curr_min=28, mod_curr_max=75, mod_curr_step=1, emphasis_curr_min=0, emphasis_curr_max=55, emphasis_curr_step=1):
    print("Setting default LpGBT line driver settings")
    lpgbt_config_line_driver(32, 0, 0, 0)

    print("Setting attenuation to %ddB" % att)
    voa.attenuate(att)
    time.sleep(1.5)

    print("Configuring GBT for PRBS31 loopback")
    gbt_config_prbs(tx_oh, tx_gbt)

    switch.output_select(SWITCH_OPM_PORT)
    power = measure_power(opm)
    print("Measured power = %.2fdBm" % power)

    # print("Setting attenuation to 0dBm to allow GBT to lock, and then disable the header pattern search")
    # voa.attenuate(0)
    # time.sleep(1.5)
    switch.output_select(switch_port)
    time.sleep(1.5)
    # locked = gbt_locked(oh, gbt)
    # if locked == 0:
    #     print("ERROR: GBT is not locked even at the initial attenuation level. Exiting..")
    #     sys.exit()
    # # disable GBT header pattern search in order not to shift the MGT data when it unlocks due to switching to the OPM for measurement
    # rw.write_reg("BEFE.GEM.GEM_SYSTEM.CTRL.GBT_FORCE_HEADER_LOCK", 1)
    # print("Setting attenuation to %ddB" % att)
    # voa.attenuate(att)
    # time.sleep(1.5)

    for curr in range(mod_curr_min, mod_curr_max, mod_curr_step):
        max_emph_curr = 85 - curr
        if max_emph_curr > curr - 10:
            max_emph_curr > curr - 10
        if max_emph_curr > emphasis_curr_max:
            max_emph_curr = emphasis_curr_max
        for emph_curr in range(emphasis_curr_min, max_emph_curr, emphasis_curr_step):
            emph_en = 1 if emph_curr > 0 else 0
            emph_short_range = 2 if emph_en == 1 else 1
            for emph_short in range(emph_short_range):
                lpgbt_config_line_driver(curr, emph_en, emph_short, emph_curr)
                curr_ma = float(curr) * 0.137
                emph_curr_ma = float(emph_curr) * 0.137

                locked = gbt_locked(oh, gbt)
                if locked == 0:
                    voa.attenuate(min_lock_att)
                    time.sleep(1.5)
                    locked = gbt_locked(oh, gbt)
                    if locked == 0:
                        print("ERROR: GBT is not locking even at %ddBm, exiting.." % min_lock_att)
                        sys.exit()
                    voa.attenuate(att)
                    time.sleep(1.5)
                    locked = gbt_locked(oh, gbt)
                if is_gem:
                    fec_err, prbs_err = read_link_errors_gem(oh, gbt, num_bits)
                print("Modulation current %d (%.2fmA / %dmV), emphasis short %d, emphasis current %d (%.2fmA / %dmV) -- locked: %d, fec_err: %d, prbs_err: %d" % (curr, curr_ma, curr_ma * 100, emph_short, emph_curr, emph_curr_ma, emph_curr_ma * 100, locked, fec_err, prbs_err))

    rw.write_reg("BEFE.GEM.GEM_SYSTEM.CTRL.GBT_FORCE_HEADER_LOCK", 0)


if __name__ == '__main__':
    if len(sys.argv) < 5:
        print("Usage: measure_sensitivity.py <COMMAND> <QSFP_ID> <SOURCE_ID> <NUM_BITS> [command dependent args]")
        print("COMMAND:")
        print("     scan-att [no-switching]: scans through various attennuation levels and prints / plots the pre-FEC and post-FEC errors")
        print("     scan-att-find-edge [no-switching]: same as above, but at the end it uses very fine attenuation steps to dial in to the spot where errors are starting")
        print("     scan-lpgbt-mod-curr <att> <mod_curr_step> <emphasis_curr_step>: sets attenuation to the specified level, and then scans through lpgbt line driver modulation current")
        print("NUM_BITS: number of bits to test for errors, this can be an expression e.g. 3*10**12")       
        sys.exit()

    command = sys.argv[1]
    qsfp_id = sys.argv[2]
    source_id = sys.argv[3]
    num_bits = eval(sys.argv[4])
    bitrate = 0
    start_time = time.time()
    if "VTRX+" in source_id or "ME0" in source_id:
        bitrate = 10.24 * 10**9
        error_type = "fec"
    elif "VTRX" in source_id or "GE21" in source_id:
        bitrate = 4.8 * 10**9
        error_type = "fec"
    elif "DMB" in source_id:
        bitrate = 1.28 * 10**9
        error_type = "prbs"
    else:
        print("ERROR: unknown source, cannot determine bitrate, see code for possible options")
        sys.exit()

    print("======= QSFP ID %s | source ID %s =======" % (qsfp_id, source_id))

    opm, switch, voa, rw, x2o_utils, x2o_gbt = configure()
    is_gem = True if rw.read_reg("BEFE.SYSTEM.RELEASE.FW_FLAVOR") == 0 else False
    if is_gem and "DMB" in source_id:
        print("ERROR: source ID indicates DMB, but the X2O is loaded with CSC firmware")
        sys.exit()
    if not is_gem and "DMB" not in source_id:
        print("ERROR: source ID indicates a non-DMB source, but the X2O is loaded with CSC firmware")
        sys.exit()

    if is_gem:
        gem_station = rw.read_reg("BEFE.GEM.GEM_SYSTEM.RELEASE.GEM_STATION")
        tx_oh = GE21_TX_OH if gem_station == 2 else ME0_TX_OH if gem_station == 0 else None
        tx_gbt = GE21_TX_GBT if gem_station == 2 else ME0_TX_GBT if gem_station == 0 else None
        x2o_gbt.initGbtRegAddrs()
        x2o_gbt.selectGbt(tx_oh, tx_gbt)

    timestamp = time.strftime("%Y%m%d-%H%M%S")

    if "scan-att" in command:
        find_edge = "find-edge" in command
        use_power_meter = True
        if len(sys.argv) > 5:
            if "no-switching" in sys.argv[5]:
                use_power_meter = False
                print("WARNING: no-switching option was provided -- power is only measured at zero attenuation, and then it's just estimated for each point based on attenuation (this can be useful to avoid GBT unlocks in the backend)")
            if "prbs" in sys.argv[5]:
                error_type = "prbs"
        scan_att(find_edge=find_edge, use_power_meter=use_power_meter)
    elif "scan-lpgbt-mod-curr" in command:
        if len(sys.argv) < 8:
            print("LpGBT modulation current scan needs two extra params: attenuation, and modulation current register value increment step, and emphasis current register value increment step")
            sys.exit()
        att = float(sys.argv[5])
        curr_step = int(sys.argv[6])
        emph_curr_step = int(sys.argv[7])
        # scan_lpgbt_mod_curr(6, att, mod_curr_min=45, mod_curr_max=76, mod_curr_step=curr_step, emphasis_curr_min=0, emphasis_curr_max=50, emphasis_curr_step=emph_curr_step)
        scan_lpgbt_mod_curr(6, att, mod_curr_min=55, mod_curr_max=76, mod_curr_step=curr_step, emphasis_curr_min=0, emphasis_curr_max=50, emphasis_curr_step=emph_curr_step)

    print("Test time: ", (time.time() - start_time)/60, "min")
    opm.disconnect()
