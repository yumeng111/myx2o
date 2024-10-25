import serial
import time
import sys

def configure(dev_file="ttyUSB0"):
    #the device file IDs the switch
    switch = Switch(dev_file)

    return switch


def select_chan(ser, chan):
    if(chan <= 0):
        print(f"INALID ARGUMENT: {chan}")
        sys.exit()
    
    #open the device file
    if not ser.is_open:
        ser.open()

    # command for calibraton
    ser.write(bytearray([0x01, 0x20, 0x00, 0x00]))
    time.sleep(1)
    # command for output channel selection
    ser.write(bytearray([0x01, 0x12, 0x00, chan]))
    time.sleep(1)
    ser.close()
    return 0


class Switch():
    def __init__(self, fp):
        self.fp = fp #device file path
        self.ser = serial.Serial(
            port = "/dev/"+fp,
            baudrate=9600,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            bytesize=serial.EIGHTBITS,
            timeout = 1
        )
    
    def select_chan(self, chan):
        select_chan(self.ser, chan)


if __name__ == "__main__":
    # handle command line args
    if(len(sys.argv) != 2):
        print("INVALID ARGUMENTS, use: python3 optical_switch.py {chan}")
        sys.exit()
    chan = int(sys.argv[1])

    ser = configure()
    # switch
    select_chan(ser.ser, chan)
