from gem.me0_lpgbt.rw_reg_lpgbt import *
import gem.gem_utils as gem_utils
from time import sleep, time
import datetime
import sys
import argparse
import random
import json
from vfat_config import initialize_vfat_config, configureVfat, enableVfatchannel

config_boss_filename_v1 = ""
config_sub_filename_v1 = ""
config_boss_v1 = {}
config_sub_v1 = {}
config_boss_filename_v2 = ""
config_sub_filename_v2 = ""
config_boss_v2 = {}
config_sub_v2 = {}

def getConfig (filename):
    f = open(filename, "r")
    reg_map = {}
    for line in f.readlines():
        reg = int(line.split()[0], 16)
        data = int(line.split()[1], 16)
        reg_map[reg] = data
    f.close()
    return reg_map


def vfat_sbit(gem, system, oh_select, vfat_list, nl1a, calpulse_only, align_phases, l1a_bxgap, set_cal_mode, cal_dac, min_error_limit, bestphase_list):
    print ("%s VFAT S-Bit Phase Scan\n"%gem)

    if bestphase_list!={}:
        print ("Setting phases for VFATs only, not scanning")
        for vfat in vfat_list:
            sbit_elinks = gem_utils.me0_vfat_to_sbit_elink(vfat)
            for elink in range(0,8):
                set_bestphase = bestphase_list[vfat][elink]
                setVfatSbitPhase(system, oh_select, vfat, sbit_elinks[elink], set_bestphase)
                print ("VFAT %02d: Phase set for ELINK %02d to: %s" % (vfat, elink, hex(set_bestphase)))
        return

    resultDir = "results"
    try:
        os.makedirs(resultDir) # create directory for results
    except FileExistsError: # skip if directory already exists
        pass
    vfatDir = "results/vfat_data"
    try:
        os.makedirs(vfatDir) # create directory for VFAT data
    except FileExistsError: # skip if directory already exists
        pass
    dataDir = "results/vfat_data/vfat_sbit_phase_scan_results"
    try:
        os.makedirs(dataDir) # create directory for data
    except FileExistsError: # skip if directory already exists
        pass
    now = str(datetime.datetime.now())[:16]
    now = now.replace(":", "_")
    now = now.replace(" ", "_")
    filename = dataDir + "/%s_OH%d_vfat_sbit_phase_scan_results_"%(gem,oh_select) + now + ".txt"
    file_out = open(filename, "w")
    filename_data = dataDir + "/%s_OH%d_vfat_sbit_phase_scan_data_"%(gem,oh_select) + now + ".txt"
    file_out_data = open(filename_data, "w")
    file_out.write("vfat  elink  phase\n")

    errs = [[[0 for phase in range(16)] for elink in range(0,8)] for vfat in range(24)]

    gem_utils.global_reset()
    sleep(0.1)
    gem_utils.write_backend_reg(gem_utils.get_backend_node("BEFE.GEM.GEM_SYSTEM.VFAT3.SC_ONLY_MODE"), 1)

    # Reading S-bit counters
    cyclic_running_node = gem_utils.get_backend_node("BEFE.GEM.TTC.GENERATOR.CYCLIC_RUNNING")
    l1a_node = gem_utils.get_backend_node("BEFE.GEM.TTC.CMD_COUNTERS.L1A")
    calpulse_node = gem_utils.get_backend_node("BEFE.GEM.TTC.CMD_COUNTERS.CALPULSE")

    gem_utils.write_backend_reg(gem_utils.get_backend_node("BEFE.GEM.TRIGGER.SBIT_MONITOR.OH_SELECT"), oh_select)
    reset_sbit_monitor_node = gem_utils.get_backend_node("BEFE.GEM.TRIGGER.SBIT_MONITOR.RESET")  # To reset S-bit Monitor
    reset_sbit_cluster_node = get_backend_node("BEFE.GEM.TRIGGER.CTRL.CNT_RESET")  # To reset Cluster Counter
    sbit_monitor_nodes = []
    cluster_count_nodes = []
    for i in range(0,8):
        sbit_monitor_nodes.append(gem_utils.get_backend_node("BEFE.GEM.TRIGGER.SBIT_MONITOR.CLUSTER%d"%i))
        cluster_count_nodes.append(gem_utils.get_backend_node("BEFE.GEM.TRIGGER.OH0.CLUSTER_COUNT_%d_CNT"%i))

    # Configure TTC generator
    ttc_cnt_reset_node = gem_utils.get_backend_node("BEFE.GEM.TTC.CTRL.MODULE_RESET")
    gem_utils.write_backend_reg(gem_utils.get_backend_node("BEFE.GEM.TTC.GENERATOR.RESET"), 1)
    if calpulse_only:
        gem_utils.write_backend_reg(gem_utils.get_backend_node("BEFE.GEM.TTC.GENERATOR.ENABLE"), 0)
        gem_utils.write_backend_reg(gem_utils.get_backend_node("BEFE.GEM.TTC.GENERATOR.ENABLE_CALPULSE_ONLY"), 1)
    else:
        gem_utils.write_backend_reg(gem_utils.get_backend_node("BEFE.GEM.TTC.GENERATOR.ENABLE"), 1)
        gem_utils.write_backend_reg(gem_utils.get_backend_node("BEFE.GEM.TTC.GENERATOR.ENABLE_CALPULSE_ONLY"), 0)
    gem_utils.write_backend_reg(gem_utils.get_backend_node("BEFE.GEM.TTC.GENERATOR.CYCLIC_L1A_GAP"), l1a_bxgap)
    gem_utils.write_backend_reg(gem_utils.get_backend_node("BEFE.GEM.TTC.GENERATOR.CYCLIC_L1A_COUNT"), nl1a)
    if l1a_bxgap >= 40:
        gem_utils.write_backend_reg(gem_utils.get_backend_node("BEFE.GEM.TTC.GENERATOR.CYCLIC_CALPULSE_TO_L1A_GAP"), 25)
    else:
        gem_utils.write_backend_reg(gem_utils.get_backend_node("BEFE.GEM.TTC.GENERATOR.CYCLIC_CALPULSE_TO_L1A_GAP"), 2)

    # Configure all VFATs
    for vfat in vfat_list:
        gbt, gbt_select, elink_daq, gpio = gem_utils.me0_vfat_to_gbt_elink_gpio(vfat)
        oh_ver = get_oh_ver(oh_select, gbt_select)
        gem_utils.check_gbt_link_ready(oh_select, gbt_select)

        link_good = gem_utils.read_backend_reg(gem_utils.get_backend_node("BEFE.GEM.OH_LINKS.OH%d.VFAT%d.LINK_GOOD" % (oh_select, vfat)))
        sync_err = gem_utils.read_backend_reg(gem_utils.get_backend_node("BEFE.GEM.OH_LINKS.OH%d.VFAT%d.SYNC_ERR_CNT" % (oh_select, vfat)))
        if system!="dryrun" and (link_good == 0 or sync_err > 0):
            print (Colors.RED + "Link is bad for VFAT# %02d"%(vfat) + Colors.ENDC)
            gem_utils.terminate()

        # Configure the pulsing VFAT
        print("Configuring VFAT %d" % (vfat))
        configureVfat(1, vfat, oh_select, 0)
        if set_cal_mode == "voltage":
            gem_utils.write_backend_reg(gem_utils.get_backend_node("BEFE.GEM.OH.OH%i.GEB.VFAT%i.CFG_CAL_MODE"% (oh_select, vfat)), 1)
            gem_utils.write_backend_reg(gem_utils.get_backend_node("BEFE.GEM.OH.OH%i.GEB.VFAT%i.CFG_CAL_DUR"% (oh_select, vfat)), 200)
        elif set_cal_mode == "current":
            gem_utils.write_backend_reg(gem_utils.get_backend_node("BEFE.GEM.OH.OH%i.GEB.VFAT%i.CFG_CAL_MODE"% (oh_select, vfat)), 2)
            gem_utils.write_backend_reg(gem_utils.get_backend_node("BEFE.GEM.OH.OH%i.GEB.VFAT%i.CFG_CAL_DUR"% (oh_select, vfat)), 0)
        else:
            gem_utils.write_backend_reg(gem_utils.get_backend_node("BEFE.GEM.OH.OH%i.GEB.VFAT%i.CFG_CAL_MODE"% (oh_select, vfat)), 0)
            gem_utils.write_backend_reg(gem_utils.get_backend_node("BEFE.GEM.OH.OH%i.GEB.VFAT%i.CFG_CAL_DUR"% (oh_select, vfat)), 0)
        gem_utils.write_backend_reg(gem_utils.get_backend_node("BEFE.GEM.OH.OH%i.GEB.VFAT%i.CFG_CAL_DAC"% (oh_select, vfat)), cal_dac)
        for i in range(128):
            enableVfatchannel(vfat, oh_select, i, 1, 0) # mask all channels and disable calpulsing

        # Reset the link, give some time to accumulate any sync errors and then check VFAT comms
        sleep(0.1)
        gem_utils.gem_link_reset()
        sleep(0.1)

    s_bit_cluster_mapping = {}
    print ("")

    # Starting Phase loop
    for phase in range(0, 16):
        print ("Scanning phase %d"%phase)
        # set phases for all elinks in all vfats
        for vfat in vfat_list:
            sbit_elinks = gem_utils.me0_vfat_to_sbit_elink(vfat)
            for elink in range(0,8):
                setVfatSbitPhase(system, oh_select, vfat, sbit_elinks[elink], phase)

        # Reset the link, give some time to accumulate any sync errors and then check VFAT comms
        sleep(0.1)
        gem_utils.gem_link_reset()
        sleep(0.1)

        print ("Checking errors: ")
        # Starting VFAT loop
        for vfat in vfat_list:
            s_bit_cluster_mapping[vfat] = {}

            # Looping over all channels
            for channel in range(0,128):
                s_bit_cluster_mapping[vfat][channel] = {}
                s_bit_cluster_mapping[vfat][channel]["calpulse_counter"] = 0
                s_bit_cluster_mapping[vfat][channel]["cluster_count"] = []
                s_bit_cluster_mapping[vfat][channel]["sbit_monitor_cluster_size"] = []
                s_bit_cluster_mapping[vfat][channel]["sbit_monitor_cluster_address"] = []

                # Enabling the pulsing channel
                enableVfatchannel(vfat, oh_select, channel, 0, 1) # unmask this channel and enable calpulsing

                # Reset L1A, CalPulse and S-bit monitor
                gem_utils.write_backend_reg(ttc_cnt_reset_node, 1)
                gem_utils.write_backend_reg(reset_sbit_monitor_node, 1)
                gem_utils.write_backend_reg(reset_sbit_cluster_node, 1)

                # Start the cyclic generator
                gem_utils.write_backend_reg(gem_utils.get_backend_node("BEFE.GEM.TTC.GENERATOR.CYCLIC_START"), 1)
                cyclic_running = gem_utils.read_backend_reg(cyclic_running_node)
                while cyclic_running:
                    cyclic_running = gem_utils.read_backend_reg(cyclic_running_node)

                # Stop the cyclic generator
                gem_utils.write_backend_reg(gem_utils.get_backend_node("BEFE.GEM.TTC.GENERATOR.RESET"), 1)

                l1a_counter = gem_utils.read_backend_reg(l1a_node)
                calpulse_counter = gem_utils.read_backend_reg(calpulse_node)

                for i in range(0,8):
                    s_bit_cluster_mapping[vfat][channel]["calpulse_counter"] = calpulse_counter
                    s_bit_cluster_mapping[vfat][channel]["cluster_count"].append(gem_utils.read_backend_reg(cluster_count_nodes[i]))
                    sbit_monitor_value = gem_utils.read_backend_reg(sbit_monitor_nodes[i])
                    sbit_cluster_address = sbit_monitor_value & 0x7ff
                    sbit_cluster_size = ((sbit_monitor_value >> 11) & 0x7) + 1
                    s_bit_cluster_mapping[vfat][channel]["sbit_monitor_cluster_size"].append(sbit_cluster_size)
                    s_bit_cluster_mapping[vfat][channel]["sbit_monitor_cluster_address"].append(sbit_cluster_address)

                # Disabling the pulsing channels
                enableVfatchannel(vfat, oh_select, channel, 1, 0) # mask this channel and disable calpulsing

            # Detecting bad phase for each Elink
            for elink in range(0,8):
                for channel in range(elink*16, elink*16 + 16):
                    multiple_cluster_counts = 0
                    for i in range(1,8):
                        if i == 1:
                            if s_bit_cluster_mapping[vfat][channel]["cluster_count"][i] != s_bit_cluster_mapping[vfat][channel]["calpulse_counter"]:
                                multiple_cluster_counts = 1
                        else:
                            if s_bit_cluster_mapping[vfat][channel]["cluster_count"][i] != 0:
                                multiple_cluster_counts = 1
                    n_clusters = 0
                    for i in range(0,8):
                        if (s_bit_cluster_mapping[vfat][channel]["sbit_monitor_cluster_address"][i] == 0x7ff and s_bit_cluster_mapping[vfat][channel]["sbit_monitor_cluster_size"][i] == 0x7):
                            continue
                        n_clusters += 1
                    if n_clusters > 1 or multiple_cluster_counts == 1:
                        errs[vfat][elink][phase] += 1

                if errs[vfat][elink][phase] == 0:
                    print (Colors.GREEN + "Phase: %d, VFAT %02d SBit ELINK %02d: nr. of channel errors=%d"%(phase, vfat, elink, errs[vfat][elink][phase]) + Colors.ENDC)
                elif errs[vfat][elink][phase] < 16:
                    print (Colors.YELLOW + "Phase: %d, VFAT %02d SBit ELINK %02d: nr. of channel errors=%d"%(phase, vfat, elink, errs[vfat][elink][phase]) + Colors.ENDC)
                else:
                    print (Colors.RED + "Phase: %d, VFAT %02d SBit ELINK %02d: nr. of channel errors=%d"%(phase, vfat, elink, errs[vfat][elink][phase]) + Colors.ENDC)

            # End of Elink loop
            print ("")
        print ("")
        # End of VFAT loop
    # End of Phase loop
    if calpulse_only:
        gem_utils.write_backend_reg(gem_utils.get_backend_node("BEFE.GEM.TTC.GENERATOR.ENABLE_CALPULSE_ONLY"), 0)
    else:
        gem_utils.write_backend_reg(gem_utils.get_backend_node("BEFE.GEM.TTC.GENERATOR.ENABLE"), 0)

    # Unconfigure all VFATs
    for vfat in vfat_list:
        print("Unconfiguring VFAT %d" % (vfat))
        configureVfat(0, vfat, oh_select, 0)
        sleep(0.1)

    aligned_phases_center = [[-9999 for elink in range(8)] for vfat in range(24)]
    for vfat in vfat_list:
         find_aligned_phase_center(vfat, errs[vfat], aligned_phases_center, min_error_limit)

    bestphase_vfat_elink = [[0 for elink in range(8)] for vfat in range(24)]
    print ("\nPhase Scan Results:")
    file_out_data.write("\nPhase Scan Results:\n")
    for vfat in vfat_list:
        centers = 8*[0]
        widths  = 8*[0]
        for elink in range(0,8):
            centers[elink], widths[elink] = find_phase_center(errs[vfat][elink], min_error_limit)
            if not align_phases:
                if centers[elink] == 7 and (widths[elink]==15 or widths[elink]==14):
                    if elink!=0:
                        centers[elink] = centers[elink-1]
            else:
                new_center = aligned_phases_center[vfat][elink]
                if new_center != -9999:
                    if centers[elink] > new_center:
                        if new_center != 14:
                            bad_phase = -9999
                            for p in range(new_center, centers[elink]+1):
                                if errs[vfat][elink][p] != 0:
                                    bad_phase = p
                                    break
                            if bad_phase == -9999:
                                centers[elink] = new_center + 1
                            else:
                                centers[elink] = new_center
                        else:
                            centers[elink] = new_center
                    elif centers[elink] < new_center:
                        if new_center != 0:
                            bad_phase = -9999
                            for p in range(centers[elink], new_center+1):
                                if errs[vfat][elink][p] != 0:
                                    bad_phase = p
                                    break
                            if bad_phase == -9999:
                                centers[elink] = new_center - 1
                            else:
                                centers[elink] = new_center
                        else:
                            centers[elink] = new_center
                    else:
                        centers[elink] = new_center

        print ("\nVFAT %02d :" %(vfat))
        file_out_data.write("\nVFAT %02d :\n" %(vfat))
        for elink in range(0,8):
            phase_print = "  ELINK %02d: " % (elink)
            min_errors = min(errs[vfat][elink])
            if min_errors > min_error_limit:
                min_errors = 0
            for phase in range(0, 16):
                if (widths[elink]>0 and phase==centers[elink]):
                    char=Colors.GREEN + "+" + Colors.ENDC
                    bestphase_vfat_elink[vfat][elink] = phase
                elif (errs[vfat][elink][phase] > min_errors):
                    char=Colors.RED + "-" + Colors.ENDC
                else:
                    char = Colors.YELLOW + "x" + Colors.ENDC

                phase_print += "%s" %char
            if widths[elink]<3:
                phase_print += Colors.RED + " (center=%d, width=%d) BAD" % (centers[elink], widths[elink]) + Colors.ENDC
            elif widths[elink]<5:
                phase_print += Colors.YELLOW + " (center=%d, width=%d) WARNING" % (centers[elink], widths[elink]) + Colors.ENDC
            else:
                phase_print += Colors.GREEN + " (center=%d, width=%d) GOOD" % (centers[elink], widths[elink]) + Colors.ENDC
            print(phase_print)
            file_out_data.write(phase_print + "\n")

        # set phases for all elinks for this vfat
        print ("\nVFAT %02d: Setting all ELINK phases to best phases: "%(vfat))
        sbit_elinks = gem_utils.me0_vfat_to_sbit_elink(vfat)
        for elink in range(0,8):
            set_bestphase = bestphase_vfat_elink[vfat][elink]
            setVfatSbitPhase(system, oh_select, vfat, sbit_elinks[elink], set_bestphase)
            print ("VFAT %02d: Phase set for ELINK %02d to: %s" % (vfat, elink, hex(set_bestphase)))
    for vfat in range(0,24):
        for elink in range(0,8):
            file_out.write("%d  %d  0x%x\n"%(vfat,elink,bestphase_vfat_elink[vfat][elink]))

    sleep(0.1)
    gem_utils.gem_link_reset()
    print ("")
    file_out.close()
    file_out_data.close()

    gem_utils.write_backend_reg(gem_utils.get_backend_node("BEFE.GEM.GEM_SYSTEM.VFAT3.SC_ONLY_MODE"), 0)
    print ("\nS-bit phase scan done\n")


def find_aligned_phase_center(vfat, err_list, aligned_phases_center, min_error_limit):
    err_list_elink = {}
    for elink in range(0, 8):
        err_list_elink[elink] = err_list[elink].copy()
    for elink in range(0, 8):
        min_errors = min(err_list_elink[elink])
        if min_errors > min_error_limit:
            min_errors = 0
        for phase in range(0, len(err_list_elink[elink])):
            if err_list_elink[elink][phase] != min_errors:
                for elink2 in range(0, 8):
                    err_list_elink[elink2][phase] = err_list_elink[elink][phase]
    for elink in range(0, 8):
        center, width = find_phase_center(err_list_elink[elink], min_error_limit)
        if width >= 5:
            aligned_phases_center[vfat][elink] = center

def find_phase_center(err_list, min_error_limit):
    # find the centers
    ngood        = 0
    ngood_max    = 0
    ngood_edge   = 0
    ngood_center = 0

    # Removing phase 15 from the calculation
    err_list_temp = err_list.copy()
    err_list_temp.pop()

    min_errors = min(err_list_temp)
    if min_errors > min_error_limit:
        min_errors = 0

    # duplicate the err_list to handle the wraparound
    err_list_doubled = err_list_temp + err_list_temp
    phase_max = len(err_list_temp)-1

    for phase in range(0,len(err_list_doubled)):
        if (err_list_doubled[phase] == min_errors):
            ngood+=1
        else: # hit an edge
            if (ngood > 0 and ngood >= ngood_max):
                ngood_max  = ngood
                ngood_edge = phase
            ngood=0

    # cover the case when there are no edges, just pick the center
    if (ngood==len(err_list_doubled)):
        ngood_max  = int(ngood/2)
        ngood_edge = len(err_list_doubled)-1

    if (ngood_max>0):
        ngood_width = ngood_max
        # even windows
        if (ngood_max % 2 == 0):
            ngood_center = ngood_edge - int(ngood_max/2) - 1
            if (err_list_doubled[ngood_edge] > err_list_doubled[ngood_edge-ngood_max-1]):
                ngood_center = ngood_center
            else:
                ngood_center = ngood_center+1
        # oddwindows
        else:
            ngood_center = ngood_edge - int(ngood_max/2) -1;

    if ngood_center > phase_max:
        ngood_center = ngood_center % phase_max - 1

    if (ngood_max==0):
        ngood_center=0

    return ngood_center, ngood_max


def setVfatSbitPhase(system, oh_select, vfat, sbit_elink, phase):
    gbt, gbt_select, rx_elink, gpio = gem_utils.me0_vfat_to_gbt_elink_gpio(vfat)
    oh_ver = get_oh_ver(oh_select, gbt_select)
    select_ic_link(oh_select, gbt_select)

    if gbt == "boss":
        if oh_ver == 1:
            config = config_boss_v1
        elif oh_ver == 2:
            config = config_boss_v2
    elif gbt == "sub":
        if oh_ver == 1:
            config = config_sub_v1
        elif oh_ver == 2:
            config = config_sub_v2

    # set phase
    GBT_ELINK_SAMPLE_PHASE_BASE_REG = -9999
    if oh_ver == 1:
        GBT_ELINK_SAMPLE_PHASE_BASE_REG = 0x0CC
    elif oh_ver == 2:
        GBT_ELINK_SAMPLE_PHASE_BASE_REG = 0x0D0
    addr = GBT_ELINK_SAMPLE_PHASE_BASE_REG + sbit_elink
    value = (config[addr] & 0x0f) | (phase << 4)
    #value = (mpeek(addr) & 0x0f) | (phase << 4)

    gem_utils.check_gbt_link_ready(oh_select, gbt_select)
    mpoke(addr, value)
    sleep(0.000001) # writing too fast for CVP13

if __name__ == "__main__":

    # Parsing arguments
    parser = argparse.ArgumentParser(description="ME0 VFAT S-Bit Phase Scan")
    parser.add_argument("-s", "--system", action="store", dest="system", help="system = backend or dryrun")
    parser.add_argument("-q", "--gem", action="store", dest="gem", help="gem = ME0")
    parser.add_argument("-o", "--ohid", action="store", dest="ohid", help="ohid = OH number")
    #parser.add_argument("-g", "--gbtid", action="store", dest="gbtid", help="gbtid = GBT number")
    parser.add_argument("-v", "--vfats", action="store", nargs="+", dest="vfats", help="vfats = list of VFAT numbers (0-23)")
    parser.add_argument("-n", "--nl1a", action="store", dest="nl1a", default = "1000", help="nl1a = fixed number of L1A cycles")
    parser.add_argument("-l", "--calpulse_only", action="store_true", dest="calpulse_only", help="calpulse_only = to use only calpulsing without L1A's")
    parser.add_argument("-a", "--align_phases", action="store_true", dest="align_phases", help="align_phases = whether to align phases of all elinks")
    parser.add_argument("-b", "--bxgap", action="store", dest="bxgap", default="20", help="bxgap = Nr. of BX between two L1As (default = 20 i.e. 0.5 us)")
    parser.add_argument("-m", "--min", action="store", dest="min", default = "4", help="min = Upper limit of the minimum number of errors allowed")
    parser.add_argument("-r", "--use_dac_scan_results", action="store_true", dest="use_dac_scan_results", help="use_dac_scan_results = to use previous DAC scan results for configuration")
    parser.add_argument("-u", "--use_channel_trimming", action="store", dest="use_channel_trimming", help="use_channel_trimming = to use latest trimming results for either options - daq or sbit (default = None)")
    parser.add_argument("-p", "--bestphase", action="store", dest="bestphase", help="bestphase = Best value of the elinkRX phase (in hex), calculated from phase scan by default")
    parser.add_argument("-f", "--bestphase_file", action="store", dest="bestphase_file", help="bestphase_file = Text file with best value of the elinkRX phase for each VFAT and ELINK (in hex), calculated from phase scan by default")
    args = parser.parse_args()

    if args.system == "backend":
        print ("Using Backend for S-bit test")
    elif args.system == "dryrun":
        print ("Dry Run - not actually running sbit phase scan")
    else:
        print (Colors.YELLOW + "Only valid options: backend, dryrun" + Colors.ENDC)
        sys.exit()

    if args.gem != "ME0":
        print(Colors.YELLOW + "Valid gem station: ME0" + Colors.ENDC)
        sys.exit()

    if args.ohid is None:
        print(Colors.YELLOW + "Need OHID" + Colors.ENDC)
        sys.exit()
    #if int(args.ohid) > 1:
    #    print(Colors.YELLOW + "Only OHID 0-1 allowed" + Colors.ENDC)
    #    sys.exit()

    if args.vfats is None:
        print (Colors.YELLOW + "Enter VFAT numbers" + Colors.ENDC)
        sys.exit()
    vfat_list = []
    for v in args.vfats:
        v_int = int(v)
        if v_int not in range(0,24):
            print (Colors.YELLOW + "Invalid VFAT number, only allowed 0-23" + Colors.ENDC)
            sys.exit()
        vfat_list.append(v_int)

    if args.bestphase is not None and args.bestphase_file is not None:
        print (Colors.YELLOW + "Provide either best phase (same for all VFATs) or text file of best phases for each VFAT" + Colors.ENDC)
        sys.exit()
    bestphase_list = {}
    if args.bestphase is not None:
        if "0x" not in args.bestphase:
            print (Colors.YELLOW + "Enter best phase in hex format" + Colors.ENDC)
            sys.exit()
        if int(args.bestphase, 16)>16:
            print (Colors.YELLOW + "Phase can only be 4 bits" + Colors.ENDC)
            sys.exit()
        for vfat in range(0,24):
            for elink in range(0,8):
                bestphase_list[vfat][elink] = int(args.bestphase,16)
    if args.bestphase_file is not None:
        file_in = open(args.bestphase_file)
        for line in file_in.readlines():
            if "vfat" in line:
                continue
            vfat = int(line.split()[0])
            elink = int(line.split()[1])
            phase = int(line.split()[2],16)
            if vfat not in bestphase_list:
                bestphase_list[vfat] = {}
            bestphase_list[vfat][elink] = phase
        file_in.close()

    if args.use_channel_trimming is not None:
        if args.use_channel_trimming not in ["daq", "sbit"]:
            print (Colors.YELLOW + "Only allowed options for use_channel_trimming: daq or sbit" + Colors.ENDC)
            sys.exit()

    if int(args.min) > 16:
        print (Colors.YELLOW + "Maximum number of errors can be 16" + Colors.ENDC)
        sys.exit()

    set_cal_mode = "current"
    cal_dac = 150 # should be 50 for voltage pulse mode

    # Initialization 
    rw_initialize(args.gem, args.system)
    initialize_vfat_config(args.gem, int(args.ohid), args.use_dac_scan_results, args.use_channel_trimming)
    print("Initialization Done\n")

    config_boss_filename_v1 = "../resources/me0_boss_config_ohv1.txt"
    config_sub_filename_v1 = "../resources/me0_sub_config_ohv1.txt"
    config_boss_filename_v2 = "../resources/me0_boss_config_ohv2.txt"
    config_sub_filename_v2 = "../resources/me0_sub_config_ohv2.txt"
    
    if not os.path.isfile(config_boss_filename_v1):
        print (Colors.YELLOW + "Missing config file for boss for OH-v1" + Colors.ENDC)
        sys.exit()
    if not os.path.isfile(config_sub_filename_v1):
        print (Colors.YELLOW + "Missing config file for sub for OH-v1" + Colors.ENDC)
        sys.exit()
    if not os.path.isfile(config_boss_filename_v2):
        print (Colors.YELLOW + "Missing config file for boss for OH-v2" + Colors.ENDC)
        sys.exit()
    if not os.path.isfile(config_sub_filename_v2):
        print (Colors.YELLOW + "Missing config file for sub for OH-v2" + Colors.ENDC)
        sys.exit()
    
    config_boss_v1 = getConfig(config_boss_filename_v1)
    config_sub_v1  = getConfig(config_sub_filename_v1)
    config_boss_v2 = getConfig(config_boss_filename_v2)
    config_sub_v2  = getConfig(config_sub_filename_v2)

    # Running Phase Scan
    try:
        vfat_sbit(args.gem, args.system, int(args.ohid), vfat_list, int(args.nl1a), args.calpulse_only, args.align_phases, int(args.bxgap), set_cal_mode, cal_dac, int(args.min), bestphase_list)
    except KeyboardInterrupt:
        print (Colors.RED + "Keyboard Interrupt encountered" + Colors.ENDC)
        rw_terminate()
    except EOFError:
        print (Colors.RED + "\nEOF Error" + Colors.ENDC)
        rw_terminate()

    # Termination
    rw_terminate()




