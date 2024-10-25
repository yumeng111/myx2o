open_hw_manager

connect_hw_server -url 10.0.0.11:12333

puts "connected to hw server"

refresh_hw_device [lindex [get_hw_devices] 0]

puts "refresh"
current_hw_device [lindex [get_hw_devices] 0]

set dna_value [get_hw_device_dna]

puts "FPGA DNA: $dna_value"

disconnect hw_server
close_hw

