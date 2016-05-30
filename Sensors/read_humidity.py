#!/usr/bin/env python

"""
Licensed under MIT (../LICENSE)

read_humidity.py

Accesses on board temperature and humidity sensor through I2C port

V0. Daniel Peyrolon, ICM-CSIC
"""

import sensors #Custom library for SATICE on board payload
import time

def avg(l):
	"""Calculate the average of the data."""
	return reduce(lambda x,y: x + y, l) / len(l)

if __name__ == "__main__":
	s = sensors.hih_6130(0x27)
	data = [s.get_data() for i in range(10)]
	hum = map(lambda d:d["humidity"], data)
	temp = map(lambda d:d["temperature"], data)
	print "%.2f,%.2f" % (avg(hum), avg(temp))
