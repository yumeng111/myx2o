from board.manager import *

def power_up():
    #m=manager(1, 0)
    m=manager(optical_add_on_ver=2)
    m.peripheral.jtag_chain(1)
    m.peripheral.power_up_expert(verbose=True)
    print("x2o powered up.")
    return 0

if __name__ == "__main__":
    power_up()
