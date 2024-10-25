import RPi.GPIO as GPIO
import time
import smbus2
import sys

PIN_RESET = 13
READ_ADDRESS = 0x49

def configure():
    #GPIO.setmode(GPIO.BOARD)
    #GPIO.setup(PIN_RESET, GPIO.OUT, initial=GPIO.HIGH)

    global bus
    bus = smbus2.SMBus(1)
    time.sleep(1)

def reset():
    #GPIO.output(PIN_RESET, GPIO.HIGH)
    bus.write_i2c_block_data(READ_ADDRESS, 0x32, [0x96, 0xa2])
    time.sleep(1)

def attenuate(value):
    val = int(value * 100)
    array = []
    array.append((val & 0xFF00) >> 8)
    array.append(val & 0xFF)
    print("Sending: ", array)
    bus.write_i2c_block_data(READ_ADDRESS, 0x80, array) 
    time.sleep(0.1)
    print("Attenuation rate: ", bus.read_i2c_block_data(READ_ADDRESS, 0x81, 2))

if __name__ == '__main__':
    configure()
    value = float(sys.argv[1])
    attenuate(value)
    #reset()
