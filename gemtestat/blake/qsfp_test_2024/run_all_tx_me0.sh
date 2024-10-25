#!/bin/bash

#SOURCE_ID="ODMB7_1"
SOURCE_ID="ME0_0"
QSFP_CAGE="8"
BITS="3*10**12"

date
python3 measure_sensitivity.py scan-att-tx $QSFP_CAGE $SOURCE_ID 0 0 $BITS -1.38 0 0
date
python3 measure_sensitivity.py scan-att-tx $QSFP_CAGE $SOURCE_ID 0 0 $BITS -1.52 0 1
date
python3 measure_sensitivity.py scan-att-tx $QSFP_CAGE $SOURCE_ID 0 0 $BITS -1.83 0 2
date
python3 measure_sensitivity.py scan-att-tx $QSFP_CAGE $SOURCE_ID 0 0 $BITS -1.35 0 3
date

