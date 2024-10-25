#!/bin/bash

QSFP_ID="VIT_SR4_104"
BITS="10**12"

python3 measure_sensitivity_odmb7.py scan-att $QSFP_ID ODMB7_1 0 0 $BITS no-switching
python3 measure_sensitivity_odmb7.py scan-att $QSFP_ID ODMB7_1 2 0 $BITS no-switching
python3 measure_sensitivity_odmb7.py scan-att $QSFP_ID ODMB7_1 3 0 $BITS no-switching

#python3 measure_sensitivity.py scan-att VIT_SR4_103 ODMB7_1 0 0 3*10**12 no-switching
#python3 measure_sensitivity.py scan-att VIT_SR4_103 ODMB7_1 2 0 3*10**12 no-switching
#python3 measure_sensitivity.py scan-att VIT_SR4_103 ODMB7_1 3 0 3*10**12 no-switching
