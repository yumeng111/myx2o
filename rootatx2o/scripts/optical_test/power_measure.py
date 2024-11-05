import rpyc

conn = rpyc.classic.connect("10.0.0.100", port=12333)

power_meter = conn.modules["measure_power"]
power_meter.configure()
power_meter.multi_measure(100, units="dBm") # parameters for multi_measure: iterations, (optional) average_count, (optional) units - W or dBm  
power_meter.to_csv()
power_meter.plot_data()
power_meter.histogram()

