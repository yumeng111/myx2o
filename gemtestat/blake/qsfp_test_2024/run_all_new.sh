#!/bin/bash

#SOURCE_ID="ODMB7_1"
SOURCE_ID="DTH_2"
QSFP_CAGE="20"
BITS="3*10**12"

python3 measure_sensitivity.py scan-att $QSFP_CAGE $SOURCE_ID 0 0 $BITS no-switching
python3 measure_sensitivity.py scan-att $QSFP_CAGE $SOURCE_ID 2 0 $BITS no-switching
python3 measure_sensitivity.py scan-att $QSFP_CAGE $SOURCE_ID 3 0 $BITS no-switching

