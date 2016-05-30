#!/usr/bin/env python

"""
Licensed under MIT (../LICENSE)

sensors.py

Provides subroutines to access I2C on board sensors and serial ports
and common operations to those sensors.

Current supported sensors:
		vx0706 -> Serial Camera
		HIH6130 -> On board Temperature and Humidity
		INA219 -> On board Power
		mpu9150 -> 9DOF->TBReviewed
		
V0. Daniel Peyrolon & Oriol Sanchez,ICM-CSIC
"""


import ctypes as ct
import fox
import os
import serial
import smbus
import time

#V1 Daniel Peyrolon - March 2015
#V2 Oriol Sanchez - February 2016
#		* Fixed temperature reading on HIH6130

class i2c_iface():
	"""Simple class that manages the I/O of the I2C bus.
		also invert the words if needed (device dependent)."""
	def __init__(self, bus, addr, invert_endian=False):
		assert(bus >= 0)
		assert(addr >= 0)
		self.addr = addr
		self.invert = invert_endian
		self.b = smbus.SMBus(bus)

	def _invert_endianness(self, val):
		"""Invert the world (ushort16) endianness if needed."""
		if self.invert == False:
			return val
		else:
			h = val & 0xff00
			l = val & 0x00ff
			return (l<<8)|(h>>8)

	def write_bus(self, val):
		"""Write only to the bus."""
		time.sleep(0.01)
		return self.b.write_byte(self.addr, val)

	def read_bus(self, length):
		"""Write data from bus."""
		time.sleep(0.01)
		return self.b.read_i2c_block_data(self.addr, length)

	def write_register(self, reg, val):
		"""Write any value at the addr"""
		# Invert if neeeded.
		val = self._invert_endianness(val)
		time.sleep(0.01)
		self.b.write_word_data(self.addr, reg, val)
		return

	def read_register(self, addrh, addrl=None):
		"""Read any value from the sensor. If two addresses, merge data."""
		time.sleep(0.01)
		if (addrl == None):
			val = self.b.read_word_data(self.addr, addrh)
		else:
			h = self.b.read_word_data(self.addr, addrh)
			time.sleep(0.01)
			l = self.b.read_word_data(self.addr, addrl)
			val = ((h << 8) | l)
		return self._invert_endianness(val)

	def read_register_byte(self, addrh, addrl=None):
		"""Read any value from the sensor. If two addresses, merge data."""
		time.sleep(0.01)
		if (addrl == None):
			val = self.b.read_byte_data(self.addr, addrh)
		else:
			h = self.b.read_byte_data(self.addr, addrh)
			time.sleep(0.01)
			l = self.b.read_byte_data(self.addr, addrl)
			val = ((h << 8) | l)
		return self._invert_endianness(val)

# Use the INA219, connected through I2C to gather consumption data.
# We have sensors on 0x40, 0x41, 0x44 and 0x45.
class ina_219():
	"""Class to manage the ina219 at SI06. Its values are:
		Calibration value is: 3792
		R_shunt = 0.18 ohms
		V_bux_max = 16V
		Vshunt_max = 0.32 V
		max_I = 1.78A
		max P = 0.3204 W"""
	ina219_conf = 0
	ina219_tension = 1
	ina219_bus_tension = 2
	ina219_power = 3
	ina219_current = 4
	ina219_cal = 5
	current_lsb = 60e-6
	power_lsb = 1200e-6
	# Config_on is the configuration needed to wake up sensor.
	config_on = 0x199f
	# config_off is the configuration needed to power down the sensor.
	config_off = 0x1998

	def __init__(self, addr):
		"""Create the connection. Starts up the sensor,
		configure, calibrates it."""
		self.iface = i2c_iface(0, addr, invert_endian=True)

		# Make it sleep.
		self.iface.write_register(self.ina219_conf, self.config_off)

		# Calibrate.
		self.iface.write_register(self.ina219_cal, 3792)
		return

	def _del_(self):
		"""By default, shuts down the sensor."""
		self.iface.write_register(self.ina219_conf, self.config_off)
		return

	def _switch_on(self):
		"""Starts the sensor."""
		self.iface.write_register(self.ina219_conf, self.config_on)
		return

	def _switch_off(self):
		"""Power down the sensor."""
		self.iface.write_register(self.ina219_conf, self.config_off)
		return

	def _read_shunt(self):
		"""Reads shunt tension (V)."""
		# Note the division by 100000 this is a division by 100 to get the
		# actual value.
		return float(self.iface.read_register(self.ina219_tension)) / 100000

	def _read_bus(self):
		"""Reads bus tension (V)."""
		ret = 0
		# Check last bit to know if the sensor has good data.
		while ret << 14 == 0:
			ret = self.iface.read_register(self.ina219_bus_tension)
		ret = ret >> 3
		return ret * 0.004

	def _read_power(self):
		"""Reads power register  (Vbus * Current) (W)."""
		return self.iface.read_register(self.ina219_power) * self.power_lsb

	def _read_current(self):
		"""Reads shunt current (A)."""
		return self.iface.read_register(self.ina219_current) * self.current_lsb

	def get_data(self):
		"""Main function used to get all the real data."""
		# Swith on and off the sensor as needed.
		self._switch_on()
		ret = {"shunt": self._read_shunt(),
			  "bus": self._read_bus(),
			  "power bus": self._read_power(),
			  "current": self._read_current()}
		self._switch_off()
		return ret

class hih_6130():
	"""Class to manage the humidity sensor."""
	def __init__(self, addr):
		"""Create the connection. Starts up the sensor, sets
		everything, calibrates it."""
		self.iface = i2c_iface(0, addr, invert_endian=True)
		return

	def _read_data(self):
		"""Reads humidity and temperature."""
		self.iface.write_bus(4)
		val = self.iface.read_bus(4)
		hum = ((val[0] & 0x3f) << 8) | val[1]
		hum = (float(hum)/16383)*100

		temp = (val[2] << 8) | val[3]
		temp = temp >> 2
		temp = ((((float(temp))/16383)*165) - 40)
		return hum, temp

	def get_data(self):
		"""Main function used to get all the real data."""
		hum, temp = self._read_data()
		return {"humidity": hum,
			"temperature": temp}

class vc0706():
	"""Class to handle the camera. Will present a very high level user
	interface."""
	port = '/dev/ttyS2'
	baudrate = 38400
	timeout = 0.2

	ser = None
	path = None

	serialnum = 0
	commandsend = 0x56
	commandreply = 0x76
	commandend = 0x00

	cmd_getversion = 0x11
	cmd_reset = 0x26
	cmd_takephoto = 0x36
	cmd_readbuff = 0x32
	cmd_getbufflen = 0x34

	fbuf_currentframe = 0x00
	fbuf_nextframe = 0x01
	fbuf_stopcurrentframe = 0x00

	getversioncommand = [commandsend, serialnum, cmd_getversion, commandend]
	resetcommand = [commandsend, serialnum, cmd_reset, commandend]
	takephotocommand = [commandsend, serialnum, cmd_takephoto, 0x01, fbuf_stopcurrentframe]
	getbufflencommand = [commandsend, serialnum, cmd_getbufflen, 0x01, fbuf_currentframe]
	readphotocommand = [commandsend, serialnum, cmd_readbuff, 0x0C, fbuf_currentframe, 0x0a]

	def __init__(self):
		"""Set up everything, the camera has to be switched on previously."""
		self._switch_on()
		assert(self._get_version() == True)
		self._switch_off()
		return

	def _switch_on(self):
		"""Create connections with camera."""
		self.ser = serial.Serial(baudrate = self.baudrate,
		                         port = self.port,
		                         timeout = self.timeout)
		time.sleep(0.5)
		return

	def _switch_off(self):
		"""Close connections with camera."""
		self.ser.close()
		time.sleep(0.5)
		return

	def _get_version(self):
		"""Gets camera version."""
		cmd = ''.join(map (chr, self.getversioncommand))
		self.ser.write(cmd)
		return self._checkreply(self.ser.read(16), self.cmd_getversion)

	def _checkreply(self, r, b):
		"""Compares the command of the received message, checks status."""
		r = map(ord, list(r))
		return r[0] == 0x76 and r[1] == self.serialnum and r[2] == b and r[3] == 0x00

	def _take_snapshot(self):
		"""Order the camera to take a photo."""
		cmd = ''.join(map(chr, self.takephotocommand))
		self.ser.write(cmd)
		r = list(self.ser.read(5))
		return self._checkreply(r, self.cmd_takephoto) and r[3] == chr(0x0)

	def _photo_data(self):
		"""Fetches the data from the camera."""
		# Get the length of the photography.
		self.ser.write(''.join(map(chr, self.getbufflencommand)))
		r = list(self.ser.read(9))
		if self._checkreply(r, self.cmd_getbufflen) and r[4] == chr(0x4):
			bytes = ord(r[5])
			bytes <<= 8
			bytes += ord(r[6])
			bytes <<= 8
			bytes += ord(r[7])
			bytes <<= 8
			bytes += ord(r[8])

		addr = 0   # the initial offset into the frame buffer
		photo = []

		# bytes to read each time (must be a mutiple of 4)
		inc = 8192

		while(addr < bytes):
			# On the last read, we may need to read fewer bytes.
			chunk = min(bytes-addr, inc);

			# Append 4 bytes that specify the offset into the frame buffer.
			command = self.readphotocommand + [(addr >> 24) & 0xff,
					(addr>>16) & 0xff,
					(addr>> 8) & 0xff,
					addr & 0xff]

			# Append 4 bytes that specify the data length to read.
			command += [(chunk >> 24) & 0xff,
					(chunk>>16) & 0xff,
					(chunk>>8 ) & 0xff,
					chunk & 0xff]

			# Append the delay.
			command += [1,0]

			# Make a string out of the command bytes.
			cmd = ''.join(map(chr, command))
			self.ser.write(cmd)

			# The reply is a 5-byte header, followed by the image data
			# followed by the 5-byte header again.
			r = list(self.ser.read(5+chunk+5))
			if len(r) != 5+chunk+5:
				# retry the read if we didn't get enough bytes back.
				continue

			if not self._checkreply(r, self.cmd_readbuff):
				print "ERROR READING PHOTO"
				return

			# Append the data between the header data to photo
			photo += r[5:chunk+5]

			# advance the offset into the frame buffer
			addr += chunk
		return photo


	def take_photo(self, path=None, time=None):
		"""Take a photography write if the path is given, at the
		indicated time if given, take the photography at the moment
		otherwise. Returns the stream of bytes."""
		self._switch_on()
		# Take a snapshot.
		self._take_snapshot()
		# Get the actual photo..
		photo = ''.join(self._photo_data())

		self._switch_off()
		if path != None:
			# If we need to create the directory, create it.
			dir = os.path.dirname(path)
			if not os.path.exists(dir):
				os.makedirs(dir)
			# Write the photography.
			f = open(path, 'w')
			f.write(photo)
			f.close()

		return ''.join(photo)


class mpu9150():
	"""This class controls the 9dof embedded in the system."""
	s_self_test_x        = 0x0D # R/W
	s_self_test_y        = 0x0E # R/W
	s_self_test_z        = 0x0F # R/W
	s_self_test_a        = 0x10 # R/W
	s_smplrt_div         = 0x19 # R/W
	s_config             = 0x1A # R/W
	s_gyro_config        = 0x1B # R/W
	s_accel_config       = 0x1C # R/W
	s_ff_thr             = 0x1D # R/W
	s_ff_dur             = 0x1E # R/W
	s_mot_thr            = 0x1F # R/W
	s_mot_dur            = 0x20 # R/W
	s_zrmot_thr          = 0x21 # R/W
	s_zrmot_dur          = 0x22 # R/W
	s_fifo_en            = 0x23 # R/W
	s_i2c_mst_ctrl       = 0x24 # R/W
	s_i2c_slv0_addr      = 0x25 # R/W
	s_i2c_slv0_reg       = 0x26 # R/W
	s_i2c_slv0_ctrl      = 0x27 # R/W
	s_i2c_slv1_addr      = 0x28 # R/W
	s_i2c_slv1_reg       = 0x29 # R/W
	s_i2c_slv1_ctrl      = 0x2A # R/W
	s_i2c_slv2_addr      = 0x2B # R/W
	s_i2c_slv2_reg       = 0x2C # R/W
	s_i2c_slv2_ctrl      = 0x2D # R/W
	s_i2c_slv3_addr      = 0x2E # R/W
	s_i2c_slv3_reg       = 0x2F # R/W
	s_i2c_slv3_ctrl      = 0x30 # R/W
	s_i2c_slv4_addr      = 0x31 # R/W
	s_i2c_slv4_reg       = 0x32 # R/W
	s_i2c_slv4_do        = 0x33 # R/W
	s_i2c_slv4_ctrl      = 0x34 # R/W
	s_i2c_slv4_di        = 0x35 # R
	s_i2c_mst_status     = 0x36 # R
	s_int_pin_cfg        = 0x37 # R/W
	s_int_enable         = 0x38 # R/W
	s_int_status         = 0x3A # R
	s_accel_xout_h       = 0x3B # R
	s_accel_xout_l       = 0x3C # R
	s_accel_yout_h       = 0x3D # R
	s_accel_yout_l       = 0x3E # R
	s_accel_zout_h       = 0x3F # R
	s_accel_zout_l       = 0x40 # R
	s_temp_out_h         = 0x41 # R
	s_temp_out_l         = 0x42 # R
	s_gyro_xout_h        = 0x43 # R
	s_gyro_xout_l        = 0x44 # R
	s_gyro_yout_h        = 0x45 # R
	s_gyro_yout_l        = 0x46 # R
	s_gyro_zout_h        = 0x47 # R
	s_gyro_zout_l        = 0x48 # R
	s_ext_s_data_00   = 0x49 # R
	s_ext_s_data_01   = 0x4A # R
	s_ext_s_data_02   = 0x4B # R
	s_ext_s_data_03   = 0x4C # R
	s_ext_s_data_04   = 0x4D # R
	s_ext_s_data_05   = 0x4E # R
	s_ext_s_data_06   = 0x4F # R
	s_ext_s_data_07   = 0x50 # R
	s_ext_s_data_08   = 0x51 # R
	s_ext_s_data_09   = 0x52 # R
	s_ext_s_data_10   = 0x53 # R
	s_ext_s_data_11   = 0x54 # R
	s_ext_s_data_12   = 0x55 # R
	s_ext_s_data_13   = 0x56 # R
	s_ext_s_data_14   = 0x57 # R
	s_ext_s_data_15   = 0x58 # R
	s_ext_s_data_16   = 0x59 # R
	s_ext_s_data_17   = 0x5A # R
	s_ext_s_data_18   = 0x5B # R
	s_ext_s_data_19   = 0x5C # R
	s_ext_s_data_20   = 0x5D # R
	s_ext_s_data_21   = 0x5E # R
	s_ext_s_data_22   = 0x5F # R
	s_ext_s_data_23   = 0x60 # R
	s_mot_detect_status  = 0x61 # R
	s_i2c_slv0_do        = 0x63 # R/W
	s_i2c_slv1_do        = 0x64 # R/W
	s_i2c_slv2_do        = 0x65 # R/W
	s_i2c_slv3_do        = 0x66 # R/W
	s_i2c_mst_delay_ctrl = 0x67 # R/W
	s_signal_path_reset  = 0x68 # R/W
	s_mot_detect_ctrl    = 0x69 # R/W
	s_user_ctrl          = 0x6A # R/W
	s_pwr_mgmt_1         = 0x6B # R/W
	s_pwr_mgmt_2         = 0x6C # R/W
	s_fifo_counth        = 0x72 # R/W
	s_fifo_countl        = 0x73 # R/W
	s_fifo_r_w           = 0x74 # R/W
	s_who_am_i           = 0x75 # R
	# Compass.
	s_cmps_xout_l        = 0x4A # R
	s_cmps_xout_h        = 0x4B # R
	s_cmps_yout_l        = 0x4C # R
	s_cmps_yout_h        = 0x4D # R
	s_cmps_zout_l        = 0x4E # R
	s_cmps_zout_h        = 0x4F # R
	# Magneto
	s_cmps_wia           = 0x00 # R
	s_cmps_info          = 0x01 # R
	s_cmps_st1           = 0x02 # R
	s_cmps_hxl           = 0x03 # R
	s_cmps_hxh           = 0x04 # R
	s_cmps_hyl           = 0x05 # R
	s_cmps_hyh           = 0x06 # R
	s_cmps_hzl           = 0x07 # R
	s_cmps_hzh           = 0x08 # R
	s_cmps_st2           = 0x09 # R
	s_cmps_cntl          = 0x0a # R/W
	s_cmps_astc          = 0x0c # R/W
	s_cmps_i2cdis        = 0x0f # R/W
	s_cmps_asax          = 0x10 # R
	s_cmps_asay          = 0x11 # R
	s_cmps_asaz          = 0x12 # R

	# Interface to connect to I2C ports.
	iface = None
	iface_mag = None
	magneto_addr = 0x0c

	# TODO: If we're still using this sensor in the next deployment,
	# we should write the self test code.
	def __init__(self, addr):
		"""Sets the configuration. And turn everything off, it will be
		switched on when needed. The default configuration is a
		simplistic one:
			Clock: 8MHz integrated.
			Accelerometer's Full scale: 2g
			Gyro's Full scale: 200 Degrees/s
		"""
		self.addr = addr
		self.iface = i2c_iface(0, addr, invert_endian=False)

		# Activate bypass mode in order to access the magnetometer.
		self.iface.write_register(self.s_int_pin_cfg, 0x02)
		# Disable FIFO, enable master mode, to use magnetometer.
		self.iface.write_register(self.s_user_ctrl, 0x00)
		# Create a new writer for the bypassed magnetometer.
		self.iface_mag = i2c_iface(0, self.magneto_addr, invert_endian=False)

		# Ensure correct identity.
		self._check_9dof()
		# Sets everything off by default.
		self._all_off()

		# Sets up the correct scales.
		self._set_scales()

		# Perform self test.
		# It will print which sensors are failing.
		#self.self_tests()
		#self._calibrate_sensor()
		return

	def _del_(self):
		_all_off()
		return

	def _all_on(self):
		"""Stops sleep mode, and sensors standby."""
		self.iface.write_register(self.s_pwr_mgmt_1, 0x00)
		self.iface.write_register(self.s_pwr_mgmt_2, 0x00)
		return

	def _all_off(self):
		"""Sets the system on sleep, and sensors on standby."""
		self.iface.write_register(self.s_pwr_mgmt_1, 0x70)
		self.iface.write_register(self.s_pwr_mgmt_2, 0x3f)
		return

	def _check_9dof(self):
		me = self.iface.read_register(self.s_who_am_i)
		assert (me == self.addr)
		return

	def _set_scales(self):
		# Deactivates self tests, sets a 2g scale.
		self.iface.write_register(self.s_accel_config, 0x00)

		# Gyroscope self test off, sets 200 degrees/s scale.
		self.iface.write_register(self.s_gyro_config, 0x00)

		# Magnetrometer self test off, has a scale of +-1200uT.
		return

	def self_tests(self):
		"""Performs self-test. Reads data from sensor, averages, compares with
		with-self-test values."""
		def get_factory_trim():
			ret = {'accel':[], 'gyro':[]}

			self_test_x = self.iface.read_register(self.s_self_test_x)
			self_test_y = self.iface.read_register(self.s_self_test_y)
			self_test_z = self.iface.read_register(self.s_self_test_z)
			self_test_a = self.iface.read_register(self.s_self_test_a)

			st_acc = []
			st_acc.append(self_test_x >> 3 | (self_test_a & 0x30))
			st_acc.append(self_test_y >> 3 | (self_test_a & 0x30))
			st_acc.append(self_test_z >> 3 | (self_test_a & 0x30))

			st_gyr = []
			st_gyr.append(self_test_x & 0x1f)
			st_gyr.append(self_test_y & 0x1f)
			st_gyr.append(self_test_z & 0x1f)

			def acc_trim(v): return (4096*0.34) * (2.7058 ** ((float(v) - 1.0)/30.0))
			ret['accel'] = map(acc_trim, st_acc)

			def gyr_trim(v): return (25.0*131.0) * (1.046 ** (float(v)-1.0))
			ret['gyro'] = map(acc_trim, st_acc)

			print st_acc
			print st_gyr
			print ret
			for i in [0,1,2]:
				ret['accel'][i] = 100.0 + 100.0*(st_acc[i] - ret['accel'][0])/ret['accel'][i]
				ret['gyro'][i] = 100.0 + 100.0*(st_gyr[i] - ret['gyro'][0])/ret['gyro'][i]
			print ret
			return ret

		def self_test_error(no_st, with_st):
			"""Calculates difference between with-self-test values
			   and withouth self-test values."""
			# Gets all the nth elements of the elements of ar.
			def get_nth(n, ar): return map(lambda a: a[n], ar)

			# Get a list with 3 lists (values for the x, y and z axis).
			no_st_ord = [get_nth(i, no_st) for i in range(len(no_st[0]))]
			with_st_ord = [get_nth(i, with_st) for i in range(len(with_st[0]))]

			# Calculate avgs.
			no_st_avgs = map(lambda l: sum(l)/float(len(l)), no_st_ord)
			with_st_avgs = map(lambda l: sum(l)/float(len(l)), with_st_ord)
			print "No ST: ", no_st_avgs
			print "W/ ST: ", with_st_avgs

			# Calculate difference.
			err = [abs(with_st_avgs[i] - no_st_avgs[i]) for i in range(3)]
			print "err: ", err
			return no_st_avgs, err

		def accel_self_test():
			"""Performs self-test on accelerometer."""
			no_st = []
			for i in range(4):
				no_st.append(self._read_accel())
				time.sleep(0.05)

			# Turn on self-test.
			self.iface.write_register(self.s_accel_config, 0xe0)

			with_st = []
			for i in range(4):
				with_st.append(self._read_accel())
				time.sleep(0.05)
			avg,err = self_test_error(no_st, with_st)

			# Turn off self-test.
			self.iface.write_register(self.s_accel_config, 0x00)
			# We need the error to be between the +-14%.
			return map(lambda a: abs(a[1]) <= abs(a[0]*0.14), zip(avg, err))

		def gyro_self_test():
			"""Performs self-test on gyroscope."""
			no_st = []
			for i in range(4):
				no_st.append(self._read_gyro())
				time.sleep(0.05)

			# Turn on self-test.
			self.iface.write_register(self.s_gyro_config, 0xe0)

			with_st = []
			for i in range(4):
				with_st.append(self._read_gyro())
				time.sleep(0.05)
			avg,err = self_test_error(no_st, with_st)

			# Turn off self-test.
			self.iface.write_register(self.s_gyro_config, 0x00)
			# We need the error to be between the +-14%.
			return map(lambda a: abs(a[1]) <= abs(a[0]*0.14), zip(avg, err))

		def cmps_self_test():
			"""Performs self-test on magnetrometer."""
			# Activate and deactivate self test.
			self.iface_mag.write_register(self.s_cmps_cntl, 0x08)
			self.iface_mag.write_register(self.s_cmps_cntl, 0x00)
			return None

		# Turn stuff on before testing anything.
		#self._all_on()
		#fact_trim = get_factory_trim()
		#accel_st = accel_self_test()
		#gyro_st = gyro_self_test()
		#cmps_st = cmps_self_test()
		# Turn stuff off before testing anything.
		#self._all_off()

		# Do stuff when failing.
		#print accel_st
		#print gyro_st
		#print cmps_st
		return

	def _read_temp(self):
		"""Read temperature from the sensor."""
		t = self.iface.read_register(self.s_temp_out_h, self.s_temp_out_l)
		t = ct.c_short(t).value
		return (t/340) + 35

	def _read_accel(self):
		"""Read acceleration from the sensor. Returns values in g."""
		ret = []
		ret.append(self.iface.read_register_byte(self.s_accel_xout_h, self.s_accel_xout_l))
		ret.append(self.iface.read_register_byte(self.s_accel_yout_h, self.s_accel_yout_l))
		ret.append(self.iface.read_register_byte(self.s_accel_zout_h, self.s_accel_zout_l))
		# We get 2's complement 16 bits (short).
		ret = map(ct.c_short, ret)
		ret = map(lambda a: a.value, ret)
		# Multiply by sensitivity.
		ret = map(lambda n: float(n)/16384, ret)
		# Zero-g output: X,Y axes: +-80 mg. Z axes: +-150mg
		return ret

	def _read_gyro(self):
		"""Read angular velocity from the sensor. Returns degrees/s."""
		ret = []
		ret.append(self.iface.read_register_byte(self.s_gyro_xout_h, self.s_gyro_xout_l))
		ret.append(self.iface.read_register_byte(self.s_gyro_yout_h, self.s_gyro_yout_l))
		ret.append(self.iface.read_register_byte(self.s_gyro_zout_h, self.s_gyro_zout_l))
		# We get 2's complement 16 bits (short).
		ret = map(ct.c_short, ret)
		ret = map(lambda a: a.value, ret)
		# Multiply by sensitivity.
		ret = map(lambda n: float(n)/131, ret)
		return ret

	# Add bits in order to get the two's complement really working (13->16b)
	def _read_cmps(self):
		"""Read magnetic field velocity from the sensor. Returns uT."""
		# By default, sensor is down. We then need to switch it on, and
		# it will go back to power-down mode.
		self.iface_mag.write_register(self.s_cmps_cntl, 0x01)
		# If there's no data ready, don't return data.
		if (self.iface_mag.read_register(self.s_cmps_st1) == 0): return [0,0,0]
		ret = []
		# Read directly from the sensor.
		ret.append(self.iface_mag.read_register_byte(self.s_cmps_hxh, self.s_cmps_hxl))
		ret.append(self.iface_mag.read_register_byte(self.s_cmps_hyh, self.s_cmps_hyl))
		ret.append(self.iface_mag.read_register_byte(self.s_cmps_hzh, self.s_cmps_hzl))
		# We get 13bits using 2's complement
		# We append get the first bit and repeat it 3 times.
		for i in range(len(ret)):
			# If the number is negative, first bit is 1.
			if i < 0: ret[i] = (ret[i] & 0xfffff)|0xe000
			# Else just get the value.
			else: ret[i] = ret[i] & 0xffff
		ret = map(ct.c_short, ret)
		ret = map(lambda a: a.value, ret)
		# Multiply by sensitivity.
		ret = map(lambda n: float(n)*0.3, ret)
		return ret

	def get_data(self):
		"""Main function used to get all the real data.
			Temperature is in Celsius degrees.
			Acceleration is in g
			Gyro is in dps.
			Magnetometer is in uT"""
		self._all_on()
		ret = {"temp":   self._read_temp(),
				"accel": self._read_accel(),
				"gyro":  self._read_gyro(),
				"cmps":  self._read_cmps()}
		self._all_off()
		return ret
