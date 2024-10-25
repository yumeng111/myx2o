import rpyc
import sys
import numpy as np
import matplotlib.pyplot as plt


# FUNCTIONS: 

# power_meter.measure(units="dBm")  # 1 measurement. Default units is Watts
# power_meter.multi_measure(iterations=100, units="W") # makes multiple measurements  
# print("Mean Power: ", power_meter.mean()) # returns mean
# print("Median Power: ", power_meter.median()) # returns median
# power_meter.to_csv() # saves data in csv file
# power_meter.plot_data() # plots data as power vs. time
# power_meter.histogram() # plots data in histogram


def configure():
	conn = rpyc.classic.connect("10.0.0.100", port=12333)
	conn._config['sync_request_timeout'] = None
	global power_meter
	power_meter = conn.modules["measure_power"]
	power_meter.configure(avg_count=avg) # configures power meter, avg_count is number of readings in 1 average(1 measurement) 

def measure():
	global median_array
	median_array = []
	for i in range(int(sys.argv[1])): # number of medians collected
		power_meter.multi_measure(iterations=int(sys.argv[2]), sleep=sleep, units="dBm") # number of iterations, sleep time between each iteration
		median_array.append(float(power_meter.median()))

	print("Mean power: ", np.mean(median_array))
	print("Median power: ", np.median(median_array))
	np.savetxt(fname='median_data.csv', X = median_array, delimiter = ',')

def histogram():
	fig, ax = plt.subplots()
	mean = np.mean(median_array)
	median = np.median(median_array)
	sigma = np.std(median_array)
	textstr = '\n'.join((
	r'$\mathrm{mean}=%.4f$' %(mean, ),
	r'$\mathrm{median}=%.4f$' %(median, ),
	r'$\sigma = %.4f$'% (sigma, )))
	ax.hist(median_array) #n_bins = 10 by default
	props = dict(boxstyle = 'round', facecolor = 'wheat',alpha = 0.5)
	ax.text(0.05, 0.95, textstr, transform=ax.transAxes, fontsize=14, verticalalignment= 'top', bbox=props)
	#if median_array[0] > 0:
		#plt.xlabel("Power (\u03BCW)")
	#else:
	plt.xlabel("Power (dBm)")
	plt.show()
	fig.savefig('/home/gemtest/shachar/histogram.png')

if __name__ == '__main__':
	try:
		if len(sys.argv) < 3:
			print("Usage: power_meter.py <num_medians> <iterations> <avg_count>(default=10) <sleep>(default=0)")
			print("num_medians is the number of medians in final data collected")
			print("iterations is number of measurements in each median")
			print("avg_count(optional) is number of readings included in 1 measurement")
			print("sleep(optional) is time delay in seconds between each reading")
			exit()
		
		global avg
		global sleep
		if len(sys.argv) >= 4:
			avg = int(sys.argv[3])
		else: 
			avg = 10		
		if len(sys.argv) >= 5:
			sleep = float(sys.argv[4]) 
		else:			
			sleep = 0
		
		configure()
		measure()
		histogram()
		power_meter.disconnect()
	except KeyboardInterrupt:
		power_meter.disconnect()
