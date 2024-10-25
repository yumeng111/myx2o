#!/bin/bash

#SOURCE_ID="ODMB7_1"
SOURCE_ID="GE21_0"
QSFP_CAGE="8"
BITS="3*10**12"

date
python3 measure_sensitivity.py scan-att-tx $QSFP_CAGE $SOURCE_ID 3 0 $BITS -1.65 3 0
date
python3 measure_sensitivity.py scan-att-tx $QSFP_CAGE $SOURCE_ID 3 0 $BITS -1.66 3 1
date
python3 measure_sensitivity.py scan-att-tx $QSFP_CAGE $SOURCE_ID 3 0 $BITS -1.62 2 0
date
python3 measure_sensitivity.py scan-att-tx $QSFP_CAGE $SOURCE_ID 3 0 $BITS -1.43 2 1
date

