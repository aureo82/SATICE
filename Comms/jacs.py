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
import time #Used to create sleeps
import serial #Required to use the serial ports, creation of sockets
import datetime #Timestamps require this library
import glob
import sys

#I'll eventually load this data from a configuration file. 
mtu=1000
path='/home/satice/testbed'

# One power routine to fit all systems, by default the rountine calls
# fox board based functions, case a pc is used the modem will probably be powered on at all
# time, thus this function will have no effect on it.
def modemT(mode=false,type="fox"):
    """
	Toggles power or sleep status of the modem through a digital output. 
    Compatible with SBD and data modems
    Input: 
		mode: false for OFF, true for ON
    Output: 
        False: AT response was not possible
        ser: serial socket for python
    """
	#Generic switch off for 30 seconds.
	print 'Modem OFF'
	case type=="fox": #Add cases for other devices...
		fox.Pin('J7.35','low') #For mk3 satice PCB with Fox Board microP unit
    time.sleep(30) #required to discharge charge pump on the modem, according to manufacturer.
	
	if mode==true: 
		print 'Modem ON'
		case type=="fox":
			fox.Pin('J7.35','high') #For mk3 satice PCB with Fox Board microP unit
		time.sleep(5)
	

def serial_ports(): #returns available serial ports
    """ Lists serial port names. Outputs:
        raises EnvironmentError:
            On unsupported or unknown platforms
        returns:
            A list of the serial ports, compatible with AT, available on the system
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
            s = serial.Serial(port,baudrate=19200)
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
    return result #vector with serial ports with AT command friendly devices

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
	# Default on the modems is 19200, you can check it with AT+CBST? 
    ser = serial.Serial(port=device,baudrate=19200)
    if ser.isOpen()== False:
        return False
    # Wait a second
    time.sleep(1)
    # Again, test for AT response
    answer = query(ser)
    if answer != 'OK':
        ser.close()
        return False
    else:
        return ser


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
    ser.write(frase)
	#ser.write(bytes(frase, encoding="UTF-8"))
    out = ''
    # let's wait 'espera' second before reading output (let's give device time to answer)
    time.sleep(wait)
    while ser.inWaiting() > 0:
        out += ser.read(1)
		#out = ser.read(ser.inWaiting()).decode(encoding='UTF-8')
    if out == '':
        return 'No answer'
    else:
        # Modem returns the issued command, next line the answer.
        # Up next a blank line is sent and finally an OK\r\n if everything goes ok.
        # If only an AT command has been issued, the answer is only OK\r\n
        out_ = out.split('\r\n')
        return out_[2]#The order is \r\nIssuedComm\r\nanswer\r\nblank\r\nok\r\n !!!!
		
def query(ser,phrase='AT\r\n',splitch=''): 
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
      if (phrase=='AT\r\n') or splitch='': #Self explanatory, anyway answer for command "AT"
        answer= answer.split(splitch)[0]
      else:       #Case I want the answer for any other command
        answer= answer.split(splitch)[1] #Using splitch as division character, I take the second field
	#*****************************
	# More elegant solution?
	# (answer != 'No answer\n') and (answer != 'OK\n'): 
    #    answer= answer.split(splitch)[1] #Using splitch as division character, I take the second field
	# else: 
    #    answer= answer.split(splitch)[0]
	#****************************
 return answer

	
def dFlowC(ser):
    """
	Disables flow control (RTS/CTS) on the modem
	Supported on 9522B and 9602, it is recommended to use flow control.
	Seems that this functionallity was added posterior to the design of the modems
	as a backwards compatibility functionality, seems to be pretty flacky thus
	9 wire serial interface is recommended.
    Input: 
        ser: serial port socket
    Output:
        Modem answer
    """
    frase = 'AT&K0\r\n'
    answer = query(ser,frase,"")
	#if answer=='OK\n':
	#	print "Flow control (RTS/CTS) dissabled" #Uncomment for debug	
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
	#if answer=='OK\n':
	#	print "Factory settings restored" #Uncomment for debug
    return answer

def dDTR(ser):
    """
    Disable DTR. 
    Input: 
        ser: Serial socket
    Output:
        Modem answer
    """
    frase = 'AT&D0\r\n'
    answer = query(ser,frase,"")
	#if answer=='OK\n':
	#	print "DTR dissabled" #Uncomment for debug
    return answer

def nR(ser,ringNumber = 1):
    """
	Sets the number of rings before answering
    Input: 
        ser: Serial socket
		ringNumber: number of rings, default 1
    Output:
        Modem answer
    """
    frase = 'ATS0 = {}\r\n'.format(ringNumber)
    answer = query(ser,frase,"")
	#if answer=='OK\n':
	#	print "Rings before answering set to {} ring(s)".format(ringNumber) #Uncomment for debug
    return answer

def sAcP(ser):
    """
    Saves current setup as active profile
    Input: 
        ser: Serial socket
    Output:
        Modem answer
    """
    frase = 'AT&W0\r\n' #Saves as profile 0
    answer = query(ser,frase,"")
	if answer=='OK\n':
		frase = 'AT&Y0\r\n' #Saves profile 0 as power-up default
    answer = query(ser,frase,"")
	#if answer=='OK\n':
	#	print "Saved setup as profile 0 and power up default setup" #Uncomment for debug
    return answer
    
def iSSet(ser):
    """
    Used with data modems on Satice, initial setup of the modem
    Input: 
        ser: Serial socket
    Output:
        boolean answer, true for success false for not succesfull.
    """
	#more elegant if I change output of answers in those particular cases to boolean:
	#if (rFS(ser) && dDTR(ser) && dFlowC(ser) && nR(ser) && sAcP(ser)): true
	#else return false
	
    answer = rFS(ser)
    if answer != 'OK':
        return False
    answer = dDTR(ser)
    if answer != 'OK':
        return False
    answer = dFlowC(ser)
    if answer != 'OK':
        return False
    answer = nR(ser)
    if answer != 'OK':
        return False
    answer = sAcP(ser)
    if answer != 'OK':
        return False
    
    return True
	
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
		
def SIMr(ser,mode="data"):
    """
    Inquires about the status of the card
    Input: 
        ser: Serial socket
		mode: data / sbd...
    Output:
        Modem answer: 0-5. Use dSIMr to decode meaning.
    """
	if mode=="sbd" or mode=="SBD":
		answer= query(ser,'AT+SBDREG?\r\n',':')
		#This would answer only with status code
		
		#UPDATE::
		#+SBDREG[=<location>] means we can add location update instead of trusting the Iridium triangulation
		#<location> has format: [+|-]DDMM.MMM,[+|-]dddmm.mmm , First field is latitude, second is longitude. (D)egrees(M)inutes.Thousandsof(M)inutes
		#A user can send an MO SBD message and register at the same time by using the +SBDIX command	
		#For example,
			#AT+SBDIX=5212.483,-00007.350
			#corresponds to 52 degrees 12.483 minutes North, 0 degrees 7.35 minutes Wes
		#--->if location used within call a second code will be answered,reg_error
		
	else: answer = query(ser,'AT+CREG?\r\n',',')
	#What happens if my answer is 'no answer?'
    if answer == 'No answer': #In this case I consider not searching neither registered
		answer = 0 
    return answer
	
def ICCID(ser):
    """
	Checks for the Carrier Integrated Circuit Card IDentifier, defines the SIM card
    Input: 
        ser: Serial socket
    Output:
        Modem answer: the CICCID, f.i. 8988169312004****** 
    """    
	answer = query(ser,'AT+CICCID\r\n',':')
    return answer

def uSIMP(ser,pin = '1111'):
    """
    Unlocks SIM card with the Pin code
    Input: 
        ser: Serial socket
        pin: Pin code, default 1111 in Irirdium cards
    Output:
         Modem answer: Usually OK or NO ANSWER.
    """   
    phrase = 'AT+CPIN="{}"\r\n'.format(pin)
	answer = query(ser,phrase,'')
	#answer= query(ser,phrase) #as I am expecting ok or no answer, this call should work (without splitch)
	##########################
	# I could just return a boolean, success or unsuccesful. Easier to work within the software
	#out =false #default values
	#if (answer==ok)
	#	out=true
	#return out
	##########################
    return answer
	
def dSIMP(ser,pin = '1111'):
    """
    Removes pin code requirement (disables pin code), current pin required.
    Input: 
        ser: Serial socket
        pin: Current pin code: default 1111
    Output:
         Modem answer: Usually OK or NO ANSWER.
    """
    phrase = 'AT+CLCK="SC",0,"{}"\r\n'.format(pin)
	answer = query(ser,phrase,'')
	#Same thing as the one before, I could just return a boolean value to mark success.
    return answer
	
def Dcall(ser,number):
    """
    Data call to Iridium phone. 
    Input: 
        ser: Serial socket
        number: phone number, f.i. 8816765***** (note that to this number, voice channel would be 8816763*****)
    Output:
         Modem answer: Usually OK or NO ANSWER. In this case if call is succesful the modem will go into data mode.
    """
    phrase = 'ATDT{}\r\n'.format(number) 
	#I usually used ATD+Number, seems you can use ATDTNumber or ATDNumber
	#phrase = 'ATD +{}\r\n'.format(number) #We used this one with PPP setup
	answer = query(ser,phrase,'')
	#Same thing as the one before, I could just return a boolean value to mark success.
	#Case I succed I'll be in data mode.
    return answer
	
def sMSBD(ser,msg):
    """
    Sends a text message to the SBD modem's Mobile Originated buffer
	in order to send this message a SBDI session must be issued.
    Input: 
        ser: Serial socket
        msg: Body of the message we want to issue
    Output:
        The modem answer, OK case succesful writting in SBD output buffer
	"""
    frase = 'AT+SBDWT='+msg+'\r\n'
    answer = query(ser,frase,"")
    return answer
	
	#Add binary bMSBD() with AT+SBDW=<message length>
	#catch Ready as answer
	#send binary data
	#catch 0 answer for succesful write on output buffer
	
def coverageTest(ser,tout=300):
    """
	This function performs a coverage test, if succesful then tries to ask 
	for sim card registration status. If sim is registered on the network 
	the function will return 1, otherwise it will return 0 as status code.
	To enhance logging output uncomment logME() call.
    Compatible with SBD and data modems -> double check, please..
    Input: Serial port to connect, timeout (default 300s)
    Output: 
        status: 0 for enough coverage/not registered. 1 for registered and with coverage.
		Maybe it is a good idea to add a "2" output in case coverage is ok but registry not (clue to unregistered sim card) 
    """
	print 'Initializing modem:\n'
    timeout = time.time() + tout   # By default 300s
    status=0
    while time.time()<timeout: #For 5 minutes
      coverage = query(ser,'AT+CSQ\r\n',':') #In this case query will return a number, 0 to 5.
      if coverage>3:
        print 'Coverage acceptable\n'
		regCode = SIMr(ser)
        #regCode = query(ser,'AT+CREG?\r\n',',') #For CREG we will also have a number ranging 1 to 4, does the same with a generic function		
        if regCode==1:
          print 'SIM registered\n'
          #logME()
		  status=1
          break #Don't wait for the timeout once we are registered
    return status
def logME(type="coverage")
	"""
	logMe logs extended information among diverse operations on the subroutines.
	Right now this is operational only on linux based systems.
	Input: Serial port to connect, timeout (default 300s)
    Output: 
        status: 0 for enough coverage/not registered. 1 for registered and with coverage.
		Maybe it is a good idea to add a "2" output in case coverage is ok but registry not (clue to unregistered sim card) 

	"""
	now = datetime.datetime.utcnow().strftime('%Y-%m-%d_%H:%M:%S') #timestamp, case we want to log
	case type=="coverage"
		f = open('/home/satice/log/coverage.log','a')
		f.write(now+' Registered with '+cobertura+' of coverage\n')
        f.close()
	#same to be added for message transmited succesfully, through data, and for message received and transmited on SBD.	
def sbdMessage(input="nop")
	"""
    Handles SBDI session, receives incomming message if available on the Mobile
	Terminated buffer and sends message if available in the Mobile Originated buffer.
	in order to send this message a SBDI session must be issued.
    Input: 
        ser: Serial socket
        msg: Body of the message we want to issue
    Output:
        The modem answer, OK case succesful writting in SBD output buffer
	"""
	answer=query(ser,'AT+SBDD2\r\n') #Clear mobile originated and terminated buffer
	if input<>'nop':  #If its not a nop, then write message to the mobile originated buffer
		respuesta = sMSBD(ser,input,"") 
	#Here I should have a for i<10,i++, for i in range (0,10) does the trick
	for i in range (0,10) #Ten tries
		RXstr=query(ser,'AT+SBDI',':') #Returns something like "3,0,0,0,0,0" from "+SBDIX:3,0,0,0,0,0"
		if len(RXstr)<8 : RXstr="3,0,0,0,0,0" #Double check that the answer is of desired length, othersiwe use a default output
		RXfrags=RXstr.split(',',5)
		#decodeStatusSBD(RXstr) #Uncomment to see definition of status messages
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

#...>>>LOVRO LIBRARY -- > Handles file fetch, partition, naming conventions, hash code generation, outputs message to be transmitted
#....>>> Transmitted message -- > f.i. filenameEXTxxYY.DATA.Checksum
#....>>> Need to be sure the separation between name field, data and checksum cannot be repeated inside data (. is too generic, use something like a "wink sequence" :D;D:D )
#...>>>Receives acknoledgment encoded, f.i. ACKfilenameEXTxxYY being xx number of chunk out of total yy parts.
#...>>>Processes stacks of output files, removes the ones succesfully transmitted, adds new files...
	
def nextfile():
  #Takes the first file out of a list command on the shortlist
  #Compares its name to the first file on the temp folder
  #If they are equal, do nothing
  #If there are no files in the temp folder, then split current file to temp folder
  os.system("/bin/bzip2 "+thePath)

def createMe():
  #Lists temp folder, takes first file
  #Creates a CRC code
  #Creates a temporal string: CRC code + content of the file through cat + name of the file.
  #return message

def compress(file):
  os.system("/bin/bzip2 "+thePath+folder_array[n][0]+folder_array[n][1]+folder_array[n][2]+folder_array[n][3]+folder_array[n][4]+folder_array[n][5]+folder_array[n][6]+folder_array[n][7]+"."16d");
  os.system("ln /home/satice/gps/rnx/"+temp_year[0]+temp_year[1]+temp_year[2]+temp_year[3]+'/'+tempdoy+'/'+folder_array[n][0]+folder_array[n][1]+folder_array[n][2]+folder_array[n][3]+tempdoy+folder_array[n][7]+"."+temp_year[2]+temp_year[3]+"d.bz2 /home/satice/new/"+folder_array[n][0]+folder_array[n][1]+folder_array[n][2]+folder_array[n][3]+tempdoy+folder_array[n][7]+"."+temp_year[2]+temp_year[3]+"d.bz2");


def sendMe(message,tout=300):
	"""
    Handles data message transmission. Waits for an ACK, case message transision is OK.
	Otherwise resend. Receiver ACK is done by comparing comparing CRC added to each package
	and the reconstruction with name and content on each partitioned file. 
    Input: 
        msg: Message we want to send
		tout: timeout, default 300s
    Output:
        The modem answer, OK case succesful writting in SBD output buffer
	"""
#sends the message through the current setup.
#waits for acknowledge, receiver must provide an ok by recreating the file with the name file and the content
#and comparing the CRC received to the one generated on that file.
  timeout = time.time() + tout   # 300 seconds by default
  outputCode=0
  while time.time()<timeout: #For 5 minutes max, we will try to send a file
    if(query(ser,message,','))=='ok': #output message must be hej,ok
      #because query will take the second field when the command is not just AT
      outputCode=1
      break
  return outputCode

if __name__ == '__main__':
    #On sequence for the modem, case u use a GPIO
    modemT(True,"Fox") #Powers on the modem.
	listS=serial_ports()
	ser = connect(listS[0])
	resp = initialConfig9522B(ser)
    num = SIMNumber(ser)
    respuesta = registeredSIM(ser)
    print(decodeNetworkRegistration(respuesta))
	
	
#DO STUFF !!!!-----------!!!!!!!!!!------------!!!!!!!!!!!!!
		
    for x in range (1,3): #Three tries
      if coverageTest(ser,300):#Case we have coverage and sim registered
      #Do your things

        #call
        # fetch file and split it
        #   create message per splitted part
        #   sendmessage (probably a loop)
        #   wait for confirmation, else send same message
        #   create new message, next splitted part, send message until no more splitted parts.
        #   when no more splitted parts wait for dual ack from receiver (meaning decompresion, CRX2RNX were succesfull)
        #   or in case is a fbs, decompresion was succesful. Case is an image, total crc ok.
        # clean temp buffer, remove transmitted file from shortlist, fetch next file from shortlist until shortlist is empty.

      else: #coverageTest returns 0, then next try
        print 'Trying again'
		
#DO STUFF !!!!-----------!!!!!!!!!!------------!!!!!!!!!!!!!

	#Close serial port and power off modem
    ser.close()
	modemT(False,"Fox") #Powers off the modem.
