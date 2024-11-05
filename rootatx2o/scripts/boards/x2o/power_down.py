from board.manager import *

def power_down():
    #m=manager(1, 0)
    m=manager(optical_add_on_ver=2)
    m.peripheral.power_down_expert()
    print("x2o powered down.")
    return 0

if __name__ == "__main__":
    power_down()
