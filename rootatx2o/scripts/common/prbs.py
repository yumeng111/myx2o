from common.rw_reg import *
from os import path
import struct
from common.utils import *
from common.fw_utils import *
import tableformatter as tf
import time

try:
    imp.find_module('colorama')
    from colorama import Back
except:
    pass

def prbs_control(links, prbs_mode):
#    for link in links:
#        link.set_prbs_mode(MgtTxRx.TX, prbs_mode)
#        if prbs_mode == 0:
#            #link.config_tx(False) # no inversion
#            link.config_tx(True) # invert for GE1/1
#            link.reset_tx()
    for link in links:
        link.set_prbs_mode(MgtTxRx.RX, prbs_mode)
        if prbs_mode == 0:
            link.config_rx(False) # no inversion for GE1/1 trigger RX
            #link.config_rx(True) # invert
            link.reset_rx()

    time.sleep(0.1)

    for link in links:
        link.reset_prbs_err_cnt()

def prbs_status(links):
    cols = ["Link", "RX Usage", "RX Type", "RX MGT", "RX PRBS Mode", "TX PRBS Mode", "PRBS Error Count"]
    rows = []
    for link in links:
        rx_mgt = link.get_mgt(MgtTxRx.RX)
        tx_mgt = link.get_mgt(MgtTxRx.TX)
        if tx_mgt is None or rx_mgt is None:
            continue
        prbs_err_cnt = link.get_prbs_err_cnt()
        row = [link.idx, link.rx_usage, rx_mgt.type, rx_mgt.idx, rx_mgt.get_prbs_mode(), tx_mgt.get_prbs_mode(), prbs_err_cnt]
        rows.append(row)

    print(tf.generate_table(rows, cols, grid_style=DEFAULT_TABLE_GRID_STYLE))

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: prbs.py <command>")
        print("Commands:")
        print("    enable: enables PRBS-31 mode on all TXs and RXs")
        print("    disable: disables PRBS mode on all TXs and RXs")
        print("    status: prints the PRBS error counters from all RXs")
        exit()

    command = sys.argv[1]
    if command not in ["enable", "disable", "status"]:
        print_red("Unknown command %s. Run the script without parameters to see the possible commmands" % command)
        exit()

    parse_xml()

    links = befe_get_all_links()

    if command == "enable":
        prbs_control(links, 5) # 5 means PRBS-31
        print("PRBS-31 has been enabled on all links (TX and RX)")
        print("NOTE: TX and RX polarity is set to be non-inverted")
        prbs_status(links)
    elif command == "disable":
        prbs_control(links, 0) # 0 means normal mode
        print("PRBS mode has been disabled on all links (TX and RX)")
        print("NOTE: TX and RX polarity is set to be non-inverted")
        prbs_status(links)
    elif command == "status":
        prbs_status(links)
