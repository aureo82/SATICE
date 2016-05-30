#!/usr/bin/env python

"""
Licensed under MIT (../LICENSE)

ucam.py

Reads voltage and current from on-board power sensors.

V0. Daniel Peyrolon & Oriol Sanchez,ICM-CSIC

Current channels definition:
		0x40 -> Modem Iridium
		0x41 -> MPU1, first power input
		0x44 -> MPU2, second power input
		0x45 -> Fox & GPS for new boards.

"""


import sensors #Custom library for SATICE on board payload
import time

def print_fields(data):
	return "%.2f,%.2f" % (data['bus'], data['current'])

if __name__ == "__main__":
	modem = sensors.ina_219(0x40)
	d1 = print_fields(modem.get_data())
	
	mpu1 = sensors.ina_219(0x44)
	d2 = print_fields(mpu1.get_data())
	
	mpu2 = sensors.ina_219(0x41)
	d3 = print_fields(mpu2.get_data())
	
	fox = sensors.ina_219(0x45)
	d4 = print_fields(fox.get_data())
	print d1+','+d2+','+d3+','+d4
