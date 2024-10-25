import RPi.GPIO as GPIO
import time 
import sys

GPIO_PINS = [36, 32, 22, 18, 16, 12] # These are the physical pins on the raspberry pi that are connected to the optical switch
SWITCH_PINS = [5, 4, 3, 2, 1, 0] # This array defines optical switch pin (A, A', B, B', C, C') physical connection to the GPIO_PIN index

# This map defines the logic value of the SWITCH_PINS for a desired switch setting
OUTPUT_SELECT_MAP = [
                        [0, 1, 1, 0, 0, 0], # input -> output #1
                        [0, 1, 0, 1, 0, 0], # input -> output #2
                        [1, 0, 0, 0, 1, 0], # input -> output #3
                        [1, 0, 0, 0, 0, 1]  # input -> output #4
                    ]

def configure():
    #Set the pin mode:
    GPIO.setmode(GPIO.BOARD)
    GPIO.setup(GPIO_PINS, GPIO.OUT, initial = GPIO.LOW) 


def set_gpio(gpio_idx, value):
    val = GPIO.HIGH if value == 1 else GPIO.LOW
    GPIO.output(GPIO_PINS[gpio_idx], val)

def set_all_gpio_low():
    for i in range(len(GPIO_PINS)):
        set_gpio(i, 0)

# This function sends a signal to the switch to select the desired output
# NOTE: outputs are counted from 0 to 3
# By default this function just sends a pulse of 30ms to the switch, but if use_pulse is set to False, then it will just hold the pins in the desired value (note that this will continuously draw current and may heat up the device)
def output_select(output_idx, use_pulse=True):
    if output_idx < 0 or output_idx > 3:
        print("ERROR: optical switch output index out of range in function switch_output_select(). Value %d was given, while the range is 0 to 3" % output_idx)
        exit()

    switch_pin_values = OUTPUT_SELECT_MAP[output_idx]
    for i in range(len(SWITCH_PINS)):
        set_gpio(SWITCH_PINS[i], switch_pin_values[i])

    time.sleep(0.03)

    set_all_gpio_low()


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: optical_switch.py <output_select>")
        print("output_select: this is the switch output port that you would like to select, range: 0 - 3")
        exit()

    out_sel = int(sys.argv[1])

    configure()
    output_select(out_sel)
    GPIO.cleanup()
