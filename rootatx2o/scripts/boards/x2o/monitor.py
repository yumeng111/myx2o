from board.manager import *

def monitor():
    m = manager(optical_add_on_ver=2)
    m.peripheral.autodetect_optics(verbose=True)
    m.detect_fpgas()

    return m.peripheral.monitor(True)

if __name__ == "__main__":
    monitor()
