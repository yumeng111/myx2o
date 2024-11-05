import usb_dongle
import time
import sys
import datetime

USE_DONGLE_LDO = 1 # normally should be set to 1, but if you're using a dongle that has SW2 shorted, then you can set this to 0

if sys.version_info > (3, 6):
    def raw_input(s):
        return input(Colors.YELLOW + s + Colors.ENDC)

# ---------------------------------------------------------------------------------

class GE21_dongle():

    PUSM_STATES = {0: "RESET", 19: "waitVCOstable", 1: "FCLRN", 2: "Contention", 3: "FSETP", 4: "Update", 5: "pauseForConfig", 6: "initXPLL", 7: "waitXPLLLock",
                   8: "resetDES", 9: "resetDES", 10: "waitDESLock", 11: "resetRXEPLL", 12: "resetRXEPLL", 13: "waitRXEPLLLock", 14: "resetSER", 15: "resetSER",
                   16: "waitSERLock", 17: "resetTXEPLL", 18: "resetTXEPLL", 19: "waitTXEPLLLock", 20: "dllReset", 21: "waitdllLocked", 22: "paReset", 23: "initScram",
                   26: "resetPSpll", 27: "resetPSpll", 28: "waitPSpllLocked", 29: "resetPSdll", 30: "waitPSdllLocked", 24: "IDLE"}

    def __init__(self, use_dongle_ldo):
        self.use_dongle_ldo = use_dongle_ldo
        self.dongle = usb_dongle.USB_dongle()
        fw = self.dongle.get_firmware_version()
        print("Dongle: %s" % fw)
        self.dongle.setvtargetldo(use_dongle_ldo)
        if use_dongle_ldo == 1:
            self.dongle.i2c_connect(1)

    def scan(self):
        addrs = self.dongle.i2c_scan()
        if len(addrs) > 0:
            self.gbtx_address = addrs[0]
        return addrs

    def disconnect(self):
        if self.use_dongle_ldo == 1:
            self.dongle.i2c_connect(0)

    def write_register(self, register, value):
        """write a value to a register"""
        reg_add_l=register&0xFF
        reg_add_h=(register>>8)&0xFF
        payload=[reg_add_l]+[reg_add_h]+[value]
        #print payload
        self.dongle.i2c_write(self.gbtx_address,payload)

    def write_register_block(self, start_addr, values):
        """write a value to a register"""

        val_idx = 0
        addr = start_addr
        regs_left = len(values)
        while regs_left > 0:
            n_write = regs_left if regs_left < MAX_WRITE_REG_BLOCK_SIZE else MAX_WRITE_REG_BLOCK_SIZE

            reg_add_l=addr&0xFF
            reg_add_h=(addr>>8)&0xFF
            payload=[reg_add_l]+[reg_add_h]+values[val_idx:val_idx+n_write]
            #print payload
            self.dongle.i2c_write(self.gbtx_address,payload)

            regs_left -= n_write
            addr += n_write
            val_idx += n_write

    def read_register(self, register):
        """read a value from a register - return register byte value"""
        reg_add_l=register&0xFF
        reg_add_h=(register>>8)&0xFF
        payload=[reg_add_l]+[reg_add_h]
        answer= self.dongle.i2c_writeread(self.gbtx_address,1,payload)
        return answer[1]

    def read_register_block(self, start_addr, num_regs):
        ret = []
        regs_left = num_regs
        addr = start_addr
        while regs_left > 0:
            n_read = regs_left if regs_left < 15 else 15
            reg_add_l=addr&0xFF
            reg_add_h=(addr>>8)&0xFF
            payload=[reg_add_l]+[reg_add_h]
            values = self.dongle.i2c_writeread(self.gbtx_address,n_read,payload)[1:]
            ret = ret + values
            regs_left -= n_read
            addr += n_read
        return ret

    def read_state(self):
        state = (self.read_register(431) >> 2) & 0x1F
        state_name = "Unknown"
        if state not in self.PUSM_STATES:
            print_red("Unknown GBTX PUSM state value %d" % state)
        else:
            state_name = self.PUSM_STATES[state]

        return state, state_name

    def fuse(self):
        self.dongle.burnefuse()

def check_state0(state):
    if state == 0:
        print_red("ERROR: GBTX state is 0 (RESET)")
        print_red("This is usually a sign that I2C communication with the chip is not working")
        print_red("Most common cause is that the I2C communication is not enabled on the board: please make sure that SW3-4 is set to the ON position")
        print_red("If the switch is set correctly, you can try a power-cycle, but if the error persists after multiple power-cycles, set this board aside for investigation")
        print_red("IMPORTANT: don't forget to disconnect the dongle from the computer before power cycling the OH")
        print_red("Exiting...")
        log_close()
        exit(-1)

def read_gbtx_sn(dongle):
    heading("TEST: reading GBTX serial number from the test fuses")
    test_fuse1 = dongle.read_register(367)
    test_fuse2 = dongle.read_register(368)
    sn = (test_fuse2 << 8) + test_fuse1
    if sn != 0:
        print_green("PASS: GBTX serial number is not zero: %d (test fuse1 = %s, test fuse2 = %s)" % (sn, hex8(test_fuse1), hex8(test_fuse2)))
        return sn
    else:
        print_red("ERROR: GBTX serial number is 0")
        fail()

def dongle_connect():
    dongle = None
    try:
        dongle = GE21_dongle(USE_DONGLE_LDO)
        print_green("Connected to the dongle")
    except Exception as e:
        print_red(e)
        print_red("ERROR: Could not connect to the dongle")
        print_red("Please check that you have the dongle connected to the computer")
        print_red("If you are running this application as a non-root user, make sure you have a file in /etc/udev/rules.d with the following contents:")
        print_red('ACTION=="add", ATTR{idVendor}=="16c0", ATTR{idProduct}=="05df", MODE:="666"')
        print_red("If you didn't have the file and now you created it, you have to execute: sudo udevadm control --reload-rules")
        print_red("Exiting...")
        log_close()
        exit(-1)

    return dongle

def get_gbt_id(dongle):
    gbt_addrs = dongle.scan()
    if len(gbt_addrs) < 1:
        print_red("ERROR: No GBTX chip detected on the I2C bus")
        print_red("Please check that the dongle is connected to the OH")
        print_red("Exiting...")
        log_close()
        exit(-1)

    if len(gbt_addrs) > 1:
        print_red("ERROR: more than one GBTX detected on the I2C bus... this should not be the case on GE2/1 OH..")
        print_red("Exiting...")
        log_close()
        exit(-1)

    gbt_addr = gbt_addrs[0]
    gbt_id = -1
    if gbt_addr == 1:
        gbt_id = 0
    elif gbt_addr == 3:
        gbt_id = 1
    else:
        print_red("ERROR: unknown GBT I2C address detected: %d" % gbt_addr)
        print_red("Is the dongle connected to a GE2/1 OH board or something else?..")
        print_red("Exiting...")
        log_close()
        exit(-1)

    return gbt_id

if __name__ == '__main__':

    if len(sys.argv) < 3:
        print('Usage: gbt_read_write.py <command> <address> [value]')
        print("Command: read / write")
        sys.exit()

    command = sys.argv[1]
    if command not in ["read", "write"]:
        print("ERROR: unrecognized command %s" % command)
        sys.exit()

    addr = int(sys.argv[2])

    dongle = dongle_connect()
    gbt_id = get_gbt_id(dongle)

    if command == "read":
        ret = dongle.read_register(addr)
        print("Address %d: %d" % (addr, ret))
    elif command == "write":
        if len(sys.argv) < 4:
            print("too few arguments")
            sys.exit()
        val = int(sys.argv[3])
        dongle.write_register(addr, val)
        print("Wrote %d to address %d" % (val, addr))
        ret = dongle.read_register(addr)
        if (ret == val):
            print("readback matches")
        else:
            print(" =========>> ERROR: readback does not match, wrote %d, read %d" % (val, ret))

    dongle.disconnect()
