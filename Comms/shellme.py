#!/usr/bin/python
"""
Licensed under MIT (../LICENSE)

SHELLME.py

The program is just a subprocess wrapper with some output
formatting capavilities.

V0. Oriol Sanchez, ICM-CSIC
"""
# Add build list support.
# from home folder, add an out buffer place "out" or "temp"
# feed splited files from shortlist to temp
# when splited files are added, add them also to the out list.
# save the outlist as a csv?

import subprocess as sp#for newer pythons, also in python 2.5 but without check_output
import os

def shellme(command='ls', argument=None, splitch=' ', debug=False, type=0):
	"""
	Shellme() issues a shell command to the system and returns its answer
	Tested in python 2.5.2. with Linux 2.6
	Input: 
		command: command, i.e. ls
		arguments: modifiers of the command, i.e. -lah,
		splitch: string used to separate the answer into a vector
	Output:
		out: answer, vector of strings separated by a splitch key or boolean in case 
			issued command does not expect an answer (type=1), note boolean answer 
			reports problem detected and not succes (thus a 0 means process issued correctly)
	Use:
		shellme('cksum',path+fle) #returns out[0] as CRC, out[1] as size, out[3] as file + path
	"""
	#Issue command
	if (argument==None): #Not likely, but posibility should always be covered.
		process= sp.Popen([command], stdout=sp.PIPE)
		if debug: print ('Shellme: '+ command)
	else:
		if type==1: stdout=sp.call('split'+argument, shell=True) #No answer expected	
		else: process= sp.Popen([command,argument], stdout=sp.PIPE)
		if debug: print ('Shellme: '+str(command)+' '+str(argument) + '\n TYPE='+str(type)+'\n')

	if debug: print ('Shellme: '+str(command)+' '+str(argument) + '\n TYPE='+str(type)+'\n')	
	
	#Generate answer
	if type==0: #Expect answer	
		stdout= process.communicate()
		out= stdout[0].split(splitch)
	else: 
		if stdout==0: out=False #No answer but success
		else: out=True #No answer, couldn't issue command
	if debug: print('Shellme: output: '+str(out)+'\n')
	return out
	#out = stdout[0].decode('utf8').split('\n') #maybe u need to decode utf8 in python 3.
	
def listme(path,debug=False,mode=0):
	"""
	Calls shellme, it's a wrap, and returns a vector of the files on the path
	Tested in python 2.5.2. with Linux 2.6
	Inpupt: 
		path: folder path.
		debug: debug mode, to report extended information
		mode: 0 for normal list, 1 to also return number of files in the folder
	Output:
		answer: vector of files in the path
	"""
	deb=debug
	answer=shellme(argument=path, splitch='\n',debug=deb)
	nfiles=len(answer)-1 #-1 for the carriage return

	if debug: print("listme answer:\n"+ str(answer)+'\n')
	if debug: print("number of files in folder: "+str(nfiles))

	if mode==0:	return answer
	elif mode==1: return answer,nfiles
	
def fetchme(path, debug=False):	
	"""
	Calls shellme, it's a wrap, and returns a matrix of files with crc codes,
	sizes and paths.
	Tested in python 2.5.2. with Linux 2.6
	Input:
		path
	Output:
		answer: matrix of files with crc codes, length and path+filename
	"""
	deb=debug
	lista=listme(path)
	answer=[]
	for i in range(0,len(lista)-1): #Iterates through all the files in path
		fle= lista[i]
		dout=shellme('cksum',path+fle,debug=deb) 
		moc=dout[2].split('\n')
		dout[2]=moc[0]
		answer.append(dout)
		if debug: 
			print('File is '+fle)
			print('CRC for '+fle+' is '+str(dout[0]))
			print('Size for '+fle+' is '+str(dout[1])+' bytes')
			print('Route for '+fle+' is '+str(dout[2])+'\n')
	return answer

def scomp(fle,oripath, despath, MTU=7000, digits=3, debug=False):
	"""
	Here "slice compress" a file to several part files..., for SATICE files are already
	pre-compressed to its minimum size. Return True if operation done correctly.
	Tested in python 2.5.2. with Linux 2.6
	Input:
		fle: filename
		oripath: origin path
		destpath: destiny path
		MTU: Maxium Transfer Unit, default 7KBytes
		digits: number of digits used in the splited file, default 3
	Output:
		itsOK: boolean output for success of operation
	"""

	#Check if already sliced in temp:
	outfi=listme(despath)	
	if outfi==['']: 
		if debug: print('Temp folder is empty')#empty folder, go on.
			
	else: #check files against incomming one.
		for i in range(0,len(outfi)-1): #Lists all files.
			flin= outfi[i].split('_')#take only filename, without part number
			flin=flin[0]			
			if (flin==fle): 
				if debug: print('File '+outfi[i] + ' is a chunk of ' + fle)
				return False #No need to continue, one file shoots this exit (Tested)
			else: 
				if debug: print('File '+outfi[i] + ' is not a chunk of ' + fle) #new file, go on.

	deb=debug
	argument= (' -b ' + str(MTU) + ' -da '+ str(digits)  +' '+ str(oripath)+str(fle) +' '+ str(despath)+str(fle)+'_') #_separates digits from filename 

	if debug: print('Length arguments: '+str(len(argument))+'\n' + 'Arguments: '+argument+'\n')	

	#General rule does not work with Popen, but now it should work with the modified shellme...
	#To Be Tested....
	itsOK=shellme('split',argument,debug,type=1) #type=1 for shell=True
	
	#Ok, you've splitted me. Now check if my last part is MTU sized, if that is the case.
	#Add another packet with a silly message so decoder uses a general rule to figure out
	#when all parts of a file are already received.
	#Silly message, that is actually a deep statement: deepthink="42 is the answer to life, the universe and everything else..."
	
	if itsOK==0: return True
	else: return False
	
	
# def dcomp(oripath, despath,MTU):
	# """
	# Here decompress a file from several part files... To be used on the server side...
	# """
	# #First, from fle I create a list from oripath with all matching fle files.
	# outfi=listme(oripath)	
	# if outfi==['']: 
		# if debug: print('Origin folder is empty, no files to rejoin')#empty folder, exit.
		# return False
	# else: #check files against incomming one.
		# for i in range(0,len(outfi)-1): #Lists all files.
			# flin= outfi[i].split('_')#take only filename, without part number
			# flin=flin[0]			
			# if i==0: fle=flin #Only filename, no part number
			# if (flin==fle): #Yup, thats the file I am looking for
				# if debug: print('File '+str(outfi[i]) + ' is a chunk of ' + str(fle))
				# #sizeme=shellme()
				# catout=shellme('cat',argument)
				# #if sizeme==MTU:#Add me to the list
				# #else:
					# #if catout=="42 is the answer to life, the universe and everything else..." #Then this is the last file and it is not ussable.
					# #else: #Add me to the list
					# #I am the last file, thus break this endless loop
			# else: 
				# if debug: print('File '+str(outfi[i]) + ' is not a chunk of ' + str(fle) ', ignoring it...') #new file, go on.

	# #cat SI941200.16f.bz2*>SI941200.16f.bz2
	# if os.path.isfile(oripath+fle): #os.path.exists(oripath+fle)
		# argument = fle + "*>>" + fle #Append to the end of a existing one 
	# else:
		# argument = fle + "*>" + fle #Create a new file
	# #What happens if I append several files into another and then I finally gzcat it...
	# try:  
		# dout=shellme('cat',argument) 
		# itsOK=True
	# except: itsOK=False
	# return itsOK


#### MAIN PROGRAM FOR TEST.   
if __name__ == '__main__':
	#path="/home/satice/new/shortlist/"
	path = '/home/satice/'
	origin='new/shortlist/'
	destiny='temp/'
	rejoin='timp/'
	fpath=path+origin #path to be loaded from conf file
	dpath=path+destiny
	rpath=path+rejoin
	
	lista=listme(fpath,debug=True)
	fle=lista[0].split()
	fle=fle[0] #splited the empty space I had after the filename
	print('\n Spliting file ' + fle)
	good=scomp(fle,fpath,dpath,debug=True)
	print('\n'+str(good)+'\n')
	
	lista,numfiles=listme(dpath,True,1)
	print('\n Number of files in Temp folder ' + str(numfiles))
	
	# print('\n Recovering file ' + fle)
	# good=dcomp(dpath,rpath,debug=True)
	# print('\n'+str(good)+'\n')
	
	# for i in range(0,len(lista)-1): #Lists all crc,size and paths from a folder.
		# fle= lista[i]
		# print('File is '+fle)
		# dout=shellme('cksum',path+fle) 
		# print('CRC for '+fle+' is '+str(dout[0]))
		# print('Size for '+fle+' is '+str(dout[1])+' bytes')
		# print('Route for '+fle+' is '+str(dout[2])+'\n')
