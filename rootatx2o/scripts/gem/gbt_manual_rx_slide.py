from common.rw_reg import *
from common.utils import *
from common.fw_utils import *
from common.promless import *
from gem.gbt import *
from gem.gem_utils import *
import sys

def gbt_manual_rx_slide_scan(oh, gbt):

    slide_en = read_reg("BEFE.GEM.GEM_SYSTEM.CTRL.GBT_RXSLIDE_EN")
    write_reg("BEFE.GEM.GEM_SYSTEM.CTRL.GBT_RXSLIDE_EN", 0)

    gbt_rx_link = read_reg("BEFE.GEM.GEM_SYSTEM.RELEASE.OH_LINK_CONFIG.OH%d.GBT%d_RX" % (oh, gbt))
    gbt_rx_mgt = read_reg("BEFE.SYSTEM.LINK_CONFIG.LINK%d.RX_MGT_IDX" % gbt_rx_link)

    print("Scannnig OH%d GBT%d -- RX MGT%d" % (oh, gbt, gbt_rx_mgt))

    locked = read_reg("BEFE.GEM.OH_LINKS.OH%d.GBT%d_RX_HEADER_LOCKED" % (oh, gbt))
    print("Lock status before slide: %d" % locked)

    for i in range(40):
        write_reg("BEFE.MGTS.MGT1.CTRL.RX_MANUAL_SLIDE", 1)
        write_reg("BEFE.MGTS.MGT1.CTRL.RX_MANUAL_SLIDE", 0)
        sleep(0.1)
        write_reg("BEFE.GEM.GEM_SYSTEM.CTRL.GBT_RESET", 1)
        write_reg("BEFE.GEM.GEM_SYSTEM.CTRL.GBT_RESET", 0)
        sleep(0.1)
        write_reg("BEFE.GEM.GEM_SYSTEM.CTRL.LINK_RESET", 1)
        sleep(0.5)
        locked = read_reg("BEFE.GEM.OH_LINKS.OH%d.GBT%d_RX_HEADER_LOCKED" % (oh, gbt))
        print("slide %d: locked = %d" % (i, locked))

    write_reg("BEFE.GEM.GEM_SYSTEM.CTRL.GBT_RXSLIDE_EN", slide_en)

if __name__ == '__main__':
    parse_xml()
    if len(sys.argv) < 3:
        print('Usage: gbt_manual_rx_slide.py <oh_num> <gbt_num>')
        sys.exit()

    gbt_manual_rx_slide_scan(int(sys.argv[1]), int(sys.argv[2]))
