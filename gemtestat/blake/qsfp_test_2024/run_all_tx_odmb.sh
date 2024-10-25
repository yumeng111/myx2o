#!/bin/bash

#SOURCE_ID="ODMB7_1"
SOURCE_ID="GE21_O-D-M-B-7"
QSFP_CAGE="26"
BITS="3*10**12"

date
python3 measure_sensitivity_ODMB7_NO_GBT_CONFIG.py scan-att-tx $QSFP_CAGE $SOURCE_ID 0 0 $BITS -1.51 0 0
date
python3 measure_sensitivity_ODMB7_NO_GBT_CONFIG.py scan-att-tx $QSFP_CAGE $SOURCE_ID 0 0 $BITS -1.42 0 1
date
python3 measure_sensitivity_ODMB7_NO_GBT_CONFIG.py scan-att-tx $QSFP_CAGE $SOURCE_ID 0 0 $BITS -1.37 1 0
date
python3 measure_sensitivity_ODMB7_NO_GBT_CONFIG.py scan-att-tx $QSFP_CAGE $SOURCE_ID 0 0 $BITS -1.12 1 1
date

