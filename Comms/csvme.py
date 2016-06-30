#!/usr/bin/python

import csv
import os
import time as t
import datetime

import random #Only used with test subroutine
import math #Only used in test subroutine


#csfile="/home/satice/conf/flist.csv" #where your fetch list file is
csfile="C:\\Users\\oriol\\Desktop\\flist.csv" #workstation test

def loFLIST(input):
	"""
	Loads Fetch List file, if not available then creates an empty one
	"""
	if not(os.path.exists(input)): #File does not exist, create new file.
		print("New file")
		os.system("echo FILENAME,TSENT,PART,CRC,SIZE,PATH,ACK >" + input + "\n") #Build headers of default CSV file
	else: print("opening existing file")

def reFLIST(input,debug=False):
	"""
	Reads file data
	"""
	flist=open(input,'r',newline='')
	readme= csv.reader(flist)
	example= list(readme) #once I list, the file is readed completely
	#print(example[1])
	fsize=(len(example)-2)#-1 for last empty line, -1 for headers
	if debug: print('Size is:' , fsize)#last line of csv
	if debug: print('Header is:' , example[0])
	if debug: print('Last line is:\n' , example[fsize],'\n')#last line of csv

	if debug: print('Entire content:')
	for i in range (1,fsize): 
		#example[i][0]#Filename // String
		#example[i][1]#Tsent // T.B.D.
		example[i][2]=int(example[i][2])#Part // Integer
		example[i][3]=int(example[i][3])#CRC // Integer
		example[i][4]=int(example[i][4])#Size in Bytes // Integer
		example[i][5]#Path // String
		example[i][6]=bool(int(example[i][6]))#ACK //Boolean
		if debug: print(example[i]) #Print all fields 
	flist.close()
	return fsize, example #return size of cue and return list with formats
		
def apFLIST(input,data,debug=False):
	"""
	Appends a line to a csv file
	"""	
	flist=open(input,'a',newline='')
	writeme=csv.writer(flist)
	writeme.writerow(data)
	flist.close()
	a,b=reFLIST(input,debug)
	if debug: print("Last line appended:\n",b[a+1])#last line of csv    
	flist.close()

def	hkFLIST(input,debug=False,tmout=600):
	"""
	House Keep csv file, if last field is true then remove line.
	Add condition, if timestamp bigger than timeout, remove line.
	
	"""
	tnow=t.time()
	fsize,example=reFLIST(input,debug) #Returns size and formated list 
	
	flist=open(confile,'w',newline='') #In this case I'll overwrite the content
	writeme=csv.writer(flist)
	#Get CSV ready to be written
	if debug: print('Entire content to be saved:')
	if debug: print(header)
	writeme.writerow(header)#First comes first, header
	for i in range (1,fsize): #skip headers row
		if ((example[i][6])==True): continue #Remove this line from the list
		if (tnow-(float(example[i][1]))>tmout): example[i][1]=0.0 #Set timestamp to 0.0 when more than timeout happens
		writeme.writerow(example[i]) #write row into updated list
		if debug: print(example[i])
	flist.close()    

def nextfile(input):
	"""
	Returns first file to be sended
	
	"""
	fsize,example=reFLIST(input,debug) #Returns size and formated list 
	for i in range (1,fsize): 
		if ((float(example[i][1]))==0.0): 
			nfile=example[i]
			break
	return nfile

	
def test(input):
	"""
	Fills the csv with one new random file, essentially use it to 
	"""
	FILENAME="pitu"
	TSTAMP=t.time()
	st = datetime.datetime.fromtimestamp(TSTAMP).strftime('%Y-%m-%d %H:%M:%S')
	print(st)
	NUM=math.floor(random.uniform(1, 10)*10)
	CRC=math.floor(random.uniform(1, 10)*10000000)
	d= math.floor(random.uniform(1, 10)*1000)
	SIZE=d
	PATH='/home/satice/pitu'
	ACK=0
	msg=[FILENAME,TSTAMP,NUM,CRC,SIZE,PATH,ACK]
	print(msg)
	apFLIST(input,msg,1)
	
#### MAIN PROGRAM FOR TEST.   
if __name__ == '__main__':
	loFLIST(csfile) #Inits list
	#Prints list data
	size,list=reFLIST(input,1) #Reads list, returns size and complete list formated
	#Load data...
	apFLIST(csfile,data) #Appends new file to list
	

