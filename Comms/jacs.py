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
		fox.Pin('J7.35','low') #Using a Fox Board as host with GPIO controlled power
    time.sleep(30) #required to discharge charge pump on the modem, according to manufacturer.
	
	if mode==true: 
		print 'Modem ON'
		case type=="fox":
			fox.Pin('J7.35','high') #For mk3 satice PCB only compatible with data modems.
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
    # Open serial socket to device
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
	"""
	#By default wait time is 1 second
    ser.write(frase)
    out = ''
    # let's wait 'espera' second before reading output (let's give device time to answer)
    time.sleep(wait)
    while ser.inWaiting() > 0:
        out += ser.read(1)
    if out == '':
        return 'No answer'
    else:
        # Modem returns the issued command, next line the answer.
        # Up next a blank line is sent and finally an OK\r\n if everything goes ok.
        # If only an AT command has been issued, the answer is only OK\r\n
        out_ = out.split('\r\n')
        return out_[2]#The order is \r\nIssuedComm\r\nanswer\r\nblank\r\nok\r\n !!!!
		

def query(ser,phrase='AT\r\n',splitch=','): 
     """
	This function issues an AT command through a serial port,
	waits for an answer and splits the string output through a split
	character (to get rid of unwanted info)
    Compatible with SBD and data modems
    Input: 	Serial port to connect
			AT command to be issued, default is 'AT' with carriage return
			Split character f.i.(';'..','..':'), default is ','
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
    return answer

def noFlowControl(ser):
    """
	Disables flow control on the modem
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
    respuesta = query(ser,frase,"")
    return respuesta

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
    respuesta = query(ser,frase,"")
    return respuesta
	
# W I P	
	
	# def writeSBD(ser,frase,espera):
    # """
    # Envia al modem un comando AT y espera su respuesta.
    # Funcion para Modem 9522B y SBD.
    # Input:
        # ser: Variable con la conexión serie al modem Iridium
        # frase: Comando AT a enviar
        # espera: Tiempo de espera de la respuesta del modem
    # Output: La respuesta del modem
    # """
    # ser.write(bytes(frase, encoding="UTF-8"))
    # out = ''
    # let's wait 'espera' second before reading output (let's give device time to answer)
    # time.sleep(espera)
    # if ser.inWaiting() > 0:
        # out = ser.read(ser.inWaiting()).decode(encoding='UTF-8')
    # if out == '':
        # return 'No answer'
    # else:
     #   Esto hay que hacerlo porque el SBD devuelve primero lo que 
    #    acabas de enviar, luego una linea en blanco y finalmente 
   #     la respuesta
  #      Despues vuelve a enviar una linea en blanco
 #       Despues un OK\r\n si todo va bien.
#        En el caso de solo enviar un AT, la respuesta ya es el OK\r\n
        # out_ = out.split('\r\n') 
        # return out_[2]
	

	
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
      cobertura = query(ser,'AT+CSQ\r\n',':') #In this case query will return a number, 0 to 5.
      if cobertura>3:
        print 'Coverage acceptable\n'
        registro = query(ser,'AT+CREG?\r\n',',')#For CREG we will also have a number ranging 1 to 4.
        if registro==1:
          print 'SIM registered\n'
          #logME()
		  status=1
          break #Don't wait for the timeout
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
		if len(RXstr)<8 : RXstr="3,0,0,0,0,0" #Double check that the answer is of desired length
		RXfrags=str.split(',',5)
		MO_Status=RXfrags[0] #review MO code 13, gateway reported  that the session did not complete for not entirely transfered msges
		MT_Status=RXfrags[2]
		if MT_status >= 1 :
			For i in range (0,10) #Ten tries
				RXstr=query(ser,'AT+SBDRT',"*")#Read message
				Delay(0,1,sec)
				SerialIn(RXStr,ComME,6000,"!",RXBufSize)
				SplitStr(RX_message,RXStr,"*!",2,5)	#Review, this is CR1k code!!!, essentially, command comes as *command*!. 
				# First get up to !, then get through the *
				If RX_Message(2) <> "" Then 
					ExitFor
				EndIf
			Next
		if MO_Status <=1 or input == 'nop': break #Case correctly sent or input message was 'nop' message
		else : time.sleep(10) #wait 10 seconds... and try to send it again.
				
			
	
	
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
