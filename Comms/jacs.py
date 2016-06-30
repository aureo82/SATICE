#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Licensed under MIT (../LICENSE)

JACS.py - Just Another Communications Script

The program implements control over:
    - Hardware interface: serial channel of the modem and GPIO to power it on/off
    - Compression and split of archives to create smaller packets with CRC control
    - Query of status of Iridium
    - Send data as ASCII strings:
        - Through raw serial connection with normal data.
        - Through SBD.
        - Through PPP-FTP.
        - Through Rudics.

A configuration file is used containing the following setup:
  - MTU packet size: MTU (For data MTU<7kB, SBD MTU<340B)
  - Operation mode: OM [0] Raw, [1] SBD, [2] PPP-FTP, [3] Rudics.
  - Temp folder path: TF '/home/satice/new/temp'
  - Origin folder of the data to be transfered: OF

V0. Raul Bardaji & Oriol Sanchez, ICM-CSIC
"""
import fox #Access to the GPIO of the PCB to power the modem, import hardware library of your device (i.e. Raspberry Pi)
#import ablib #Acme boards library, udated library for fox kernel 3 and newer boards.
#import RPi.GPIO as GPIO
import send5.py as lv #Review
import time #Used to create sleeps
import serial #Required to use the serial ports, creation of sockets
import datetime #Timestamps require this library
import glob
import sys

# GLOBAL VARIABLES
debug=False #generic value for debug, updatable through the load configuration function.
confile="/home/satice/conf/coms.conf" #where your configuration file is


def logMe(home,log="Null",msg="Null")
	"""
	Writes a given message to a given log file.
	Example: 
		logMe(home,"coms",msg)
	Input:
		home: home path
		log: log file name
		message: message to be written
	Output: 
		None.
	"""
	wrote=False
	now = datetime.datetime.utcnow().strftime('%Y-%m-%d_%H:%M:%S') #timestamp, case we want to log
	f = open(home+'log/'+log".log", 'a')
	f.write(now+' '+msg+'\n')
	wrote=True
	f.close()

def read_config(confile):
	"""
	Reads configuration file 
	Input:
		confile: configuration file, if it does not exist the program creates it with default content. In this case
		the user has to manually update the phone number to call on the conf file.
	Output:
		mtu: Maximum Transfer Unit
		home: Home folder
		numphone: Phone number to call
		debug: Boolean, indicates debug as active
	"""
	if not(os.path.exists(confile)): #File does not exist, create new file.
		print("New file")
		os.system("echo MTU,PATH,PHONE,DEBUG >" + confile + "\n") #Load a default com setup
		os.system("echo 7000,/home/satice/,0123456789,False >>" + confile + "\n") #Load a default com setup
	cfile = open(confile,'r')
	headers = cfile.readline()#Discard first line, headers
	config = cfile.readline()
	cf=config.split(',')
	mtu=int(cf[0])
	home=str(cf[1])
	numphone=str(cf[2])
	debg=bool(cf[3])#Debug set to debg to differentiate function variable from global variable
	if (debg):
		print('MTU ' +str(mtu)+ ',HOME '+ str(home)+',NUMPHONE ' + str(numphone) +'\r')
		logMe(home,"coms",('MTU ' +str(mtu)+ ',HOME '+ str(home)+',NUMPHONE ' + str(numphone)))
	return mtu, home, numphone, debg

def modemT(mode=false,type="fox"):
    """
	Toggles power or sleep status of the modem through a digital output. A discharge cycle 
	is always done to be sure the power on cycle timing is always respected. This particular
	side requirement allows us to issue a hard reset by calling a modemT(true).
    Compatibility depends on access to digital outputs. For PC use this function is not required.
    Input: 
		mode: false for OFF, true for ON
		type: device type, to load the propper hardware control for digital outputs
    Output: 
        Return true/false for on/off case the power status is required.
	Default call: modemT(0) #Powers off, fox type..
    """
	#Generic switch off for 30 seconds.
	if (debug): 
		print('Modem OFF \r') #Debug is a global boolean variable.
		logMe(home,"coms","Modem OFF")
	if type=="fox": #Add cases for other devices...
		fox.Pin('J7.35','low') #For mk3 satice PCB with Fox Board microP unit
    time.sleep(30) #required to discharge charge pump on the modem, according to manufacturer.
	mON=False
	
	if mode==true: 
		if (debug): 
			print('Modem ON \r')
			logMe(home,"coms","Modem ON")
		if type=="fox":
			fox.Pin('J7.35','high') #For mk3 satice PCB with Fox Board microP unit
		time.sleep(5)
		mON=True
	return mON

def serial_ports(): 
    """ Lists serial port names.
	Outputs:
        EnvironmentError: On unsupported or unknown platforms
        Result: A list of the serial ports, compatible with AT, available on the system. 
				If no serial ports are available with a modem, returns false (To Be Implemented).
    """
    if sys.platform.startswith('win'):
        ports = ['COM%s' % (i + 1) for i in range(256)]
    elif sys.platform.startswith('linux') or sys.platform.startswith('cygwin'):
        # this excludes your current terminal "/dev/tty"
        ports = glob.glob('/dev/tty[A-Za-z]*')
    elif sys.platform.startswith('darwin'):
        ports = glob.glob('/dev/tty.*')
    else:
        raise EnvironmentError('Unsupported platform')
    result = []
    for port in ports:
        try:
            s = serial.Serial(port,baudrate=19200,timeout=2, write_timeout=220) 
			#Rest of parameters init by default, i.e. 8bit, no parity, 1 stop bit, no xon/off, no rtscts, no dsrdtr.
			#Update for 9Wire operation!!
			# Wait for hot start
            time.sleep(1)
			respuesta = query(ser) #query without 2nd parameter does an AT query
			if respuesta != 'OK':
				ser.close()
			else:
				s.close()
				result.append(port)
        except (OSError, serial.SerialException):
            pass
	if (debug): 
		if (len(result) ==0): 
			msg='No available ports'
			print(msg)
			logME(home,"coms",msg)
		else:
			print('Available ports:', result)
			logMe(home,"coms",('Available ports:', result))
		
	#Case result is empty...
	if (len(result) ==0): #If no AT ports in the list
		return False #vector with serial ports with AT command friendly devices
		else return result
	
	
def connect(device):
    """
	This function sets a serial socket to a given serial port and 
	ensures AT commands are accepted by the serial host.
    Compatible with SBD and data modems
    Input: Serial port to connect
    Output: 
        False: AT response was not possible
        ser: serial socket for python
    """
    # Open serial socket to device, baudrate may change. 
	# Default on the modems is 19200, you can check/set it with sCBST()
    ser = serial.Serial(port=device,baudrate=19200,timeout=2, writeTimeout=220)
    if ser.isOpen()== False:
        return False
    # Wait a second
    time.sleep(1) #This wait time could be increased up to 5s if required..
    # Again, test for AT response
    answer = query(ser)
    if answer != 'OK':
        ser.close()
        return False
    else: #This serial socket matches an AT capable system
		ser.flushInput() #Clear the input buffer
		ser.flushOutput() #Clear the output buffer
		if (debug):
			print('Connected to the modem on '+ str(device) + '\r')
			logMe(home,"coms",('Connected to the modem on' + str(device)))
        return ser

def disconnect(ser):
	"""
	This function disconnects the serial socket given as a parameter.
	Input: Serial port to disconnect
	Output: Succes of serial socket closure
	"""
	out=True
	try: 
		ser.close()
	except:
		#I should flush the socket and delete the port lock file in this case.
		out=False
	if (debug):
		print('Disconnected from the modem on '+ str(device) + '\r')
		logMe(home,"coms",('Disconnected from the modem on' + str(device)))
	return out
	
def writeMod(ser,frase,wait=1):
    """
	This function handles the serial input from system to modem
	and gets the serial output from modem to system.
    Compatible with SBD and data modems
    Input: 	Serial port to connect
			Input command, usually AT commands
			wait, timeout by default 1s
    Output: 
        False: AT response was not possible
	Default call: writeMod(ser,frase);
	
	***-> Need feedback about the encoding stuff, is it really necessary? 
	"""
	#By default wait time is 1 second
	ser.write(bytes(frase, encoding="UTF-8"))
    out = ''
    # let's wait 'espera' second before reading output (let's give device time to answer)
    time.sleep(wait)
    while ser.inWaiting() > 0:
		out = ser.read(ser.inWaiting()).decode(encoding='UTF-8')
    if out == '':
        return 'No answer'
    else:
        # Modem returns the issued command by default (can be disabled by ATE=0), 
		# next line is the answer to issued command. This soft works with echo enabled.
		# The order is \r\nIssuedComm\r\nanswer\r\nblank\r\nok\r\n !!!!
        out_ = out.split('\r\n')
        return out_[2]
def query(ser,phrase='AT\r\n',splitch=' '): 
     """
	This function issues an AT command through a serial port,
	waits for an answer and splits the string output through a split
	character (to get rid of unwanted info)
    Compatible with SBD and data modems
    Input: 	Serial port to connect
			AT command to be issued, default is 'AT' with carriage return
			Split character f.i.(';'..','..':'), default is not used
    Output: 
        answer: first grade decoded answer, may need further split if answer
		is a vector of status codes.
	Default call: query(ser); does an AT inquiry to the modem.
	"""
	if (phrase != 'AT\r\n'):
      tao=9 #The wait time if the command ain't a simple AT
    else: tao=1
    answer = writeMod(ser,phrase,tao)
	# DECODE SUBROUTINE??? like answer=decode(answer)
	# get answer from escape command +++, command to get again in data mode...
    if answer != 'No answer\n':  
      if splitch=' ': #This splitch is done in case the answer is either a simple OK or a complex
		# multianswer without a label marker (i.e. answer from CREG? returns <mode,code,cell,area>)
		# also, in case we issue a configuration command, answer may be only an OK.
        answer= answer.split(splitch)[0]
      else:       #Case I want the answer for any other command
        answer= answer.split(splitch)[1] #Using splitch as division character, I take the second field
	return answer
def rFS(ser):
    """
    Restore factory settings. 
    Input: 
        ser: Serial socket
    Output:
        Modem answer
	"""
    frase = 'AT&F0\r\n'
    answer = query(ser,frase,"")
	if answer=='OK\n' and debug: #both true
		print("Factory settings restored \r") #Uncomment for debug
		logMe(home,"coms",('Factory settings restored'))	
    return answer 
def sFlowC(ser,opt=0):
    """
	Set flow control (RTS/CTS) on the modem
	Supported on 9522B and 9602, it is recommended to use flow control.
	Seems that this functionallity was added posterior to the design of the modems
	as a backwards compatibility functionality, seems to be pretty flacky thus
	9 wire serial interface is recommended.
    Input: 
        ser: serial port socket
		opt: Option, 0 to disable, 1 to enable. Disabled by default.
    Output:
        Modem answer
    """
	frase='AT&K'+str(opt)+'\r\n'
    #frase = 'AT&K0\r\n'
    answer = query(ser,frase,"")
	if answer=='OK\n' and debug: #both true
		if opt=0:		
			print("Flow control (RTS/CTS) dissabled")
			logMe(home,"coms",('Flow control (RTS/CTS) dissabled'))	
		else: #Case opt=1		
			print("Flow control (RTS/CTS) enabled")
			logMe(home,"coms",('Flow control (RTS/CTS) enabled'))		
	if answer!='OK\n'
		answer=False
	else:
		answer=True
	return answer
	
def sDTR(ser,opt=0):
    """
    Set DTR. 
    Input: 
        ser: Serial socket
		opt: Option, 0 to disable, 1 to enable. Disabled by default.
    Output:
        answer: Boolean marking succes of operation
    """
	frase='AT&D'+str(opt)+'\r\n'
    #frase2 = 'AT&D0\r\n'
    answer = query(ser,frase,"")
	if answer=='OK\n' and debug: #both true
		if opt=0:		
			print("DTR dissabled \r")
			logMe(home,"coms",('DTR dissabled'))	
		else: #Case opt=1		
			print("DTR enabled \r")
			logMe(home,"coms",('DTR enabled'))	
	if answer!='OK\n'
		answer=False
	else:
		answer=True
    return answer

def nR(ser,ringNumber = 1):
    """
	Sets the number of rings before answering
    Input: 
        ser: Serial socket
		ringNumber: number of rings, default 1
    Output:
        answer: Boolean marking success of operation
    """
    frase = 'ATS0 = {}\r\n'.format(ringNumber)
    answer = query(ser,frase,"")
	if answer=='OK\n' and debug:
		msg="Number of rings before answering set to {} ring(s)".format(ringNumber)
		print(msg+'\r') 
		logMe(home,"coms",msg)
	if answer!='OK\n'
		answer=False
	else:
		answer=True
    return answer

def sAcP(ser,opt=0):
    """
    Saves current setup as active profile, acording to AT command reference manual
	this is not supported on 9601 and 9602 SBD modems. In the same manual, pg 136 
	both commands are used in a SBD modem (probably a 9602..)
    Input: 
        ser: Serial socket
    Output:
        answer: Boolean, marking success of operation
    """
	frase='AT&W'+str(opt)+'\r\n' #Saves as profile opt (0)
    #frase = 'AT&W0\r\n'
    answer = query(ser,frase,"")
	if answer=='OK\n':
		frase='AT&Y'+str(opt)+'\r\n' #Saves profile opt (0) as power-up default
		answer = query(ser,frase,"")
		if answer=='OK\n' and debug:
		    msg = 'Saved setup as profile {} and power up default setup'.format(opt)
			print(msg+'\r')
			logMe(home,"coms",msg)	
	if answer!='OK\n'
		answer=False
	else:
		answer=True
    return answer

def sCREG(ser,type=0):
    """
    Sets the Carrier Registration type
    Input: 
        ser: Serial socket
		type: CREG typology::
				0 - Default, disable network registration unsolicitud result code (NRURC)
				1 - Enable NRURC
				2 - Enable NRURC with Location Area Code
				Comment: on the 9522b type 0 setup returns the same stat codes as type 1
    Output:
        answer: boolean according to success of operation
    """
	frase='AT&CREG='+str(type)+'\r\n'
    answer = query(ser,frase," ")
	if answer=='OK\n' and debug:
		    msg = 'Carrier Registration set to {}'.format(type)
			print(msg+'\r')
			logMe(home,"coms",msg)	
	if answer!='OK\n'
		answer=False
	else:
		answer=True
    return answer	
 
def idMOD(ser):
	"""
	Input: Serial port socket
	Ouput: Modem model
	"""
	frase='AT+CGMM='+str(type)+'\r\n'
    answer = query(ser,frase," ")
	if and debug:
		msg = 'Modem model: {}'.format(answer)
		print(msg+'\r')
		logMe(home,"coms",msg)	
	#Set also to a global variable? 
    return answer	
	 
def sCBST(ser,opt=71):
    """
    Sets the Carrier Bearer service type
    Input: 
        ser: Serial socket
		opt: Carrier Bearer service type [0-7, 65,66,68,70,71]
				0 is autobauding
				7 9600bps v.32 (default on modem and PPP)
				71 9600bps v.110 (Used by default on Rudics)
    Output:
        answer: boolean according to operation success
    """
	frase='AT&CBST='+str(opt)+',0,1\r\n'
    answer = query(ser,frase," ")
	if answer=='OK\n' and debug:
		    msg = 'Carrier Bearer Service set to {}'.format(opt)
			print(msg+'\r')
			logMe(home,"coms",msg)	
	if answer!='OK\n'
		answer=False
	else:
		answer=True
    return answer	
	
def iSSet(ser):
    """
    Used with data modems on Satice, initial setup of the modem
    Input: 
        ser: Serial socket
    Output:
        boolean answer, true for success false for not succesfull.
    """
	manswer=True #by default consider setup status to ok
	answer = rFS(ser) #restore factory settings
	if not(answer): manswer=False #false
	time.sleep(0.5)	
    answer = sDTR(ser) #Set DTR, default, default is disabled
	if not(answer): manswer=False #false
	time.sleep(0.5)
    answer = sFlowC(ser) #Set flow control, default is disabled
	if not(answer): manswer=False #false
	time.sleep(0.5)
	modem= idMOD(ser) #returns "9522B" for 9522B
	#if modem in modems: return True, else set as SBD...
	time.sleep(0.5)
	#Following setup is "model" sensible
	if modem=="9522B"  or modem=="A3LAr" or modem=="A3LA-r" or modem=="9523":
		#Update if statement with a is in dictionary: f.i. if modem in modems...
		answer = sCBST(ser)    #Set Carrier Bearer Service to default 71,0,1
		if not(answer): manswer=False #false
		time.sleep(0.5)
		answer = nR(ser) #Set number of rings to default (1)
		if not(answer): manswer=False #false
		time.sleep(0.5)

	answer = sAcP(ser) #Save as active configuration 
	if not(answer): manswer=False #false
	time.sleep(0.5)
	return manswer #Otherwise we can return False and break the function as soon as one of the setups fails
	
def dSIMr(answer,mode="data"):
    """
    Decodes output from AT+CREG? command, useful for debug or log
    Input:
        answer: int con la info a decodificar
		mode: data / sbd...
    Output: 
        Returns the meaning of the code in an ASCII string
    """
	if mode=="sbd" or mode=="SBD":
		if answer == 0:
			return 'ISU Detached.'
		elif answer == 1:
			return 'ISU attached but not registered, bad location.'
		elif answer == 2:
			return 'Registered, home network.'
		elif answer == 3:
			return 'Registration denied.'
	if mode=="reg_err":
		#Gateway reported
		if answer == 0:
			return 'No error.'
		elif answer == 2:
			return 'Session completed, Location Update not accepted'
		elif (answer >= 3) and (answer <= 14):
			return 'Reserved, Location Update failure.'
		elif answer==15:
			return 'Access is denied'
		#ISU reported	
		elif answer==16:
			return 'ISU has been locked and may not make SBD calls (see +CULK command).'
		elif answer==17:		
			return 'Gateway not responding (local session timeout).'
		elif answer==18:		
			return 'Connection lost (RF drop).'
		elif answer==19:
			return 'Link failure (A protocol error caused termination of the call).'
		elif ((answer >= 20) and (answer <= 31)) or ((answer >= 39) and (answer <= 63)): 
			return 'Reserved, but indicate failure if used.'
		elif answer==32:			
			return 'No network service, unable to initiate call.'
		elif answer==33:				
			return 'Antenna fault, unable to initiate call.'
		elif answer==34:	
			return 'Radio is disabled, unable to initiate call (see *Rn command).'
		elif answer==35:				
			return 'ISU is busy, unable to initiate call.'
		elif answer==36:	
			return 'Try later, must wait 3 minutes since last registration.'
		elif answer==37:	
			return 'SBD service is temporarily disabled.'
		elif answer==38:	
			return 'Try later, traffic management period (see +SBDLOE command)'
		elif answer==64:	
			return 'Band violation (attempt to transmit outside permitted frequency band).'
		elif answer==65:	
			return 'PLL lock failure; hardware error during attempted transmit.'	
	else :
		if answer == 0:
			return 'Not registered, ME is not currently searching a new operator to register to.'
		elif answer == 1:
			return 'Registered, home network'
		elif answer == 2:
			return 'Not registered, but ME is currently searching a new operator to register to.'
		elif answer == 3:
			return 'Registration denied.'
		elif answer == 4:
			return 'Unknown.'
		elif answer == 5:
			return 'Registered, roaming.'
		
def SIMr(ser,mode="data",type="0"):
    """
    Inquires about the status of the card, by default the routine uses the data modem query.
    Input: 
        ser: Serial socket
		mode: data / sbd...
		type: CREG typology::
				0 - Default, disable network registration unsolicitud result code (NRURC)
				1 - Enable NRURC
				2 - Enable NRURC and location info.<n>,<stat>[,<lac>,<ci>]
					Being: 	<lac> location area code
							<ci> cell identifier (not used in Iridium, actually if implemented
							could be a nice way to log satellite health...)
				Comment: on the 9522b type 0 setup returns the same stat codes as type 1
    Output:
        Modem answer: 0-5. Use dSIMr to decode meaning.
    """
	if mode=="sbd" or mode=="SBD":
		answer= query(ser,'AT+SBDREG?\r\n',':')
		#This would answer only with status code.
		
		#UPDATE::
		#+SBDREG[=<location>] means we can add location update instead of trusting the Iridium triangulation
		# That way we also save the space of the location data on the sbd message.
		#<location> has format: [+|-]DDMM.MMM,[+|-]dddmm.mmm , First field is latitude, second is longitude. (D)egrees(M)inutes.Thousandsof(M)inutes
		#A user can send an MO SBD message and register at the same time by using the +SBDIX command	
		#For example,
			#AT+SBDIX=5212.483,-00007.350
			#corresponds to 52 degrees 12.483 minutes North, 0 degrees 7.35 minutes Wes
		#--->if location used within call a second code will be answered,reg_error
		
	else: 
		answer = sCREG(ser,type)
		answer = query(ser,'AT+CREG?\r\n',':')
		#Answer will be <n>,<stat> or <n>,<stat>[,<lac>,<ci>]
		answer = answer.split(',')
		if len(answer)>2: #long answer with location area code
			lac=answer[2]
		answer= answer[1] #Done to return the same as with SBD mode.
	#What happens if my answer is 'no answer?'
    if answer == 'No answer': #In this case I consider not searching neither registered
		answer = 0 
	#Finally, how do I return lac and stat if I use the enhaced CREG---???	
    return answer
	
def ICCID(ser):
    """
	Checks for the Carrier Integrated Circuit Card IDentifier, defines the SIM card
    Input: 
        ser: Serial socket
    Output:
        Modem answer: the CICCID, f.i. 8988169312004****** 
    """    
	answer = query(ser,'AT+CICCID\r\n',' ')#splitch is empty as the answer is the id code itself
	if debug:
		    msg = 'CICCID is {}'.format(answer)
			print(msg+'\r')
			logMe(home,"coms",msg)	
    return answer

def uSIMP(ser,pin = '1111'):
    """
    Unlocks SIM card with the Pin code
    Input: 
        ser: Serial socket
        pin: Pin code, default 1111 in Irirdium cards
    Output:
        answer: Boolean according to operation success
    """   
    phrase = 'AT+CPIN="{}"\r\n'.format(pin)
	#answer = query(ser,phrase,' ')
	answer= query(ser,phrase) #as I am expecting ok or no answer, this call should work (without splitch)
	if answer=='OK\n' and debug:
		msg = 'Sim card unlocked with pin='.format(pin)
		print(msg+'\r')
		logMe(home,"coms",msg)	
	
	if answer!='OK\n'
		answer=False
	else:
		answer=True
	return answer
	
def dSIMP(ser,pin = '1111',opt=0):
    """
    Removes pin code requirement (disables pin code), current pin required.
    Input: 
        ser: Serial socket
        pin: Current pin code: default 1111
		opt: [0,1] to disable/enable pin code.
    Output:
        answer: Boolean according to operation success
    """
    phrase = 'AT+CLCK="SC",'+str(opt)+',"{}"\r\n'.format(pin)
	answer = query(ser,phrase,' ')
	if answer=='OK\n' and debug:
		msg = 'Sim card pin requirement disabled, pin used='.format(pin)
		print(msg+'\r')
		logMe(home,"coms",msg)	
	
	if answer!='OK\n'
		answer=False
	else:
		answer=True
    return answer
	
def sMSBD(ser,msg):
    """
    Sends a text message to the SBD modem's Mobile Originated buffer
	in order to send this message a SBDI session must be issued.
    Input: 
        ser: Serial socket
        msg: Body of the message we want to issue
    Output:
        answer: Boolean according to operation success
	"""
    frase = 'AT+SBDWT='+msg+'\r\n'
    answer = query(ser,frase,"")
	if answer=='OK\n' and debug:
		msg = 'Output buffer updated to: '.format(msg)
		print(msg+'\r')
		logMe(home,"coms",msg)	
	if answer!='OK\n'
		answer=False
	else:
		answer=True
    return answer
	
#Add binary bMSBD() with AT+SBDW=<message length>
#catch Ready as answer
#send binary data
#catch 0 answer for succesful write on output buffer
	
def coverageTest(ser,tout=300,mode="data"):
    """
	This function performs a coverage test, if succesful then tries to ask 
	for sim card registration status. If sim is registered on the network 
	the function will return 1, otherwise it will return 0 as status code.
	To enhance logging output uncomment logME() call.
    Compatible with SBD and data modems -> double check, please..
    Input: 
		ser: Serial port socket
		tout: Timeout for the test (default 300s)
		mode: type of modem [SBD or Data]. - > Future work, extract this info from the modem itself.
    Output: 
        status: Multiple ouput
				1st field:	0 for enough coverage/not registered. 1 for registered and with coverage.
				2nd field: coverage [0-5].
				3rd field: registry status code (use dSIMr(code) ) to decode message.
    """
	print 'Initializing modem:\n'
    timeout = time.time() + tout   # By default 300s
    status=(False,0,0) #Init return vector
    while time.time()<timeout: #For 5 minutes
      coverage = query(ser,'AT+CSQ\r\n',':') #In this case query will return a number, 0 to 5.
	  	if debug:
		    msg = 'Coverage is {} out of 5'.format(coverage)
			print(msg+'\r')
			logMe(home,"coms",msg)	
      status[1]=coverage
	  if coverage>3:
        print 'Coverage acceptable\n'
		regCode = SIMr(ser)
		status[2] = regCode
		if debug:
			msg=dSIMr(regCode,mode)
			print(msg)
			logMe(home,"coms",msg)	
        if regCode==1:
          print 'SIM registered\n'
		  status[0]=False
          break #Don't wait for the timeout once we are registered
    return status
	
def sbdMessage(ser,input="nop",lat="nop",lon="nop")
	"""
    Handles SBDI session, receives incomming message if available on the Mobile
	Terminated buffer and sends message if available in the Mobile Originated buffer.
	in order to send this message a SBDI session must be issued.
	Optionally an extended SBD session may be initiated, by adding location data.
    Input: 
        ser: Serial socket
        input: Body of the message we want to issue
		lat: Latitude [+|-]DDMM.MMM , where:
			DD Degrees latitude (00-89)
			MM Minutes latitude (00-59)
			MMM Thousandths of minutes latitude (000-999)
		lon: Longitude [+|-]dddmm.mmm
			ddd Degrees longitude (000-179)
			mm Minutes longitude (00-59)
			mmm Thousandths of minutes longitude (000-999)
    Output:
        The modem answer, OK case succesful writting in SBD output buffer
	"""
	location=str(lat)+','+str(lon)
	answer=query(ser,'AT+SBDD2\r\n') #Clear mobile originated and terminated buffer
	if input<>'nop':  #If its not a nop, then write message to the mobile originated buffer
		respuesta = sMSBD(ser,input,"") 
	for i in range (0,10) #Ten tries
		if (lat=="nop" or lon=="nop"): #Case no location data is provided
			RXstr=query(ser,'AT+SBDI',':') #Returns something like "3,0,0,0,0,0" from "+SBDI:3,0,0,0,0,0"
		else:
			RXstr=query(ser,'AT+SBDIX='+location,':') #Returns something like "3,0,0,0,0,0" from "+SBDIX:3,0,0,0,0,0"
		if len(RXstr)<8 : RXstr="3,0,0,0,0,0" #Double check that the answer is of desired length, othersiwe use a default output
		RXfrags=RXstr.split(',',5)
		#decodeStatusSBD(RXstr) #Uncomment to see definition of status messages, or ad if debug=true 
		MO_Status=RXfrags[0] 
		#review MO code 13, gateway reported  that the session did not complete for not entirely transfered msges
		#If this happens, then 
		MT_Status=RXfrags[2]
		if MT_status == 1 : #Not sure I need ten tries if message is already in the MT buffer...
			For i in range (0,10) #Ten tries
				RXstr=query(ser,'AT+SBDRT',"*")#Read message
				RX_message=RXstr.split('!') 
				#This means I can receive multiple commands: f.i. RESET!LEFT!RIGHT!UP!SLEEP!...
				#A decoding answer routine may be required to asign each command to a desired task
				#Would I need to strip() all vector cells? case there are empty spaces inside?
				
		if MO_Status <=1 or input == 'nop': break #Case correctly sent or input message was 'nop' message
		else : time.sleep(10) #wait 10 seconds... and try to send it again.
		
def decodeStatusSBD(answer,mode="X"):
    """
    Decode SBD status according to AT command reference manual, answer is already splited in RXfrags=RXstr.split(',',5),
	being RXstr=query(ser,'AT+SBDI',':')
    Input:
        answer: code to be decoded 	<MO status>,<MOMSN>,<MT status>,<MTMSN>,<MT length>,<MT queued>
		mode: default is X for eXtended (SBDIX output), use mode n,N or others for (SBDI output)
	Output: 
        Prints meaning of code
    """
	#Use of strip() to get rid of empty spaces inside the vector cells, shouldn't be necessary...
	if mode!="X":
		if answer[0].strip() == '0':
			MOStatus = 'No SBD message to send from the ISU.'
		if answer[0].strip() == '1':
			MOStatus = 'SBD message successfully sent from the ISU to the GSS.'
		if answer[0].strip() == '2':
			MOStatus = 'An error occurred while attempting to send SBD message from ISU to GSS.'
	else:
		if answer[0].strip() == '0':
			MOStatus = 'MO message, if any, transferred successfully.'
		elif answer[0].strip() == '1':
			MOStatus = 'MO message, if any, transferred successfully, but the MT message in the queue was too big to be transferred.'
		elif answer[0].strip() == '2':
			MOStatus = 'MO message, if any, transferred successfully, but the requested Location Update was not accepted.'
		elif answer[0].strip() == '3' or answer[0] == '4':
			MOStatus = 'Reserved, but indicate MO session success if used.'
		elif answer[0].strip() == '5' or answer[0] == '6' or answer[0] == '7' or answer[0] == '8':
			MOStatus = 'Reserved, but indicate MO session failure if used.'
		elif answer[0].strip() == '10':
			MOStatus = 'GSS reported that the call did not complete in the allowed time.'
		elif answer[0].strip() == '11':
			MOStatus = 'MO message queue at the GSS is full.'
		elif answer[0].strip() == '12':
			MOStatus = 'MO message has too many segments.'
		elif answer[0].strip() == '13':
			MOStatus = 'GSS reported that the session did not complete.'
		elif answer[0].strip() == '14':
			MOStatus = 'Invalid segment size.'
		elif answer[0].strip() == '15':
			MOStatus = 'Access is denied.'
		elif answer[0].strip() == '16':
			MOStatus = 'ISU has been locked and may not make SBD calls (see +CULK command).'
		elif answer[0].strip() == '17':
			MOStatus = 'Gateway not responding (local session timeout).'
		elif answer[0].strip() == '18':
			MOStatus = 'Connection lost (RF drop).'
		elif answer[0].strip() == '19':
			MOStatus = 'Link failure (A protocol error caused termination of the call).'
		elif answer[0].strip() == '32':
			MOStatus = 'No network service, unable to initiate call.'
		elif answer[0].strip() == '33':
			MOStatus = 'Antenna fault, unable to initiate call.'
		elif answer[0].strip() == '34':
			MOStatus = 'Radio is disabled, unable to initiate call (see *Rn command).'
		elif answer[0].strip() == '35':
			MOStatus = 'ISU is busy, unable to initiate call.'
		elif answer[0].strip() == '36':
			MOStatus = 'Try later, must wait 3 minutes since last registration.'
		elif answer[0].strip() == '37':
			MOStatus = 'SBD service is temporarily disabled.'
		elif answer[0].strip() == '38':
			MOStatus = 'Try later, traffic management period (see +SBDLOE command).'
		elif answer[0].strip() == '64':
			MOStatus = 'Band violation (attempt to transmit outside permitted frequency band).'
		elif answer[0].strip() == '65':
			MOStatus = 'PLL lock failure; hardware error during attempted transmit.'
		else:
			MOStatus = 'Reserved, but indicate failure if used.'
			
	# This part is common to SBDI, SBDIX, SBDIXA
	if answer[2].strip() == '0':
		MTStatus = 'No new SBD message to be received from Iridium Network.'
	elif answer[2].strip() == '1':
		MTStatus = 'SBD message successfully received from Iridium Network.'
	elif answer[2].strip() == '2':
		MTStatus = 'An error occurred while attempting to perform a mailbox check or receive a message from the Iridium Network.'	
	print('MO status:',MOStatus)  
    print('MOMSN:',answer[1].strip())
    print('MT status:',MTStatus)    
    print('MTMSN:',answer[3].strip())
    print('MT length:',answer[4].strip())
    print('MT queued:',answer[5].strip())	

def Dcall(ser,number):
    """
    Data call to Iridium phone. 
    Input: 
        ser: Serial socket
        number: phone number, f.i. 8816765***** (note that to this number, voice channel would be 8816763*****)
    Output:
         Modem answer: Usually OK or NO ANSWER. In this case if call is succesful the modem will go into data mode.
    """
	#I usually used ATD+Number, seems you can use ATDTNumber or ATDNumber
	#phrase = 'ATD +{}\r\n'.format(number) #We used this one with PPP setup
    phrase = 'ATDT{}\r\n'.format(number) 
	if debug:
		msg='Dialling: {} ...'.format(number)
		print(msg+'\r')
		logMe(home,"coms",msg)	
	res1 = query(ser,phrase,' ')
	#Same thing as the one before, I could just return a boolean value to mark success.
	#Case I succed I'll be in data mode.
	if "Open" in res1 and "CARRIER" not in res1:
		connected = True
	else:
		connected = False		
	if debug and connected:
		msg='Connected to : {}'.format(number)
		print(msg+'\r')
		logMe(home,"coms",msg)
	time.sleep(1)  #give the serial port sometime to receive the data	
    return res1
	
def callR(ser,tlf):
	'''
	Does the same as Dcall()
	'''
	connected = False
	while(connected == False): #Add a timeout so the modem is not trying to call for more than half an hour for instance?
		ser.write("ATDT+"+str(tlf)+"\r\n")
		time.sleep(0.5)  #give the serial port sometime to receive the data
		res1 = ""	
		while True: 
			response = ser.readline()
			print(response.strip())
				res1+=response.strip()

			# wait for new data after each line
				timeout = time.time() + 10
				while not ser.inWaiting() and timeout > time.time():
						pass
				if not ser.inWaiting():
					break 
					
		# frase='ATDT+'+str(tlf)+'\r\n'   #Does the same as the code before.
		# res1 = query(ser,frase," ")

		if "Open" in res1 and "CARRIER" not in res1:
			connected = True
		else:
			connected = False		
	time.sleep(1)  #give the serial port sometime to receive the data	
	return connected
	
#### MAIN PROGRAM FOR TEST.   
if __name__ == '__main__':
	#LOAD CONF FILES
	mtu,home,numphone,debug=read_config(confile):	
	#COMBLOCK
    #On sequence for the modem including setup.
    modemT(True,"Fox") #Powers on the modem, case GPIO is used. IMPLEMENTED	
	listS = serial_ports() #List available AT ports
	if not(listS): print("No AT ports available")
	ser = connect(listS[0]) #Connect to the first one
	resp = iSSet(ser) #Initial setup of the modem
	#dSIMP(ser)	#Unlock sim card, only first time a new SIM is used.
    status = coverageTest(ser) #See if registered with coverage, tries for 300 seconds 
		if (debug):
		#print(dSIMr(status[1])) #Use a log function !!! COVERAGE
		msg=dSIMr(status[1])
		logMe(home,"coms",msg)
		#print(dSIMr(status[2])) #Use a log function !!! REGISTRY STATUS
		msg=dSIMr(status[2])
		logMe(home,"coms",msg)
	if (status[0]): #if status is true (coverage and registry)
	#Call gateway
	connected=callR(ser,tlf)	
	
	#FILEBLOCK
	if connected:
		# read all files in directiory and try to send them
		logMe(home,"coms","Connected to RUDICS Gateway")
		dir1 = "/home/satice/new/shortlist";
		lv.readFiles(dir1);

	#END COMBLOCK
	logMe(home,"coms","Disconnected from network")
	disconnect(ser) #Close serial port
	modemT(False,"Fox") #Powers off the modem.
	sys.exit() #Kill the program
	
	

