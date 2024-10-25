#!/bin/bash

SOURCE="ODMB7_WITH_100M_CABLE"
QSFP_CAGE="20"
BITS="3*10**12"
#OPTIONS="no-switching"
OPTIONS=""

python3 measure_sensitivity.py scan-att $QSFP_CAGE $SOURCE 0 0 $BITS $OPTIONS
python3 measure_sensitivity.py scan-att $QSFP_CAGE $SOURCE 1 0 $BITS $OPTIONS
python3 measure_sensitivity.py scan-att $QSFP_CAGE $SOURCE 2 0 $BITS $OPTIONS

#python3 measure_sensitivity.py scan-att $QSFP_CAGE ODMB7_1 0 0 $BITS no-switching
#python3 measure_sensitivity.py scan-att $QSFP_CAGE ODMB7_1 1 0 $BITS no-switching
#python3 measure_sensitivity.py scan-att $QSFP_CAGE ODMB7_1 2 0 $BITS no-switching
