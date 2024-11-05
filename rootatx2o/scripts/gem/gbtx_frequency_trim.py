from common.rw_reg import *
from common.utils import *
from common.fw_utils import *
from common.promless import *
from gem.gbt import *
from gem.gem_utils import *
import sys

def gbtx_frequency_trim(oh, gbt):
    print("Scanning OH%d GBT%d" % (oh, gbt))

    station = read_reg("BEFE.GEM.GEM_SYSTEM.RELEASE.GEM_STATION")
    gbt_global_num = -1
    if station == 2:
        gbt_global_num = oh * 2 + gbt
    elif station == 1:
        gbt_global_num = oh * 3 + gbt
    else:
        print_red("ERROR: station %d is not supported" % station)
        return

    write_reg("BEFE.GEM.SLOW_CONTROL.IC.GBTX_LINK_SELECT", gbt_global_num)

    trim_regs = [313, 314, 315]

    for trim in range(128):
        write_reg("BEFE.GEM.SLOW_CONTROL.IC.WRITE_DATA", trim)
        for reg in trim_regs:
            write_reg("BEFE.GEM.SLOW_CONTROL.IC.ADDRESS", reg)
            write_reg("BEFE.GEM.SLOW_CONTROL.IC.EXECUTE_WRITE", 1)

        sleep(0.1)
        write_reg("BEFE.GEM.GEM_SYSTEM.CTRL.LINK_RESET", 1)
        sleep(0.1)

        ovf = read_reg("BEFE.GEM.OH_LINKS.OH%d.GBT%d_RX_HAD_OVERFLOW" % (oh, gbt))
        unf = read_reg("BEFE.GEM.OH_LINKS.OH%d.GBT%d_RX_HAD_UNDERFLOW" % (oh, gbt))
        ovf_std = "TRUE" if ovf == 1 else "FALSE"
        unf_std = "TRUE" if unf == 1 else "FALSE"

        color = Colors.RED if ovf == 1 or unf == 1 else Colors.GREEN
        print_color("Trim %d: ovf: %s, unf: %s" % (trim, ovf_str, unf_str), color)


if __name__ == '__main__':
    parse_xml()
    if len(sys.argv) < 3:
        print('Usage: gbtx_frequency_trim.py <oh_num> <gbt_num>')
        sys.exit()

    gbtx_frequency_trim(int(sys.argv[1]), int(sys.argv[2]))
