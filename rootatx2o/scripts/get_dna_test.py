import os

jtag_dev = os.open("/dev/tty0", os.O_RDWR | os.O_NOCTTY | os.O_SYNC)

int_val = int("110010", 2)
byte_data =int_val.to_bytes(1, byteorder = "big")
os.write(jtag_dev, byte_data) 

res = os.read(jtag_dev, 1) 

print(bin(int.from_bytes(res, "big")))

os.close(jtag_dev)
